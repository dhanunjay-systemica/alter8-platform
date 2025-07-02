"""
User service for handling user operations
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from app.models.user import User, UserRole, RegistrationStatus
from app.core.security import get_password_hash

logger = structlog.get_logger()


class UserService:
    """User service class"""
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Get a user by email
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()
    
    async def get_user_by_phone(self, db: AsyncSession, phone: str) -> Optional[User]:
        """
        Get a user by phone
        """
        result = await db.execute(select(User).where(User.phone == phone))
        return result.scalars().first()
    
    async def get_user_by_email_or_phone(self, db: AsyncSession, identifier: str) -> Optional[User]:
        """
        Get a user by email or phone
        """
        result = await db.execute(
            select(User).where((User.email == identifier) | (User.phone == identifier))
        )
        return result.scalars().first()
    
    async def create_agent(self, db: AsyncSession, data: dict) -> User:
        """
        Create a new agent user
        """
        user = User(
            email=data.email,
            phone=data.phone,
            password_hash=get_password_hash(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=UserRole.AGENT,
            registration_status=RegistrationStatus.PENDING,
            is_verified=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info("Agent user created", user_id=user.id, email=user.email)
        return user
    
    async def create_field_executive(self, db: AsyncSession, data: dict, admin_id: str) -> User:
        """
        Create a new field executive user
        """
        user = User(
            email=data.email,
            phone=data.phone,
            password_hash=get_password_hash(data.temporary_password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=UserRole.FIELD_EXECUTIVE,
            registration_status=RegistrationStatus.APPROVED,
            approved_by=admin_id,
            approved_at=datetime.utcnow(),
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info("Field executive user created", user_id=user.id, email=user.email)
        return user

