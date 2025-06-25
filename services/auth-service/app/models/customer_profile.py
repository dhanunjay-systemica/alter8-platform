"""
Customer profile model
"""

from datetime import datetime, date
from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Boolean, Date, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class LookingFor(str, enum.Enum):
    """What customer is looking for"""
    RENT = "rent"
    BUY = "buy"
    BOTH = "both"


class VerificationLevel(str, enum.Enum):
    """Customer verification levels"""
    PHONE_VERIFIED = "phone_verified"
    EMAIL_VERIFIED = "email_verified"
    DOCUMENT_VERIFIED = "document_verified"
    FULLY_VERIFIED = "fully_verified"


class CustomerProfile(Base):
    """Customer profile model"""
    __tablename__ = "customer_profiles"
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        primary_key=True
    )
    
    # Personal information
    date_of_birth = Column(Date, nullable=True)
    occupation = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    monthly_income = Column(DECIMAL(10, 2), nullable=True)
    
    # Contact preferences
    preferred_contact_method = Column(String(20), default="whatsapp")
    communication_language = Column(String(10), default="en")
    contact_hours_start = Column(String(5), default="09:00")  # HH:MM format
    contact_hours_end = Column(String(5), default="21:00")
    
    # Property preferences
    looking_for = Column(
        ENUM(LookingFor, name="customer_looking_for"),
        default=LookingFor.RENT
    )
    budget_min = Column(DECIMAL(10, 2), nullable=True)
    budget_max = Column(DECIMAL(10, 2), nullable=True)
    preferred_locations = Column(JSONB, nullable=True)  # Array of location objects
    property_requirements = Column(JSONB, nullable=True)  # Bedrooms, amenities, etc.
    
    # Family information
    family_size = Column(String(20), nullable=True)  # "1", "2-3", "4-5", "6+"
    has_pets = Column(Boolean, default=False)
    pet_details = Column(Text, nullable=True)
    
    # Lifestyle preferences
    preferred_furnishing = Column(String(20), nullable=True)  # furnished, semi-furnished, unfurnished
    move_in_date = Column(Date, nullable=True)
    lease_duration_preferred = Column(String(20), nullable=True)  # "6 months", "1 year", "2+ years"
    
    # Verification and privacy
    verification_level = Column(
        ENUM(VerificationLevel, name="customer_verification_level"),
        default=VerificationLevel.PHONE_VERIFIED
    )
    privacy_settings = Column(JSONB, nullable=True)
    data_sharing_consent = Column(Boolean, default=False)
    marketing_consent = Column(Boolean, default=False)
    
    # Identity verification
    id_proof_type = Column(String(50), nullable=True)  # aadhar, pan, passport, etc.
    id_proof_number = Column(String(50), nullable=True)
    id_proof_verified = Column(Boolean, default=False)
    id_proof_verified_at = Column(DateTime, nullable=True)
    
    # Address proof
    address_proof_type = Column(String(50), nullable=True)
    address_proof_verified = Column(Boolean, default=False)
    address_proof_verified_at = Column(DateTime, nullable=True)
    
    # Current address
    current_address_line1 = Column(String(255), nullable=True)
    current_address_line2 = Column(String(255), nullable=True)
    current_city = Column(String(100), nullable=True)
    current_state = Column(String(100), nullable=True)
    current_pincode = Column(String(10), nullable=True)
    
    # Emergency contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relation = Column(String(50), nullable=True)
    
    # Search and interaction history
    total_searches = Column(DECIMAL(10, 0), default=0)
    total_property_views = Column(DECIMAL(10, 0), default=0)
    total_shortlisted = Column(DECIMAL(10, 0), default=0)
    total_inquiries = Column(DECIMAL(10, 0), default=0)
    
    # Preferences learned from behavior
    preferred_property_types = Column(JSONB, nullable=True)  # Based on search history
    preferred_amenities = Column(JSONB, nullable=True)
    search_radius_km = Column(DECIMAL(5, 2), default=5.0)
    
    # Engagement metrics
    last_search_at = Column(DateTime, nullable=True)
    last_property_view_at = Column(DateTime, nullable=True)
    last_inquiry_at = Column(DateTime, nullable=True)
    avg_session_duration = Column(DECIMAL(10, 2), default=0.0)  # in minutes
    
    # Referral information
    referred_by_agent_id = Column(UUID(as_uuid=True), nullable=True)
    referral_code_used = Column(String(50), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    user = relationship("User", back_populates="customer_profile")
    
    def __repr__(self):
        return f"<CustomerProfile(user_id={self.user_id}, looking_for={self.looking_for})>"
    
    @property
    def profile_completion_percentage(self) -> int:
        """Calculate profile completion percentage"""
        total_fields = 15
        completed_fields = 0
        
        # Basic info
        if self.date_of_birth:
            completed_fields += 1
        if self.occupation:
            completed_fields += 1
        if self.monthly_income:
            completed_fields += 1
        
        # Preferences
        if self.budget_min and self.budget_max:
            completed_fields += 1
        if self.preferred_locations:
            completed_fields += 1
        if self.property_requirements:
            completed_fields += 1
        if self.move_in_date:
            completed_fields += 1
        
        # Contact info
        if self.current_address_line1:
            completed_fields += 1
        if self.emergency_contact_name and self.emergency_contact_phone:
            completed_fields += 1
        
        # Identity verification
        if self.id_proof_verified:
            completed_fields += 2
        if self.address_proof_verified:
            completed_fields += 2
        
        # Additional details
        if self.family_size:
            completed_fields += 1
        if self.preferred_furnishing:
            completed_fields += 1
        if self.lease_duration_preferred:
            completed_fields += 1
        
        return min(int((completed_fields / total_fields) * 100), 100)
    
    @property
    def is_eligible_for_premium_properties(self) -> bool:
        """Check if customer is eligible for premium property access"""
        return (
            self.verification_level in [VerificationLevel.DOCUMENT_VERIFIED, VerificationLevel.FULLY_VERIFIED] and
            self.id_proof_verified and
            self.address_proof_verified and
            self.monthly_income is not None
        )