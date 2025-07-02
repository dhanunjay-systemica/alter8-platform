"""
Authentication endpoints for user registration and login
"""

from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    AgentRegistrationRequest,
    FieldExecutiveRegistrationRequest,
    LoginResponse,
    RefreshTokenRequest,
    UserRegistrationResponse,
    UserResponse,
)
from app.schemas.otp import OTPVerification
from app.services.otp_service import OTPService
from app.services.rate_limit_service import RateLimitService
from app.services.token_service import token_service
from app.services.user_service import UserService

logger = structlog.get_logger()

router = APIRouter()

user_service = UserService()
otp_service = OTPService()
rate_limit_service = RateLimitService()


@router.post("/register/agent", response_model=UserRegistrationResponse)
async def register_agent(
    request: Request,
    registration_data: AgentRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new agent account
    
    Agents need to be authorized before registration is complete.
    This creates a pending registration that requires admin approval.
    """
    # Rate limiting
    client_ip = request.client.host
    await rate_limit_service.check_rate_limit(
        key=f"agent_registration:{client_ip}",
        limit=5,  # 5 registrations per hour per IP
        window=3600
    )

    logger.info("Agent registration attempt", email=registration_data.email)

    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(db, registration_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        existing_phone = await user_service.get_user_by_phone(db, registration_data.phone)
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

        # Create user with pending status
        user = await user_service.create_agent(db, registration_data)

        # Send verification OTP
        await otp_service.send_verification_otp(
            phone=user.phone,
            email=user.email,
            purpose="email_verification"
        )

        logger.info("Agent registration created", user_id=user.id, email=user.email)

        return UserRegistrationResponse(
            id=user.id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            registration_status=user.registration_status,
            message="Registration successful. Please verify your email and wait for admin approval."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/register/field-executive", response_model=UserRegistrationResponse)
async def register_field_executive(
    request: Request,
    registration_data: FieldExecutiveRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register a new field executive account
    
    Only admins can create field executive accounts.
    """
    # Check if current user is admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create field executive accounts"
        )

    logger.info("Field executive registration by admin",
               admin_id=current_user.id,
               email=registration_data.email)

    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(db, registration_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        existing_phone = await user_service.get_user_by_phone(db, registration_data.phone)
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

        # Create field executive user (pre-approved)
        user = await user_service.create_field_executive(db, registration_data, current_user.id)

        # Send welcome message with login credentials
        await otp_service.send_welcome_message(
            phone=user.phone,
            email=user.email,
            temporary_password=registration_data.temporary_password
        )

        logger.info("Field executive created", user_id=user.id, created_by=current_user.id)

        return UserRegistrationResponse(
            id=user.id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            registration_status=user.registration_status,
            message="Field executive account created successfully. Welcome message sent."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Field executive registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/verify-registration")
async def verify_registration(
    otp_data: OTPVerification,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email/phone during registration process
    """
    try:
        # Verify OTP
        is_valid = await otp_service.verify_otp(
            identifier=otp_data.identifier,
            code=otp_data.code,
            purpose="email_verification"
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )

        # Update user verification status
        user = await user_service.get_user_by_email_or_phone(db, otp_data.identifier)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Mark as verified
        if otp_data.identifier == user.email:
            user.email_verified_at = datetime.utcnow()
        elif otp_data.identifier == user.phone:
            user.phone_verified_at = datetime.utcnow()

        user.is_verified = True
        await db.commit()

        logger.info("User verification completed", user_id=user.id)

        return {
            "message": "Verification successful",
            "verified": True,
            "next_step": "waiting_for_approval" if user.role == UserRole.AGENT else "account_ready"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again."
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    User login with email/phone and password
    """
    client_ip = request.client.host

    # Rate limiting for login attempts
    await rate_limit_service.check_rate_limit(
        key=f"login_attempts:{client_ip}",
        limit=10,  # 10 attempts per 15 minutes per IP
        window=900
    )

    try:
        # Get user by email or phone
        user = await user_service.get_user_by_email_or_phone(db, form_data.username)

        if not user:
            # Increment failed attempt counter for IP
            await rate_limit_service.increment_counter(f"failed_login:{client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Check if user can login
        can_login, reason = user.can_login()
        if not can_login:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=reason
            )

        # Verify password
        if not verify_password(form_data.password, user.password_hash):
            # Increment failed login attempts
            user.failed_login_attempts += 1

            # Lock account after max attempts
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )
                logger.warning("Account locked due to failed attempts", user_id=user.id)

            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Successful login - reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = client_ip
        await db.commit()

        # Create token pair using token service
        token_data = await token_service.create_token_pair(
            user_id=str(user.id),
            role=user.role.value
        )

        logger.info("User login successful", user_id=user.id, role=user.role)

        return LoginResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=UserResponse(
                id=user.id,
                email=user.email,
                phone=user.phone,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_verified=user.is_verified,
                profile_picture_url=user.profile_picture_url
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Verify refresh token and get user_id
        user_id = await token_service.verify_refresh_token(request.refresh_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new access token
        token_data = await token_service.refresh_access_token(
            request.refresh_token,
            user.role.value
        )

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )

        logger.info("Token refreshed successfully", user_id=user.id)

        return LoginResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=UserResponse(
                id=user.id,
                email=user.email,
                phone=user.phone,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_verified=user.is_verified,
                profile_picture_url=user.profile_picture_url
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    User logout - invalidate tokens
    """
    try:
        # Extract tokens from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )

        access_token = authorization.split(" ")[1]

        # Get refresh token from user session (if stored)
        # For now, we'll blacklist the access token and clear refresh tokens
        user_id = str(current_user.id)

        # Get stored refresh token
        refresh_token = await token_service._get_refresh_token(user_id)

        # Logout user (blacklist tokens and clear session)
        if refresh_token:
            success = await token_service.logout_user(user_id, access_token, refresh_token)
        else:
            # Just blacklist access token if no refresh token found
            success = await token_service.blacklist_token(access_token)
            await token_service._clear_user_session(user_id)

        if success:
            logger.info("User logout successful", user_id=current_user.id)
            return {"message": "Logout successful"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all")
async def logout_all_sessions(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user from all sessions - invalidate all refresh tokens
    """
    try:
        user_id = str(current_user.id)

        # Logout from all sessions
        success = await token_service.logout_all_sessions(user_id)

        if success:
            logger.info("User logged out from all sessions", user_id=current_user.id)
            return {"message": "Logged out from all sessions successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout from all sessions failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Logout all sessions failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout from all sessions failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        phone=current_user.phone,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_verified=current_user.is_verified,
        profile_picture_url=current_user.profile_picture_url
    )
