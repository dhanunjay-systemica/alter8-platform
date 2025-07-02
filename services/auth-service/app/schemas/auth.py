"""
Authentication schemas for request and response models
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
import re

from app.models.user import UserRole, RegistrationStatus


class AgentRegistrationRequest(BaseModel):
    """Agent registration request schema"""
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    # Agent-specific fields
    agency_name: str = Field(..., min_length=1, max_length=255)
    rera_license: Optional[str] = Field(None, max_length=100)
    experience_years: int = Field(..., ge=0, le=50)
    specializations: list[str] = Field(default_factory=list)
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Remove any non-digit characters
        phone_digits = re.sub(r'\D', '', v)
        
        # Check if it's a valid Indian mobile number
        if not re.match(r'^[6-9]\d{9}$', phone_digits):
            raise ValueError('Please enter a valid 10-digit Indian mobile number')
        
        return f"+91{phone_digits}"
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        return v


class FieldExecutiveRegistrationRequest(BaseModel):
    """Field executive registration request schema"""
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    temporary_password: str = Field(..., min_length=8, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    # Field executive specific fields
    employee_id: str = Field(..., min_length=1, max_length=50)
    assigned_areas: list[str] = Field(default_factory=list)
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        phone_digits = re.sub(r'\D', '', v)
        if not re.match(r'^[6-9]\d{9}$', phone_digits):
            raise ValueError('Please enter a valid 10-digit Indian mobile number')
        return f"+91{phone_digits}"


class UserRegistrationResponse(BaseModel):
    """User registration response schema"""
    id: str
    email: str
    phone: str
    first_name: str
    last_name: str
    role: UserRole
    registration_status: RegistrationStatus
    message: str


class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: str
    phone: str
    first_name: str
    last_name: str
    role: UserRole
    is_verified: bool
    profile_picture_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class TokenData(BaseModel):
    """Token data schema"""
    user_id: Optional[str] = None
    role: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """Password change request schema"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=50)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=50)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        return v


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str
