"""
Token management service for JWT tokens, blacklisting, and session management
"""

import hashlib
from datetime import datetime
from typing import Any

import structlog
from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis_client import redis_service
from app.core.security import create_access_token, create_refresh_token

logger = structlog.get_logger()


class TokenService:
    """Service for managing JWT tokens and blacklisting"""

    def __init__(self):
        self.redis = redis_service

    async def create_token_pair(self, user_id: str, role: str) -> dict[str, Any]:
        """Create access and refresh token pair"""
        access_token = create_access_token(
            subject=user_id,
            additional_claims={"role": role}
        )
        refresh_token = create_refresh_token(subject=user_id)

        # Store refresh token in Redis for validation
        await self._store_refresh_token(user_id, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    async def verify_refresh_token(self, refresh_token: str) -> str | None:
        """Verify refresh token and return user_id if valid"""
        try:
            # Decode token to get user_id
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id or token_type != "refresh":
                return None

            # Check if token is blacklisted
            if await self.is_token_blacklisted(refresh_token):
                logger.warning("Blacklisted refresh token used", user_id=user_id)
                return None

            # Check if token exists in Redis (valid refresh tokens)
            stored_token = await self._get_refresh_token(user_id)
            if stored_token != refresh_token:
                logger.warning("Invalid refresh token used", user_id=user_id)
                return None

            return user_id

        except JWTError as e:
            logger.warning("Invalid refresh token", error=str(e))
            return None

    async def refresh_access_token(self, refresh_token: str, user_role: str) -> dict[str, Any] | None:
        """Create new access token using refresh token"""
        user_id = await self.verify_refresh_token(refresh_token)
        if not user_id:
            return None

        # Create new access token
        access_token = create_access_token(
            subject=user_id,
            additional_claims={"role": user_role}
        )

        logger.info("Access token refreshed", user_id=user_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Keep same refresh token
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    async def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist"""
        try:
            # Decode token to get expiration
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False}  # Don't verify expiration for blacklisting
            )

            exp = payload.get("exp")
            if not exp:
                return False

            # Calculate TTL (time until token expires)
            exp_datetime = datetime.fromtimestamp(exp)
            ttl = int((exp_datetime - datetime.utcnow()).total_seconds())

            if ttl > 0:
                # Create token hash for storage efficiency
                token_hash = self._hash_token(token)
                key = f"blacklist:{token_hash}"

                await self.redis.set_with_expiry(key, "1", ttl)
                logger.info("Token blacklisted", ttl=ttl)
                return True

            return False

        except JWTError as e:
            logger.error("Failed to blacklist token", error=str(e))
            return False

    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            token_hash = self._hash_token(token)
            key = f"blacklist:{token_hash}"
            return await self.redis.exists(key)
        except Exception as e:
            logger.error("Failed to check token blacklist", error=str(e))
            return False

    async def logout_user(self, user_id: str, access_token: str, refresh_token: str) -> bool:
        """Logout user by blacklisting tokens and clearing session"""
        try:
            # Blacklist both tokens
            access_blacklisted = await self.blacklist_token(access_token)
            refresh_blacklisted = await self.blacklist_token(refresh_token)

            # Remove refresh token from Redis
            await self._remove_refresh_token(user_id)

            # Clear user session
            await self._clear_user_session(user_id)

            logger.info("User logged out", user_id=user_id)
            return access_blacklisted and refresh_blacklisted

        except Exception as e:
            logger.error("Logout failed", user_id=user_id, error=str(e))
            return False

    async def logout_all_sessions(self, user_id: str) -> bool:
        """Logout user from all sessions"""
        try:
            # Remove all refresh tokens for user
            await self._remove_all_refresh_tokens(user_id)

            # Clear user session
            await self._clear_user_session(user_id)

            logger.info("All sessions logged out", user_id=user_id)
            return True

        except Exception as e:
            logger.error("Logout all failed", user_id=user_id, error=str(e))
            return False

    def _hash_token(self, token: str) -> str:
        """Create hash of token for efficient storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    async def _store_refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """Store refresh token in Redis"""
        key = f"refresh_token:{user_id}"
        expiry = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        return await self.redis.set_with_expiry(key, refresh_token, expiry)

    async def _get_refresh_token(self, user_id: str) -> str | None:
        """Get stored refresh token for user"""
        key = f"refresh_token:{user_id}"
        return await self.redis.get(key)

    async def _remove_refresh_token(self, user_id: str) -> bool:
        """Remove refresh token for user"""
        key = f"refresh_token:{user_id}"
        return await self.redis.delete(key)

    async def _remove_all_refresh_tokens(self, user_id: str) -> bool:
        """Remove all refresh tokens for user (for logout all)"""
        # For now, same as single token removal
        # In future, could support multiple concurrent sessions
        return await self._remove_refresh_token(user_id)

    async def _clear_user_session(self, user_id: str) -> bool:
        """Clear user session data"""
        key = f"session:{user_id}"
        return await self.redis.delete(key)


# Global token service instance
token_service = TokenService()
