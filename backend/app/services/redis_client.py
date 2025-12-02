"""
Redis client for caching and performance optimization.
"""
import redis
import json
from typing import Optional, Any, Union
from functools import wraps
import hashlib
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Redis connection pool
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client."""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    redis_url = getattr(settings, 'REDIS_URL', None)
    if not redis_url:
        logger.warning("REDIS_URL not configured, caching disabled")
        return None
    
    try:
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        # Test connection
        _redis_client.ping()
        logger.info("✅ Redis connected successfully")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}, caching disabled")
        return None


def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from prefix and arguments."""
    key_parts = [prefix]
    if args:
        key_parts.extend(str(arg) for arg in args)
    if kwargs:
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    # Hash if too long
    if len(key_string) > 200:
        key_string = prefix + ":" + hashlib.md5(key_string.encode()).hexdigest()
    return key_string


def cached(ttl: int = 300, key_prefix: str = None):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds (default 5 minutes)
        key_prefix: Prefix for cache key (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            client = get_redis_client()
            if not client:
                # Redis not available, just call function
                return await func(*args, **kwargs)
            
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key_str = cache_key(prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                cached_value = client.get(cache_key_str)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key_str}")
                    return json.loads(cached_value)
                
                # Cache miss, call function
                logger.debug(f"Cache MISS: {cache_key_str}")
                result = await func(*args, **kwargs)
                
                # Store in cache
                if result is not None:
                    client.setex(
                        cache_key_str,
                        ttl,
                        json.dumps(result, default=str)
                    )
                
                return result
            except Exception as e:
                logger.warning(f"Cache error for {cache_key_str}: {e}")
                # On cache error, just call function
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class CacheService:
    """Service for Redis caching operations."""
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Get value from cache."""
        client = get_redis_client()
        if not client:
            return None
        
        try:
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        client = get_redis_client()
        if not client:
            return False
        
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache."""
        client = get_redis_client()
        if not client:
            return False
        
        try:
            client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """Delete all keys matching pattern."""
        client = get_redis_client()
        if not client:
            return 0
        
        try:
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    @staticmethod
    def clear_user_cache(user_id: str):
        """Clear all cache entries for a user."""
        CacheService.delete_pattern(f"user:{user_id}:*")
    
    @staticmethod
    def invalidate_subscription_cache(user_id: str):
        """Invalidate subscription-related cache for user."""
        CacheService.delete_pattern(f"subscription:{user_id}:*")
        CacheService.delete_pattern(f"tier:{user_id}:*")
        CacheService.delete_pattern(f"limits:{user_id}:*")


# Singleton instance
cache_service = CacheService()

