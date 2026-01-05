from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.database import get_db
from app.models.url import URL
from app.models.user import User
from app.services.encoder import Base62Encoder, URLValidator
from app.services.cache import URLCache
from app.services.rate_limiter import RateLimiter
from app.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/shorten", tags=["shorten"])


class ShortenRequest(BaseModel):
    """Request model for URL shortening"""
    url: HttpUrl
    custom_alias: Optional[str] = Field(None, min_length=3, max_length=20, regex="^[a-zA-Z0-9_-]+$")
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760)  # Max 1 year


class ShortenResponse(BaseModel):
    """Response model for shortened URL"""
    id: str
    short_code: str
    short_url: str
    original_url: str
    custom_alias: Optional[str]
    title: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class URLListResponse(BaseModel):
    """Response model for URL list"""
    id: str
    short_code: str
    short_url: str
    original_url: str
    custom_alias: Optional[str]
    click_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    # For this implementation, we use a simple user ID header
    # In production, verify JWT token
    try:
        token = authorization.replace("Bearer ", "")
        
        result = await db.execute(
            select(User).where(User.id == token)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    x_forwarded_for: Optional[str] = Header(None)
):
    """
    Shorten a URL with optional custom alias
    
    - **url**: Original URL to shorten (required)
    - **custom_alias**: Custom short alias (3-20 chars, alphanumeric)
    - **title**: Short URL title
    - **description**: URL description
    - **expires_in_hours**: Expiration time in hours
    """
    
    # Rate limiting
    allowed = await RateLimiter.is_allowed(
        identifier=user.id,
        action="shorten"
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Normalize and validate URL
    original_url = str(request.url)
    
    if not URLValidator.is_valid_url(original_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format"
        )
    
    original_url = URLValidator.normalize_url(original_url)
    
    # Check custom alias if provided
    if request.custom_alias:
        result = await db.execute(
            select(URL).where(URL.custom_alias == request.custom_alias)
        )
        
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom alias already in use"
            )
    
    # Generate short code if no custom alias
    short_code = request.custom_alias or Base62Encoder.generate_short_code()
    
    # Check if short code already exists
    while not request.custom_alias:
        result = await db.execute(
            select(URL).where(URL.short_code == short_code)
        )
        
        if result.scalar_one_or_none() is None:
            break
        
        short_code = Base62Encoder.generate_short_code()
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
    
    # Create URL record
    url_record = URL(
        id=str(uuid.uuid4()),
        user_id=user.id,
        original_url=original_url,
        short_code=short_code,
        custom_alias=request.custom_alias,
        title=request.title,
        description=request.description,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(url_record)
    await db.commit()
    await db.refresh(url_record)
    
    # Cache the URL
    short_url = f"{settings.shortener_domain}/{short_code}"
    await URLCache.set_url(
        short_code,
        {
            "id": url_record.id,
            "original_url": original_url,
            "short_code": short_code,
            "is_active": True,
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    )
    
    if request.custom_alias:
        await URLCache.set_alias(
            request.custom_alias,
            {
                "id": url_record.id,
                "original_url": original_url,
                "short_code": short_code
            }
        )
    
    logger.info(f"URL shortened: {short_code} -> {original_url}")
    
    return ShortenResponse(
        id=url_record.id,
        short_code=short_code,
        short_url=short_url,
        original_url=original_url,
        custom_alias=request.custom_alias,
        title=request.title,
        created_at=url_record.created_at,
        expires_at=expires_at
    )


@router.get("/user/urls", response_model=list[URLListResponse])
async def get_user_urls(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all URLs created by the current user"""
    
    if limit > 100:
        limit = 100
    
    result = await db.execute(
        select(URL)
        .where(URL.user_id == user.id)
        .order_by(URL.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    urls = result.scalars().all()
    
    return [
        URLListResponse(
            id=url.id,
            short_code=url.short_code,
            short_url=f"{settings.shortener_domain}/{url.short_code}",
            original_url=url.original_url,
            custom_alias=url.custom_alias,
            click_count=url.click_count,
            created_at=url.created_at,
            updated_at=url.updated_at
        )
        for url in urls
    ]
