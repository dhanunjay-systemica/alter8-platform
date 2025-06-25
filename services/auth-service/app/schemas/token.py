"""
Token-related Pydantic schemas
"""

from typing import Optional, Any, Dict
from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload schema"""
    sub: str  # User ID
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: str  # Token type (access, refresh)
    role: Optional[str] = None
    permissions: Optional[list[str]] = None
    session_id: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class TokenValidationResponse(BaseModel):
    """Token validation response schema"""
    valid: bool
    user_id: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[list[str]] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None