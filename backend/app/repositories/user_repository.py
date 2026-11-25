"""
app/repositories/user_repository.py
─────────────────────────────────────
PURPOSE:
  All database queries related to users live here.
  This is the ONLY place that talks directly to the database for users.

WHY A REPOSITORY LAYER?
  Separates database logic from business logic.
  - Service layer says WHAT to do ("register a user")
  - Repository layer says HOW to do it ("INSERT INTO users ...")
  This makes the code testable: in tests, you can swap the repository
  with a fake one without touching any business logic.
  UserRepository is that Storekeeper. 
  The Storekeeper knows exactly where the boxes are, how the shelves are arranged, 
  and how to safely fetch items without breaking anything.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Encapsulates all User database operations.
    Instantiated per-request with a fresh DB session.
    """

    def __init__(self, db: Session):
        # Store the session — all methods use this same session
        # so they participate in the same transaction
        self.db = db

    # ── Read Operations ─────────────────────────────────────────────────────────

    def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        """Fetch a user by their UUID. Returns None if not found."""
        if isinstance(user_id, str):
            try:
                user_id = UUID(user_id)
            except (ValueError, AttributeError):
                return None
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Fetch a user by email address.
        Used during login to find the user to authenticate.
        Case-insensitive search using lower() for reliability.
        """
        return (
            self.db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Fetch a paginated list of all users.
        skip/limit = standard pagination pattern (like SQL OFFSET/LIMIT).
        Only used by superadmin endpoints.
        """
        return self.db.query(User).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Count total users. Used to check if any superadmin exists on startup."""
        return self.db.query(User).count()

    def exists_by_email(self, email: str) -> bool:
        """Check if an email is already registered. Used during registration."""
        return (
            self.db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        ) is not None

    # ── Write Operations ─────────────────────────────────────────────────────────

    def create(self, user_data: UserCreate, is_superadmin: bool = False) -> User:
        """
        Create a new user in the database.

        Steps:
        1. Hash the plain password → never store plain text
        2. Build the User ORM object
        3. Add to session and commit
        4. Refresh to load DB-generated fields (id, created_at, etc.)
        5. Return the populated User object
        """
        db_user = User(
            email=user_data.email.lower().strip(),   # Normalize email
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=UserRole.SUPERADMIN if is_superadmin else UserRole.MEMBER,
            is_superadmin=is_superadmin,
            is_active=True,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)  # Load DB-generated fields (UUID, timestamps)
        logger.info(f"Created user: {db_user.email} (superadmin={is_superadmin})")
        return db_user

    def update(self, user_id: str | UUID, data: UserUpdate) -> Optional[User]:
        """
        Update user fields. Only updates fields that are explicitly provided.
        Uses `exclude_unset=True` → if a field wasn't sent in the request, don't touch it.
        """
        user = self.get_by_id(user_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Normalize email if it's being updated
        if "email" in update_data and update_data["email"]:
            update_data["email"] = update_data["email"].lower().strip()

        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user_id: str | UUID, new_hashed_password: str) -> bool:
        """Update only the hashed_password field."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.hashed_password = new_hashed_password
        self.db.commit()
        return True

    def update_last_login(self, user_id: str | UUID) -> None:
        """
        Record the timestamp of the user's last successful login.
        Called by the auth service immediately after a successful login.
        """
        from datetime import datetime, timezone
        user = self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            self.db.commit()

    def deactivate(self, user_id: str | UUID) -> bool:
        """
        Soft-delete: set is_active=False instead of deleting the row.
        Preserves audit trail — we can always see what the user did historically.
        Returns True if deactivated, False if user not found.
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.is_active = False
        self.db.commit()
        logger.info(f"Deactivated user: {user.email}")
        return True

    def superadmin_exists(self) -> bool:
        """Check if any superadmin user exists. Used on startup seeding."""
        return (
            self.db.query(User)
            .filter(User.is_superadmin == True)  # noqa: E712
            .first()
        ) is not None
