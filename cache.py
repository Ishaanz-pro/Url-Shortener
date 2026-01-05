import redis.asyncio as redis
from app.config import settings
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis cache manager for distributed caching"""
    
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    async def get_redis(cls) -> redis.Redis:
        """Get Redis connection"""
        if cls._instance is None:
            cls._instance = await redis.from_url(
                settings.redis_url,
                encoding="utf8",
                decode_responses=True
            )
        return cls._instance
    
    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            r = await cls.get_redis()
            value = await r.get(key)
            if value:
                return json.loads(value) if value.startswith('{') or value.startswith('[') else value
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @classmethod
    async def set(cls, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            r = await cls.get_redis()
            expire = expire or settings.redis_cache_expiry
            
            if isinstance(value, dict) or isinstance(value, list):
                value = json.dumps(value)
            
            await r.setex(key, expire, str(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete key from cache"""
        try:
            r = await cls.get_redis()
            await r.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            r = await cls.get_redis()
            return await r.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


class URLCache:
    """Specialized cache for URL operations"""
    
    @staticmethod
    def _get_url_key(short_code: str) -> str:
        """Generate cache key for URL"""
        return f"url:{short_code}"
    
    @staticmethod
    def _get_alias_key(alias: str) -> str:
        """Generate cache key for alias"""
        return f"alias:{alias}"
    
    @staticmethod
    def _get_user_urls_key(user_id: str) -> str:
        """Generate cache key for user URLs"""
        return f"user_urls:{user_id}"
    
    @classmethod
    async def get_url(cls, short_code: str) -> Optional[dict]:
        """Get URL from cache"""
        return await CacheManager.get(cls._get_url_key(short_code))
    
    @classmethod
    async def set_url(cls, short_code: str, url_data: dict, expire: Optional[int] = None) -> bool:
        """Cache URL data"""
        return await CacheManager.set(cls._get_url_key(short_code), url_data, expire)
    
    @classmethod
    async def delete_url(cls, short_code: str) -> bool:
        """Delete URL from cache"""
        return await CacheManager.delete(cls._get_url_key(short_code))
    
    @classmethod
    async def get_by_alias(cls, alias: str) -> Optional[dict]:
        """Get URL by alias from cache"""
        return await CacheManager.get(cls._get_alias_key(alias))
    
    @classmethod
    async def set_alias(cls, alias: str, url_data: dict, expire: Optional[int] = None) -> bool:
        """Cache alias mapping"""
        return await CacheManager.set(cls._get_alias_key(alias), url_data, expire)
    
    @classmethod
    async def delete_alias(cls, alias: str) -> bool:
        """Delete alias from cache"""
        return await CacheManager.delete(cls._get_alias_key(alias))
