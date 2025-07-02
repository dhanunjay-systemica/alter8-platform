"""
Admin endpoints for user management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User

logger = structlog.get_logger()

router = APIRouter()


@router.get("/users/pending")
async def get_pending_registrations(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending user registrations (admin only)
    """
    # TODO: Implement pending registrations logic
    return {"message": "Pending registrations endpoint"}


@router.post("/users/{user_id}/approve")
async def approve_user_registration(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve user registration (admin only)
    """
    # TODO: Implement user approval logic
    return {"message": f"User {user_id} approved"}


@router.post("/users/{user_id}/reject")
async def reject_user_registration(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject user registration (admin only)
    """
    # TODO: Implement user rejection logic
    return {"message": f"User {user_id} rejected"}
