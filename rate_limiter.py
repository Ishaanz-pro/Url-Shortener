import redis.asyncio as redis
from app.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter using Redis sliding window"""
    
    @staticmethod
    async def _get_redis() -> redis.Redis:
        """Get Redis connection"""
        return await redis.from_url(
            settings.redis_url,
            encoding="utf8",
            decode_responses=True
        )
    
    @staticmethod
    def _get_key(identifier: str, action: str = "general") -> str:
        """Generate rate limit key"""
        return f"rate_limit:{identifier}:{action}"
    
    @classmethod
    async def is_allowed(
        cls,
        identifier: str,
        action: str = "general",
        requests: Optional[int] = None,
        period: Optional[int] = None
    ) -> bool:
        """Check if request is allowed"""
        try:
            requests = requests or settings.rate_limit_requests
            period = period or settings.rate_limit_period_seconds
            
            r = await cls._get_redis()
            key = cls._get_key(identifier, action)
            
            current = await r.incr(key)
            
            if current == 1:
                await r.expire(key, period)
            
            await r.close()
            
            return current <= requests
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            return True  # Allow on error
    
    @classmethod
    async def get_remaining(
        cls,
        identifier: str,
        action: str = "general",
        requests: Optional[int] = None,
        period: Optional[int] = None
    ) -> int:
        """Get remaining requests"""
        try:
            requests = requests or settings.rate_limit_requests
            period = period or settings.rate_limit_period_seconds
            
            r = await cls._get_redis()
            key = cls._get_key(identifier, action)
            
            current = await r.get(key)
            ttl = await r.ttl(key)
            
            await r.close()
            
            if current is None:
                return requests
            
            remaining = requests - int(current)
            return max(0, remaining)
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            return requests
    
    @classmethod
    async def reset(cls, identifier: str, action: str = "general") -> bool:
        """Reset rate limit for identifier"""
        try:
            r = await cls._get_redis()
            key = cls._get_key(identifier, action)
            await r.delete(key)
            await r.close()
            return True
        except Exception as e:
            logger.error(f"Rate limit reset error: {e}")
            return False
