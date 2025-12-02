"""
Distributed rate limiter using Redis.
Coordinates rate limiting across multiple Celery workers.
"""
import redis
import time
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class DistributedRateLimiter:
    """
    Rate limiter that works across multiple Celery workers.
    Uses Redis to coordinate rate limiting.
    """
    
    def __init__(self, key: str = "sp_api", requests_per_second: int = 5):
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=False)
            self.key = f"rate_limit:{key}"
            self.requests_per_second = requests_per_second
            self.window_ms = 1000  # 1 second window
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiter: {e}")
            self.redis = None
    
    def wait(self):
        """Wait if needed to respect rate limit across all workers."""
        if not self.redis:
            # Fallback: simple sleep if Redis unavailable
            time.sleep(1.0 / self.requests_per_second)
            return
        
        while True:
            try:
                now_ms = int(time.time() * 1000)
                window_start = now_ms - self.window_ms
                
                # Remove old entries
                self.redis.zremrangebyscore(self.key, 0, window_start)
                
                # Count requests in current window
                current_count = self.redis.zcard(self.key)
                
                if current_count < self.requests_per_second:
                    # Add this request
                    request_id = f"{now_ms}:{os.getpid()}:{time.time()}"
                    self.redis.zadd(self.key, {request_id: now_ms})
                    self.redis.expire(self.key, 2)  # Auto-cleanup
                    return
                
                # Wait a bit and retry
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"Rate limiter error: {e}, falling back to sleep")
                time.sleep(1.0 / self.requests_per_second)
                return
    
    def acquire(self) -> bool:
        """Try to acquire a rate limit slot. Returns False if limit exceeded."""
        if not self.redis:
            return True  # Allow if Redis unavailable
        
        try:
            now_ms = int(time.time() * 1000)
            window_start = now_ms - self.window_ms
            
            self.redis.zremrangebyscore(self.key, 0, window_start)
            current_count = self.redis.zcard(self.key)
            
            if current_count < self.requests_per_second:
                request_id = f"{now_ms}:{os.getpid()}:{time.time()}"
                self.redis.zadd(self.key, {request_id: now_ms})
                self.redis.expire(self.key, 2)
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Rate limiter acquire error: {e}")
            return True  # Allow if error


# Global instances
sp_api_limiter = DistributedRateLimiter("sp_api", requests_per_second=8)
keepa_limiter = DistributedRateLimiter("keepa", requests_per_second=5)

