from __future__ import annotations

import structlog
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import AuditEvent, User
from app.db.models.enums import ActorType, UserRole

log = structlog.get_logger("auth")


def authenticate(db: Session, identifier: str, password: str) -> User | None:
    user = db.scalar(
        select(User).where(
            or_(User.email == identifier, User.display_name == identifier)
        )
    )
    if user is None or not verify_password(password, user.password_hash):
        log.info("auth.login_failed", identifier=identifier)
        return None
    log.info("auth.login_succeeded", user_id=str(user.id), role=user.role)
    return user


def seed_users(db: Session) -> None:
    _upsert_user(
        db,
        email=settings.admin_email,
        display_name=settings.dashboard_username,
        password=settings.dashboard_password,
        role=UserRole.ADMIN,
    )
    _upsert_user(
        db,
        email=settings.seed_operator_email,
        display_name="operator",
        password=settings.seed_operator_password,
        role=UserRole.OPERATOR,
    )
    db.commit()


def _upsert_user(
    db: Session,
    *,
    email: str,
    display_name: str,
    password: str,
    role: UserRole,
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    password_hash = hash_password(password)
    if user is None:
        user = User(
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            role=role.value,
        )
        db.add(user)
        db.flush()
        db.add(
            AuditEvent(
                actor_type=ActorType.SYSTEM.value,
                event_type="user.seeded",
                event_data_json={"email": email, "role": role.value},
            )
        )
        log.info("auth.user_seeded", user_id=str(user.id), role=role.value)
        return user

    user.display_name = display_name
    user.role = role.value
    user.password_hash = password_hash
    log.info("auth.user_updated", user_id=str(user.id), role=role.value)
    return user
