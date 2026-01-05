from celery import Celery
from app.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.url import URL, Analytics
from datetime import datetime
import logging
from user_agents import parse as parse_ua

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "url_shortener",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
)

# Database setup for Celery
database_url = settings.database_url.replace(
    "postgresql://", 
    "postgresql+asyncpg://"
)

engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=3600
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_async_session() -> AsyncSession:
    """Get async database session"""
    return AsyncSessionLocal()


@celery_app.task(bind=True, max_retries=3)
def record_analytics(
    self,
    url_id: str,
    ip_address: str,
    user_agent: str,
    country: str,
    referrer: str
):
    """Record click analytics asynchronously"""
    try:
        import asyncio
        
        async def _record():
            session = await get_async_session()
            try:
                # Parse user agent
                ua = parse_ua(user_agent)
                
                device_type = "desktop"
                if ua.is_mobile:
                    device_type = "mobile"
                elif ua.is_tablet:
                    device_type = "tablet"
                
                # Create analytics record
                analytics = Analytics(
                    url_id=url_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    country=country,
                    city=None,
                    device_type=device_type,
                    browser=ua.browser.family,
                    os=ua.os.family,
                    referrer=referrer,
                    clicked_at=datetime.utcnow()
                )
                
                session.add(analytics)
                
                # Update URL click count
                result = await session.execute(
                    select(URL).where(URL.id == url_id)
                )
                url = result.scalar_one_or_none()
                
                if url:
                    url.click_count += 1
                    url.last_clicked_at = datetime.utcnow()
                
                await session.commit()
                logger.info(f"Analytics recorded for URL {url_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error recording analytics: {e}")
                raise
            finally:
                await session.close()
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_record())
        
    except Exception as exc:
        logger.error(f"Task error: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def cleanup_expired_urls(self):
    """Clean up expired URLs periodically"""
    try:
        import asyncio
        
        async def _cleanup():
            session = await get_async_session()
            try:
                # Mark expired URLs as inactive
                from sqlalchemy import and_
                
                result = await session.execute(
                    select(URL).where(
                        and_(
                            URL.expires_at.isnot(None),
                            URL.expires_at < datetime.utcnow(),
                            URL.is_active == True
                        )
                    )
                )
                
                expired_urls = result.scalars().all()
                
                for url in expired_urls:
                    url.is_active = False
                
                await session.commit()
                logger.info(f"Cleaned up {len(expired_urls)} expired URLs")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error cleaning up URLs: {e}")
                raise
            finally:
                await session.close()
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_cleanup())
        
    except Exception as exc:
        logger.error(f"Cleanup task error: {exc}")
        raise


# Celery Beat schedule
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-expired-urls-hourly': {
        'task': 'app.workers.tasks.cleanup_expired_urls',
        'schedule': crontab(minute=0),  # Every hour
    },
}
