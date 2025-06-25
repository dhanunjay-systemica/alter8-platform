"""
Agent profile model
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer, DECIMAL, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class VerificationStatus(str, enum.Enum):
    """Verification status for agents"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class AgentProfile(Base):
    """Agent profile model"""
    __tablename__ = "agent_profiles"
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        primary_key=True
    )
    
    # Agency information
    agency_name = Column(String(255), nullable=False)
    agency_address = Column(Text, nullable=True)
    agency_phone = Column(String(20), nullable=True)
    agency_email = Column(String(255), nullable=True)
    agency_website = Column(String(255), nullable=True)
    
    # RERA compliance
    rera_license = Column(String(50), unique=True, nullable=True, index=True)
    rera_expiry_date = Column(DateTime, nullable=True)
    rera_state = Column(String(100), nullable=True)
    
    # Professional details
    experience_years = Column(Integer, nullable=True)
    specialization = Column(String(255), nullable=True)  # Residential, Commercial, etc.
    languages_spoken = Column(JSONB, nullable=True)  # ["English", "Hindi", "Kannada"]
    
    # Service areas
    service_areas = Column(JSONB, nullable=True)  # Geographic areas served
    property_types = Column(JSONB, nullable=True)  # Types of properties handled
    
    # Business metrics
    commission_rate = Column(DECIMAL(5, 2), default=2.00)  # Default 2%
    total_deals_closed = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(15, 2), default=0.00)
    average_rating = Column(DECIMAL(3, 2), default=0.00)
    total_reviews = Column(Integer, default=0)
    
    # Verification and compliance
    verification_status = Column(
        ENUM(VerificationStatus, name="agent_verification_status"),
        default=VerificationStatus.PENDING,
        index=True
    )
    verification_documents = Column(JSONB, nullable=True)  # Document URLs and types
    background_check_status = Column(String(20), default="pending")
    background_check_date = Column(DateTime, nullable=True)
    
    # Bank details for payments
    bank_account_number = Column(String(20), nullable=True)
    bank_ifsc_code = Column(String(11), nullable=True)
    bank_account_holder_name = Column(String(255), nullable=True)
    bank_verified = Column(Boolean, default=False)
    
    # Contact preferences
    preferred_contact_method = Column(String(20), default="whatsapp")  # whatsapp, sms, email, call
    availability_hours = Column(JSONB, nullable=True)  # Working hours
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # Performance tracking
    response_time_avg = Column(Integer, default=0)  # Average response time in minutes
    properties_listed_count = Column(Integer, default=0)
    properties_sold_count = Column(Integer, default=0)
    properties_rented_count = Column(Integer, default=0)
    
    # Subscription and billing
    subscription_plan = Column(String(50), default="basic")
    subscription_expires_at = Column(DateTime, nullable=True)
    billing_cycle = Column(String(20), default="monthly")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    user = relationship("User", back_populates="agent_profile")
    
    def __repr__(self):
        return f"<AgentProfile(user_id={self.user_id}, agency={self.agency_name})>"
    
    @property
    def is_rera_valid(self) -> bool:
        """Check if RERA license is valid"""
        if not self.rera_license or not self.rera_expiry_date:
            return False
        return datetime.utcnow() < self.rera_expiry_date
    
    @property
    def verification_completion_percentage(self) -> int:
        """Calculate profile completion percentage"""
        required_fields = [
            self.agency_name,
            self.rera_license,
            self.service_areas,
            self.bank_account_number,
            self.bank_ifsc_code,
        ]
        
        completed_fields = sum(1 for field in required_fields if field)
        return int((completed_fields / len(required_fields)) * 100)