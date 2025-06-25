"""
OTP verification model
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, DateTime, String, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.core.config import settings


class OTPType(str, enum.Enum):
    """OTP types"""
    PHONE_VERIFICATION = "phone_verification"
    EMAIL_VERIFICATION = "email_verification"
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"
    PROPERTY_ACCESS = "property_access"
    TRANSACTION = "transaction"


class OTPStatus(str, enum.Enum):
    """OTP status"""
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"


class OTPVerification(Base):
    """OTP verification model"""
    __tablename__ = "otp_verifications"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    # OTP details
    otp_code = Column(String(10), nullable=False)
    otp_type = Column(
        ENUM(OTPType, name="otp_type"),
        nullable=False,
        index=True
    )
    
    # Contact information
    phone_number = Column(String(20), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    
    # User association (optional - customers might not have user accounts)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Status and timing
    status = Column(
        ENUM(OTPStatus, name="otp_status"),
        default=OTPStatus.PENDING,
        index=True
    )
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Context information
    context_data = Column(String(500), nullable=True)  # JSON string for additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Delivery information
    delivery_method = Column(String(20), nullable=False)  # whatsapp, sms, email
    delivery_status = Column(String(20), default="pending")  # pending, sent, delivered, failed
    delivery_attempt_count = Column(Integer, default=0)
    delivery_error = Column(String(500), nullable=True)
    
    # Security features
    rate_limit_key = Column(String(100), nullable=True, index=True)  # For rate limiting
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<OTPVerification(id={self.id}, type={self.otp_type}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if OTP is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if OTP is valid for verification"""
        return (
            self.status == OTPStatus.PENDING and
            not self.is_expired and
            self.attempts < self.max_attempts
        )
    
    @property
    def time_remaining(self) -> int:
        """Get remaining time in seconds"""
        if self.is_expired:
            return 0
        remaining = self.expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds()))
    
    def verify(self, provided_otp: str) -> bool:
        """Verify the provided OTP"""
        self.attempts += 1
        self.updated_at = datetime.utcnow()
        
        if not self.is_valid:
            self.status = OTPStatus.EXPIRED if self.is_expired else OTPStatus.FAILED
            return False
        
        if self.otp_code == provided_otp:
            self.status = OTPStatus.VERIFIED
            self.verified_at = datetime.utcnow()
            return True
        
        if self.attempts >= self.max_attempts:
            self.status = OTPStatus.FAILED
        
        return False
    
    @classmethod
    def create_otp(
        cls,
        otp_type: OTPType,
        otp_code: str,
        phone_number: str = None,
        email: str = None,
        user_id: str = None,
        context_data: str = None,
        delivery_method: str = "whatsapp",
        expire_minutes: int = None
    ) -> "OTPVerification":
        """Create a new OTP verification record"""
        
        if expire_minutes is None:
            expire_minutes = settings.OTP_EXPIRE_MINUTES
        
        expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
        
        return cls(
            otp_code=otp_code,
            otp_type=otp_type,
            phone_number=phone_number,
            email=email,
            user_id=user_id,
            context_data=context_data,
            delivery_method=delivery_method,
            expires_at=expires_at,
            max_attempts=settings.OTP_MAX_ATTEMPTS
        )