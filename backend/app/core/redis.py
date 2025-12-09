"""
Redis client wrapper for caching with connection pooling and graceful fallback.
Optimized for high-performance caching of API responses.
"""
import os
import json
import logging
from typing import Optional, Any, Dict
import redis
from redis.connection import ConnectionPool

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None
_redis_enabled: bool = False
_redis_connected: bool = False


def _initialize_redis() -> Optional[redis.Redis]:
    """
    Initialize Redis client with connection pooling.
    
    Returns:
        Redis client instance or None if unavailable
    """
    global _redis_client, _redis_enabled, _redis_connected
    
    # Check if already initialized
    if _redis_client is not None:
        return _redis_client
    
    # Get Redis URL from environment
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("⚠️  REDIS_URL not set - caching disabled")
        _redis_enabled = False
        _redis_connected = False
        return None
    
    _redis_enabled = True
    
    try:
        # Create connection pool for better performance
        pool = ConnectionPool.from_url(
            redis_url,
            max_connections=10,
            socket_timeout=2,
            socket_connect_timeout=2,
            socket_keepalive=True,
            decode_responses=True,
            health_check_interval=30
        )
        
        # Create Redis client with connection pool
        _redis_client = redis.Redis(connection_pool=pool)
        
        # Test connection with ping
        _redis_client.ping()
        
        _redis_connected = True
        logger.info("✅ Redis connected successfully")
        logger.info(f"   Connection pool: max_connections=10")
        logger.info(f"   Timeouts: socket=2s, connect=2s")
        logger.info(f"   Health check: every 30s")
        
        return _redis_client
    
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        logger.warning("   Caching disabled - application will work without cache")
        _redis_enabled = True  # Enabled but not connected
        _redis_connected = False
        _redis_client = None
        return None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client instance (lazy initialization).
    
    Returns:
        Redis client or None if unavailable
    """
    if _redis_client is None:
        return _initialize_redis()
    return _redis_client


def get_cached(key: str) -> Optional[Any]:
    """
    Get value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Parsed JSON value or None if not found/error
    """
    client = get_redis_client()
    if not client or not _redis_connected:
        return None
    
    try:
        value = client.get(key)
        if value is None:
            logger.debug(f"Cache MISS: {key}")
            return None
        
        logger.debug(f"Cache HIT: {key}")
        return json.loads(value)
    
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️  Failed to decode cached value for {key}: {e}")
        return None
    except Exception as e:
        logger.warning(f"⚠️  Redis get error for {key}: {e}")
        return None


def set_cached(key: str, value: Any, ttl_seconds: int = 10) -> bool:
    """
    Store value in cache with TTL.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl_seconds: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client or not _redis_connected:
        return False
    
    try:
        json_value = json.dumps(value, default=str)
        client.setex(key, ttl_seconds, json_value)
        logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
        return True
    
    except (TypeError, ValueError) as e:
        logger.warning(f"⚠️  Failed to serialize value for {key}: {e}")
        return False
    except Exception as e:
        logger.warning(f"⚠️  Redis set error for {key}: {e}")
        return False


def delete_cached(key: str) -> bool:
    """
    Delete key from cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client or not _redis_connected:
        return False
    
    try:
        result = client.delete(key)
        if result > 0:
            logger.debug(f"Cache DELETE: {key}")
        return result > 0
    
    except Exception as e:
        logger.warning(f"⚠️  Redis delete error for {key}: {e}")
        return False


def get_cache_info(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get cache statistics and status.
    
    Args:
        user_id: Optional user ID to check if their stats are cached
        
    Returns:
        Dictionary with cache info
    """
    global _redis_enabled, _redis_connected
    
    info: Dict[str, Any] = {
        "enabled": _redis_enabled,
        "connected": _redis_connected,
        "hit_rate": None,
        "memory_usage": None,
        "user_cached": False,
        "cache_key": None
    }
    
    if not _redis_enabled:
        return info
    
    client = get_redis_client()
    if not client or not _redis_connected:
        return info
    
    try:
        # Get Redis info
        redis_info = client.info("memory")
        info["memory_usage"] = {
            "used_memory_human": redis_info.get("used_memory_human", "N/A"),
            "used_memory_peak_human": redis_info.get("used_memory_peak_human", "N/A")
        }
        
        # Check if user's stats are cached
        if user_id:
            cache_key = f"asin_stats:{user_id}"
            info["cache_key"] = cache_key
            info["user_cached"] = client.exists(cache_key) > 0
            if info["user_cached"]:
                ttl = client.ttl(cache_key)
                info["ttl_seconds"] = ttl if ttl > 0 else 0
        
        # Get hit/miss stats (if available)
        stats = client.info("stats")
        keyspace_hits = stats.get("keyspace_hits", 0)
        keyspace_misses = stats.get("keyspace_misses", 0)
        total_requests = keyspace_hits + keyspace_misses
        
        if total_requests > 0:
            info["hit_rate"] = round((keyspace_hits / total_requests) * 100, 2)
            info["keyspace_hits"] = keyspace_hits
            info["keyspace_misses"] = keyspace_misses
    
    except Exception as e:
        logger.warning(f"⚠️  Failed to get cache info: {e}")
    
    return info


# Initialize Redis on module import
_initialize_redis()

