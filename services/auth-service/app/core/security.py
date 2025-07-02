"""
Security utilities for JWT tokens, password hashing, and authentication
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Any

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.auth import TokenData

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow()
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(subject: str | Any) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> TokenData | None:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id = payload.get("sub")
        role = payload.get("role")

        if user_id is None:
            return None

        token_data = TokenData(user_id=user_id, role=role)
        return token_data

    except (JWTError, ValidationError) as e:
        logger.warning("Token verification failed", error=str(e))
        return None


async def verify_token_with_blacklist(token: str) -> TokenData | None:
    """Verify JWT token and check if it's blacklisted"""
    try:
        # First verify token structure and signature
        token_data = verify_token(token)
        if not token_data:
            return None

        # Check if token is blacklisted
        from app.services.token_service import token_service
        if await token_service.is_token_blacklisted(token):
            logger.warning("Blacklisted token used", user_id=token_data.user_id)
            return None

        return token_data

    except Exception as e:
        logger.warning("Token verification with blacklist failed", error=str(e))
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def generate_otp(length: int = None) -> str:
    """Generate numeric OTP"""
    if length is None:
        length = settings.OTP_LENGTH

    digits = string.digits
    otp = ''.join(secrets.choice(digits) for _ in range(length))
    return otp


def generate_secure_token(length: int = 32) -> str:
    """Generate secure random token for password resets, etc."""
    return secrets.token_urlsafe(length)


def validate_password_strength(password: str) -> dict[str, Any]:
    """Validate password against security policy"""
    errors = []

    if len(password) < settings.MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters")

    if settings.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if settings.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if settings.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    if settings.REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
