"""
User-related Pydantic schemas
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, validator, Field
from uuid import UUID

from app.models.user import UserRole, RegistrationStatus


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    phone: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$')
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole


class UserCreate(UserBase):
    """User creation schema"""
    password: Optional[str] = Field(None, min_length=8)
    
    @validator('password')
    def validate_password(cls, v, values):
        if values.get('role') in [UserRole.AGENT, UserRole.ADMIN] and not v:
            raise ValueError('Password is required for agents and admins')
        return v


class UserUpdate(BaseModel):
    """User update schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')
    profile_picture_url: Optional[str] = None


class UserResponse(UserBase):
    """User response schema"""
    id: UUID
    is_verified: bool
    is_active: bool
    registration_status: RegistrationStatus
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str
    remember_me: bool = False


class UserProfile(BaseModel):
    """Complete user profile schema"""
    id: UUID
    email: str
    phone: str
    first_name: str
    last_name: str
    full_name: str
    role: UserRole
    profile_picture_url: Optional[str] = None
    is_verified: bool
    is_active: bool
    registration_status: RegistrationStatus
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    # Role-specific profile data
    agent_profile: Optional[Dict[str, Any]] = None
    customer_profile: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    """Password change schema"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordReset(BaseModel):
    """Password reset schema"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class AgentRegistration(UserCreate):
    """Agent registration schema"""
    role: UserRole = UserRole.AGENT
    agency_name: str = Field(..., min_length=1, max_length=255)
    rera_license: Optional[str] = Field(None, max_length=50)
    service_areas: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=50)


class CustomerRegistration(UserBase):
    """Customer registration schema (OTP-based, no password)"""
    role: UserRole = UserRole.CUSTOMER
    looking_for: Optional[str] = Field("rent", regex=r'^(rent|buy|both)$')
    preferred_locations: Optional[List[str]] = None


class FieldExecutiveCreate(UserCreate):
    """Field executive creation schema (admin only)"""
    role: UserRole = UserRole.FIELD_EXECUTIVE
    assigned_areas: Optional[List[str]] = None


class UserApproval(BaseModel):
    """User approval schema"""
    user_id: UUID
    approved: bool
    rejection_reason: Optional[str] = None