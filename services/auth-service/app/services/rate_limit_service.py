"""
Rate limiting service for API protection
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import HTTPException, status
from app.core.redis_client import get_redis

logger = structlog.get_logger()


class RateLimitService:
    """Rate limiting service class"""
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP, user_id)
            limit: Maximum number of requests allowed
            window: Time window in seconds
        
        Returns:
            True if within limit, raises HTTPException if exceeded
        """
        try:
            redis_client = await get_redis()
            
            # Get current count
            current_count = await redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            if current_count >= limit:
                # Rate limit exceeded
                ttl = await redis_client.ttl(key)
                logger.warning("Rate limit exceeded", 
                             key=key, 
                             limit=limit, 
                             current_count=current_count,
                             ttl=ttl)
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                    headers={"Retry-After": str(ttl)}
                )
            
            # Increment counter
            await redis_client.incr(key)
            
            # Set expiration if this is the first request
            if current_count == 0:
                await redis_client.expire(key, window)
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            # Fail open - allow request if rate limiting fails
            return True
    
    async def increment_counter(self, key: str, window: int = 3600) -> int:
        """
        Increment a counter with expiration
        
        Args:
            key: Counter key
            window: Expiration time in seconds
        
        Returns:
            Current count
        """
        try:
            redis_client = await get_redis()
            
            # Get current count
            current_count = await redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Increment
            new_count = await redis_client.incr(key)
            
            # Set expiration if this is the first increment
            if current_count == 0:
                await redis_client.expire(key, window)
            
            return new_count
            
        except Exception as e:
            logger.error("Counter increment failed", error=str(e))
            return 0
    
    async def get_remaining_time(self, key: str) -> int:
        """
        Get remaining time until rate limit resets
        
        Args:
            key: Rate limit key
        
        Returns:
            Remaining time in seconds
        """
        try:
            redis_client = await get_redis()
            ttl = await redis_client.ttl(key)
            return max(0, ttl)
        except Exception as e:
            logger.error("TTL check failed", error=str(e))
            return 0
