"""
OTP verification endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from app.core.database import get_db
from app.schemas.otp import OTPRequest, OTPVerify, OTPResponse, OTPVerificationResult
from app.services.otp_service import OTPService
from app.services.rate_limit_service import RateLimitService

logger = structlog.get_logger()

router = APIRouter()

otp_service = OTPService()
rate_limit_service = RateLimitService()


@router.post("/send", response_model=OTPResponse)
async def send_otp(
    request: Request,
    otp_request: OTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send OTP for verification
    """
    client_ip = request.client.host
    
    # Rate limiting for OTP requests
    await rate_limit_service.check_rate_limit(
        key=f"otp_send:{client_ip}",
        limit=5,  # 5 OTP requests per hour per IP
        window=3600
    )
    
    try:
        # TODO: Implement OTP sending logic
        logger.info("OTP send request", request=otp_request.dict())
        
        return OTPResponse(
            success=True,
            message="OTP sent successfully",
            expires_in=600,  # 10 minutes
            can_resend_in=60,  # 1 minute
            attempts_remaining=3
        )
        
    except Exception as e:
        logger.error("OTP send failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )


@router.post("/verify", response_model=OTPVerificationResult)
async def verify_otp(
    request: Request,
    otp_verify: OTPVerify,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP code
    """
    client_ip = request.client.host
    
    # Rate limiting for OTP verification
    await rate_limit_service.check_rate_limit(
        key=f"otp_verify:{client_ip}",
        limit=10,  # 10 verification attempts per hour per IP
        window=3600
    )
    
    try:
        # TODO: Implement OTP verification logic
        logger.info("OTP verification request", request=otp_verify.dict())
        
        return OTPVerificationResult(
            verified=True,
            message="OTP verified successfully"
        )
        
    except Exception as e:
        logger.error("OTP verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP verification failed"
        )
