from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.db.models import User
from app.db.models.enums import UserRole
from app.db.session import get_db


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    raw_id = request.session.get("user_id")
    if not raw_id:
        raise UnauthorizedError()
    try:
        user_id = UUID(str(raw_id))
    except ValueError as exc:
        request.session.clear()
        raise UnauthorizedError() from exc

    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        raise UnauthorizedError()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN.value:
        raise ForbiddenError("Admin role required")
    return user
