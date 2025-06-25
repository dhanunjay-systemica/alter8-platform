"""
OTP-related Pydantic schemas
"""

from typing import Optional
from pydantic import BaseModel, Field, validator

from app.models.otp_verification import OTPType


class OTPRequest(BaseModel):
    """OTP request schema"""
    phone_number: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')
    email: Optional[str] = None
    otp_type: OTPType
    delivery_method: str = Field("whatsapp", regex=r'^(whatsapp|sms|email)$')
    context_data: Optional[str] = None
    
    @validator('phone_number', 'email')
    def validate_contact_info(cls, v, values, field):
        phone = values.get('phone_number') if field.name == 'email' else v
        email = values.get('email') if field.name == 'phone_number' else v
        
        if not phone and not email:
            raise ValueError('Either phone_number or email must be provided')
        
        return v


class OTPVerify(BaseModel):
    """OTP verification schema"""
    phone_number: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')
    email: Optional[str] = None
    otp_code: str = Field(..., min_length=4, max_length=10)
    otp_type: OTPType
    
    @validator('phone_number', 'email')
    def validate_contact_info(cls, v, values, field):
        phone = values.get('phone_number') if field.name == 'email' else v
        email = values.get('email') if field.name == 'phone_number' else v
        
        if not phone and not email:
            raise ValueError('Either phone_number or email must be provided')
        
        return v


class OTPResponse(BaseModel):
    """OTP response schema"""
    success: bool
    message: str
    expires_in: Optional[int] = None  # Seconds until expiration
    can_resend_in: Optional[int] = None  # Seconds until resend allowed
    attempts_remaining: Optional[int] = None


class OTPVerificationResult(BaseModel):
    """OTP verification result schema"""
    verified: bool
    message: str
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    verification_token: Optional[str] = None  # For property access
    expires_in: Optional[int] = None


class CustomerOTPAccess(BaseModel):
    """Customer OTP access for properties"""
    phone_number: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$')
    property_share_token: str
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)