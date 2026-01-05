from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.url import URL
from app.services.cache import URLCache
from app.workers.tasks import record_analytics
from datetime import datetime
from fastapi.responses import RedirectResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["redirect"])


async def get_client_ip(request: Request, x_forwarded_for: str = Header(None)) -> str:
    """Extract client IP from request"""
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host


@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_forwarded_for: str = Header(None)
):
    """
    Redirect to original URL using short code
    
    This endpoint:
    1. Checks Redis cache first (cache-first strategy)
    2. Falls back to database if not cached
    3. Records analytics asynchronously via Celery
    4. Updates last_clicked_at timestamp
    """
    
    # Try cache first
    cached = await URLCache.get_url(short_code)
    
    if cached:
        url_id = cached.get("id")
        original_url = cached.get("original_url")
        is_active = cached.get("is_active")
        expires_at = cached.get("expires_at")
        
        # Check expiration
        if expires_at:
            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="URL has expired"
                )
        
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="URL not found"
            )
    else:
        # Fall back to database
        result = await db.execute(
            select(URL).where(URL.short_code == short_code)
        )
        url_record = result.scalar_one_or_none()
        
        if not url_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="URL not found"
            )
        
        # Check if active
        if not url_record.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="URL not found"
            )
        
        # Check expiration
        if url_record.is_expired():
            url_record.is_active = False
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="URL has expired"
            )
        
        original_url = url_record.original_url
        url_id = url_record.id
        
        # Cache for future requests
        await URLCache.set_url(
            short_code,
            {
                "id": url_record.id,
                "original_url": original_url,
                "short_code": short_code,
                "is_active": True,
                "expires_at": url_record.expires_at.isoformat() if url_record.expires_at else None
            }
        )
    
    # Get client information
    client_ip = await get_client_ip(request, x_forwarded_for)
    user_agent = request.headers.get("user-agent", "")
    referrer = request.headers.get("referer", "")
    
    # Extract country from IP (simplified - in production use GeoIP2)
    country = "US"  # Placeholder
    
    # Queue analytics recording asynchronously
    try:
        record_analytics.delay(
            url_id=url_id,
            ip_address=client_ip,
            user_agent=user_agent,
            country=country,
            referrer=referrer
        )
    except Exception as e:
        logger.error(f"Failed to queue analytics: {e}")
    
    logger.info(f"Redirecting {short_code} to {original_url}")
    
    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)
