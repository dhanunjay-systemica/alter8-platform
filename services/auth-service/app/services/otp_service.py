"""
OTP service for handling verification operations
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import structlog
from app.core.config import settings
from app.core.redis_client import get_redis

logger = structlog.get_logger()


class OTPService:
    """OTP service class"""
    
    def generate_otp(self, length: int = None) -> str:
        """
        Generate a random OTP
        """
        length = length or settings.OTP_LENGTH
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    async def send_verification_otp(self, phone: str, email: str, purpose: str) -> bool:
        """
        Send verification OTP to phone or email
        """
        try:
            otp = self.generate_otp()
            redis_client = await get_redis()
            
            # Store OTP in Redis with expiration
            otp_key = f"otp:{purpose}:{email if '@' in email else phone}"
            await redis_client.setex(
                otp_key, 
                settings.OTP_EXPIRE_MINUTES * 60, 
                otp
            )
            
            # Store attempt counter
            attempts_key = f"otp_attempts:{purpose}:{email if '@' in email else phone}"
            await redis_client.setex(
                attempts_key,
                settings.OTP_EXPIRE_MINUTES * 60,
                0
            )
            
            # For development, just log the OTP
            logger.info("OTP generated", 
                       phone=phone, 
                       email=email, 
                       purpose=purpose, 
                       otp=otp)
            
            # TODO: Implement actual SMS/WhatsApp/Email sending
            # This would integrate with external services like Twilio, SendGrid, etc.
            
            return True
            
        except Exception as e:
            logger.error("Failed to send OTP", error=str(e))
            return False
    
    async def verify_otp(self, identifier: str, code: str, purpose: str) -> bool:
        """
        Verify OTP code
        """
        try:
            redis_client = await get_redis()
            otp_key = f"otp:{purpose}:{identifier}"
            attempts_key = f"otp_attempts:{purpose}:{identifier}"
            
            # Check attempts
            attempts = await redis_client.get(attempts_key)
            attempts = int(attempts) if attempts else 0
            
            if attempts >= settings.OTP_MAX_ATTEMPTS:
                logger.warning("Max OTP attempts exceeded", identifier=identifier, purpose=purpose)
                return False
            
            # Get stored OTP
            stored_otp = await redis_client.get(otp_key)
            if not stored_otp:
                logger.warning("OTP not found or expired", identifier=identifier, purpose=purpose)
                return False
            
            # Increment attempts
            await redis_client.incr(attempts_key)
            
            # Verify code
            if stored_otp.decode() == code:
                # Valid OTP - delete it
                await redis_client.delete(otp_key)
                await redis_client.delete(attempts_key)
                logger.info("OTP verified successfully", identifier=identifier, purpose=purpose)
                return True
            else:
                logger.warning("Invalid OTP", identifier=identifier, purpose=purpose)
                return False
            
        except Exception as e:
            logger.error("OTP verification failed", error=str(e))
            return False
    
    async def send_welcome_message(self, phone: str, email: str, temporary_password: str) -> bool:
        """
        Send welcome message with temporary password
        """
        try:
            # For development, just log the message
            logger.info("Welcome message sent", 
                       phone=phone, 
                       email=email, 
                       temp_password=temporary_password)
            
            # TODO: Implement actual welcome message sending
            # This would send via WhatsApp/SMS/Email with login instructions
            
            return True
            
        except Exception as e:
            logger.error("Failed to send welcome message", error=str(e))
            return False
