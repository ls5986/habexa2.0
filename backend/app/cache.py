"""
Redis caching for API responses.
"""
import os
import redis
import json
import logging
from typing import Optional, Any
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        try:
            # Try to get Redis URL from environment (Render provides REDIS_URL)
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis = redis.from_url(redis_url, decode_responses=True)
            else:
                # Fallback to individual host/port
                self.redis = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=0,
                    decode_responses=True
                )
            # Test connection
            self.redis.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}. Caching disabled.")
            self.redis = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            return None
        
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 86400):
        """
        Set value in cache.
        Default TTL: 24 hours (86400 seconds)
        """
        if not self.redis:
            return False
        
        try:
            self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str):
        """Delete key from cache."""
        if not self.redis:
            return False
        
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        if not self.redis:
            return False
        
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# Singleton
cache = CacheService()

