"""
Redis client configuration and utilities
"""

import json
from typing import Any, Optional
import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Global Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if redis_client is None:
        await init_redis()
    return redis_client


class RedisService:
    """Redis service with common operations"""
    
    def __init__(self):
        self.client = None
    
    async def get_client(self) -> redis.Redis:
        """Get Redis client"""
        if self.client is None:
            self.client = await get_redis()
        return self.client
    
    async def set_with_expiry(
        self, 
        key: str, 
        value: Any, 
        expiry_seconds: int
    ) -> bool:
        """Set key with expiration"""
        client = await self.get_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await client.setex(key, expiry_seconds, value)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        client = await self.get_client()
        return await client.get(key)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value by key"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        client = await self.get_client()
        return bool(await client.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        client = await self.get_client()
        return bool(await client.exists(key))
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        client = await self.get_client()
        return await client.incrby(key, amount)
    
    async def set_if_not_exists(self, key: str, value: Any, expiry_seconds: int = None) -> bool:
        """Set key only if it doesn't exist"""
        client = await self.get_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        if expiry_seconds:
            return await client.set(key, value, nx=True, ex=expiry_seconds)
        else:
            return await client.setnx(key, value)


# Global Redis service instance
redis_service = RedisService()


# Helper functions for common patterns
async def cache_user_session(user_id: str, session_data: dict, expiry_seconds: int = None) -> bool:
    """Cache user session data"""
    if expiry_seconds is None:
        expiry_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    key = f"session:{user_id}"
    return await redis_service.set_with_expiry(key, session_data, expiry_seconds)


async def get_user_session(user_id: str) -> Optional[dict]:
    """Get user session data"""
    key = f"session:{user_id}"
    return await redis_service.get_json(key)


async def invalidate_user_session(user_id: str) -> bool:
    """Invalidate user session"""
    key = f"session:{user_id}"
    return await redis_service.delete(key)


async def store_otp(phone_number: str, otp: str, expiry_seconds: int = None) -> bool:
    """Store OTP for phone number"""
    if expiry_seconds is None:
        expiry_seconds = settings.OTP_EXPIRE_MINUTES * 60
    
    key = f"otp:{phone_number}"
    return await redis_service.set_with_expiry(key, otp, expiry_seconds)


async def verify_otp(phone_number: str, provided_otp: str) -> bool:
    """Verify OTP for phone number"""
    key = f"otp:{phone_number}"
    stored_otp = await redis_service.get(key)
    
    if stored_otp and stored_otp == provided_otp:
        await redis_service.delete(key)  # OTP can only be used once
        return True
    return False


async def track_login_attempts(identifier: str, max_attempts: int = None) -> tuple[int, bool]:
    """Track login attempts and return (current_attempts, is_locked)"""
    if max_attempts is None:
        max_attempts = settings.MAX_LOGIN_ATTEMPTS
    
    key = f"login_attempts:{identifier}"
    attempts = await redis_service.increment(key)
    
    if attempts == 1:
        # Set expiry for first attempt
        client = await redis_service.get_client()
        await client.expire(key, settings.LOCKOUT_DURATION_MINUTES * 60)
    
    is_locked = attempts > max_attempts
    return attempts, is_locked


async def reset_login_attempts(identifier: str) -> bool:
    """Reset login attempts counter"""
    key = f"login_attempts:{identifier}"
    return await redis_service.delete(key)