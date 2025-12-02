"""
Redis-based Token Bucket Rate Limiter for SP-API.
Implements the same algorithm SP-API uses, shared across ALL Celery workers.
"""
import redis
import time
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class TokenBucketRateLimiter:
    """
    Redis-based token bucket rate limiter.
    Implements the same algorithm SP-API uses.
    Shared across ALL Celery workers.
    """
    
    def __init__(self, name: str, rate: float, burst: int):
        """
        Args:
            name: Unique identifier for this limiter
            rate: Tokens added per second
            burst: Maximum bucket size
        """
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.name = name
        self.rate = rate  # tokens per second
        self.burst = burst  # max tokens
        self.key_tokens = f"ratelimit:{name}:tokens"
        self.key_last_update = f"ratelimit:{name}:last_update"
    
    def _refill(self) -> float:
        """Refill tokens based on time elapsed. Returns current token count."""
        now = time.time()
        
        # Get current state atomically
        pipe = self.redis.pipeline()
        pipe.get(self.key_tokens)
        pipe.get(self.key_last_update)
        tokens_raw, last_update_raw = pipe.execute()
        
        tokens = float(tokens_raw) if tokens_raw else self.burst
        last_update = float(last_update_raw) if last_update_raw else now
        
        # Calculate tokens to add
        elapsed = now - last_update
        tokens_to_add = elapsed * self.rate
        new_tokens = min(self.burst, tokens + tokens_to_add)
        
        # Update state
        pipe = self.redis.pipeline()
        pipe.set(self.key_tokens, new_tokens)
        pipe.set(self.key_last_update, now)
        pipe.expire(self.key_tokens, 300)  # 5 min expiry
        pipe.expire(self.key_last_update, 300)
        pipe.execute()
        
        return new_tokens
    
    def acquire(self, tokens: int = 1, timeout: float = 120) -> bool:
        """
        Acquire tokens from the bucket. Blocks until available or timeout.
        
        Args:
            tokens: Number of tokens needed (usually 1)
            timeout: Max seconds to wait
        
        Returns:
            True if tokens acquired, False if timeout
        """
        start = time.time()
        
        while time.time() - start < timeout:
            # Refill and get current tokens
            current_tokens = self._refill()
            
            if current_tokens >= tokens:
                # Try to consume tokens atomically
                new_tokens = self.redis.incrbyfloat(self.key_tokens, -tokens)
                
                if new_tokens >= 0:
                    logger.debug(f"[{self.name}] Acquired {tokens} token(s), {new_tokens:.2f} remaining")
                    return True
                else:
                    # Race condition - restore and retry
                    self.redis.incrbyfloat(self.key_tokens, tokens)
            
            # Calculate wait time until next token
            wait_time = (tokens - current_tokens) / self.rate if current_tokens < tokens else 0.1
            wait_time = min(wait_time, 2.0)  # Cap at 2 seconds
            
            logger.debug(f"[{self.name}] Waiting {wait_time:.2f}s for tokens ({current_tokens:.2f}/{self.burst})")
            time.sleep(wait_time)
        
        logger.warning(f"[{self.name}] Timeout waiting for {tokens} tokens")
        return False
    
    def get_status(self) -> dict:
        """Get current bucket status."""
        tokens = self._refill()
        return {
            "name": self.name,
            "tokens": round(tokens, 2),
            "burst": self.burst,
            "rate": self.rate
        }


class KeepaTokenLimiter:
    """
    Keepa uses tokens-per-minute model.
    Tokens refill every minute based on plan.
    """
    
    def __init__(self, tokens_per_minute: int = 10):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.tokens_per_minute = tokens_per_minute
        self.key_tokens = "ratelimit:keepa:tokens"
        self.key_last_refill = "ratelimit:keepa:last_refill"
    
    def _refill_if_needed(self) -> int:
        """Refill tokens if a minute has passed."""
        now = time.time()
        last_refill = self.redis.get(self.key_last_refill)
        last_refill = float(last_refill) if last_refill else 0
        
        # Refill every 60 seconds
        if now - last_refill >= 60:
            self.redis.set(self.key_tokens, self.tokens_per_minute)
            self.redis.set(self.key_last_refill, now)
            return self.tokens_per_minute
        
        tokens = self.redis.get(self.key_tokens)
        return int(tokens) if tokens else self.tokens_per_minute
    
    def acquire(self, tokens: int = 1, timeout: float = 300) -> bool:
        """Acquire Keepa tokens. Each ASIN costs 1 token."""
        start = time.time()
        
        while time.time() - start < timeout:
            current = self._refill_if_needed()
            
            if current >= tokens:
                new_val = self.redis.decrby(self.key_tokens, tokens)
                if new_val >= 0:
                    logger.debug(f"[keepa] Acquired {tokens} tokens, {new_val} remaining")
                    return True
                else:
                    self.redis.incrby(self.key_tokens, tokens)
            
            # Wait for next refill
            last_refill = float(self.redis.get(self.key_last_refill) or 0)
            wait_until_refill = 60 - (time.time() - last_refill)
            wait = max(1, min(wait_until_refill, 10))
            logger.info(f"[keepa] Waiting {wait:.0f}s for tokens ({current}/{self.tokens_per_minute})")
            time.sleep(wait)
        
        return False


# Per-endpoint rate limiters (matching SP-API limits)
rate_limiters = {
    "competitive_pricing": TokenBucketRateLimiter("sp_competitive_pricing", rate=0.5, burst=1),
    "item_offers": TokenBucketRateLimiter("sp_item_offers", rate=0.5, burst=1),
    "fees_estimate": TokenBucketRateLimiter("sp_fees_estimate", rate=0.5, burst=1),
    "catalog": TokenBucketRateLimiter("sp_catalog", rate=2.0, burst=2),
}

# Global rate limiters - shared across all workers
sp_api_pricing_limiter = TokenBucketRateLimiter("sp_pricing", rate=0.5, burst=1)
sp_api_fees_limiter = TokenBucketRateLimiter("sp_fees", rate=0.5, burst=1)
keepa_limiter = KeepaTokenLimiter(tokens_per_minute=10)  # Adjust based on your plan


class KeepaTokenLimiter:
    """
    Keepa uses tokens-per-minute model.
    Tokens refill every minute based on plan.
    """
    
    def __init__(self, tokens_per_minute: int = 10):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.tokens_per_minute = tokens_per_minute
        self.key_tokens = "ratelimit:keepa:tokens"
        self.key_last_refill = "ratelimit:keepa:last_refill"
    
    def _refill_if_needed(self) -> int:
        """Refill tokens if a minute has passed."""
        now = time.time()
        last_refill = self.redis.get(self.key_last_refill)
        last_refill = float(last_refill) if last_refill else 0
        
        # Refill every 60 seconds
        if now - last_refill >= 60:
            self.redis.set(self.key_tokens, self.tokens_per_minute)
            self.redis.set(self.key_last_refill, now)
            return self.tokens_per_minute
        
        tokens = self.redis.get(self.key_tokens)
        return int(tokens) if tokens else self.tokens_per_minute
    
    def acquire(self, tokens: int = 1, timeout: float = 300) -> bool:
        """Acquire Keepa tokens. Each ASIN costs 1 token."""
        start = time.time()
        
        while time.time() - start < timeout:
            current = self._refill_if_needed()
            
            if current >= tokens:
                new_val = self.redis.decrby(self.key_tokens, tokens)
                if new_val >= 0:
                    logger.debug(f"[keepa] Acquired {tokens} tokens, {new_val} remaining")
                    return True
                else:
                    self.redis.incrby(self.key_tokens, tokens)
            
            # Wait for next refill
            last_refill = float(self.redis.get(self.key_last_refill) or 0)
            wait_until_refill = 60 - (time.time() - last_refill)
            wait = max(1, min(wait_until_refill, 10))
            logger.info(f"[keepa] Waiting {wait:.0f}s for tokens ({current}/{self.tokens_per_minute})")
            time.sleep(wait)
        
        return False


# Global rate limiters - shared across all workers
sp_api_pricing_limiter = TokenBucketRateLimiter("sp_pricing", rate=0.5, burst=1)
sp_api_fees_limiter = TokenBucketRateLimiter("sp_fees", rate=0.5, burst=1)
keepa_limiter = KeepaTokenLimiter(tokens_per_minute=10)  # Adjust based on your plan


def get_limiter(endpoint: str) -> TokenBucketRateLimiter:
    """Get rate limiter for an endpoint."""
    return rate_limiters.get(endpoint, rate_limiters["competitive_pricing"])

