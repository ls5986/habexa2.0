"""Simple in-memory cache with TTL."""
import time
from typing import Any, Optional
from functools import wraps

_cache = {}

def get_cached(key: str, ttl_seconds: int = 300) -> Optional[Any]:
    """Get value from cache if not expired."""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < ttl_seconds:
            return value
        else:
            del _cache[key]
    return None

def set_cached(key: str, value: Any) -> None:
    """Set value in cache with current timestamp."""
    _cache[key] = (value, time.time())

def clear_cache(key: str = None) -> None:
    """Clear specific key or entire cache."""
    if key:
        _cache.pop(key, None)
    else:
        _cache.clear()

def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and args
            cache_key = f"{key_prefix}{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached_value = get_cached(cache_key, ttl_seconds)
            if cached_value is not None:
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            set_cached(cache_key, result)
            
            return result
        return wrapper
    return decorator

