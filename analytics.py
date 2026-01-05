from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app.models.url import URL, Analytics
from app.models.user import User
from app.routes.shorten import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class CountryStats(BaseModel):
    country: Optional[str]
    clicks: int


class DeviceStats(BaseModel):
    device_type: Optional[str]
    clicks: int


class BrowserStats(BaseModel):
    browser: Optional[str]
    clicks: int


class AnalyticsResponse(BaseModel):
    total_clicks: int
    unique_days: int
    top_countries: list[CountryStats]
    top_devices: list[DeviceStats]
    top_browsers: list[BrowserStats]
    last_clicked_at: Optional[datetime]


@router.get("/{short_code}", response_model=AnalyticsResponse)
async def get_url_analytics(
    short_code: str,
    days: Optional[int] = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get analytics for a specific shortened URL
    
    - **short_code**: The short URL code
    - **days**: Number of days to analyze (default: 30)
    """
    
    if not (1 <= days <= 365):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days must be between 1 and 365"
        )
    
    # Verify URL ownership
    result = await db.execute(
        select(URL).where(
            and_(
                URL.short_code == short_code,
                URL.user_id == user.id
            )
        )
    )
    url = result.scalar_one_or_none()
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found"
        )
    
    # Calculate date range
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total clicks
    click_result = await db.execute(
        select(func.count(Analytics.id)).where(
            and_(
                Analytics.url_id == url.id,
                Analytics.clicked_at >= start_date
            )
        )
    )
    total_clicks = click_result.scalar() or 0
    
    # Unique days
    days_result = await db.execute(
        select(func.count(func.distinct(func.date(Analytics.clicked_at)))).where(
            and_(
                Analytics.url_id == url.id,
                Analytics.clicked_at >= start_date
            )
        )
    )
    unique_days = days_result.scalar() or 0
    
    # Top countries
    countries_result = await db.execute(
        select(
            Analytics.country,
            func.count(Analytics.id).label("clicks")
        ).where(
            and_(
                Analytics.url_id == url.id,
                Analytics.clicked_at >= start_date
            )
        ).group_by(Analytics.country)
        .order_by(func.count(Analytics.id).desc())
        .limit(10)
    )
    
    top_countries = [
        CountryStats(country=row[0], clicks=row[1])
        for row in countries_result.fetchall()
    ]
    
    # Top devices
    devices_result = await db.execute(
        select(
            Analytics.device_type,
            func.count(Analytics.id).label("clicks")
        ).where(
            and_(
                Analytics.url_id == url.id,
                Analytics.clicked_at >= start_date
            )
        ).group_by(Analytics.device_type)
        .order_by(func.count(Analytics.id).desc())
    )
    
    top_devices = [
        DeviceStats(device_type=row[0], clicks=row[1])
        for row in devices_result.fetchall()
    ]
    
    # Top browsers
    browsers_result = await db.execute(
        select(
            Analytics.browser,
            func.count(Analytics.id).label("clicks")
        ).where(
            and_(
                Analytics.url_id == url.id,
                Analytics.clicked_at >= start_date
            )
        ).group_by(Analytics.browser)
        .order_by(func.count(Analytics.id).desc())
        .limit(5)
    )
    
    top_browsers = [
        BrowserStats(browser=row[0], clicks=row[1])
        for row in browsers_result.fetchall()
    ]
    
    return AnalyticsResponse(
        total_clicks=total_clicks,
        unique_days=unique_days,
        top_countries=top_countries,
        top_devices=top_devices,
        top_browsers=top_browsers,
        last_clicked_at=url.last_clicked_at
    )


@router.get("/stats/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get dashboard statistics for all user URLs"""
    
    # Total URLs created
    urls_result = await db.execute(
        select(func.count(URL.id)).where(URL.user_id == user.id)
    )
    total_urls = urls_result.scalar() or 0
    
    # Total clicks across all URLs
    clicks_result = await db.execute(
        select(func.sum(URL.click_count)).where(URL.user_id == user.id)
    )
    total_clicks = clicks_result.scalar() or 0
    
    # Most clicked URLs
    top_urls_result = await db.execute(
        select(URL.short_code, URL.click_count)
        .where(URL.user_id == user.id)
        .order_by(URL.click_count.desc())
        .limit(5)
    )
    
    top_urls = [
        {"short_code": row[0], "clicks": row[1]}
        for row in top_urls_result.fetchall()
    ]
    
    return {
        "total_urls": total_urls,
        "total_clicks": total_clicks,
        "top_urls": top_urls
    }
