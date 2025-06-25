"""
API v1 router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, otp, admin

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(otp.router, prefix="/otp", tags=["OTP"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])