import secrets

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.errors import AppError, UnauthorizedError
from app.db.models import GmailAccount, User
from app.db.session import get_db
from app.modules.gmail.oauth import authorization_url, build_flow, persist_refresh_token

router = APIRouter(prefix="/gmail", tags=["gmail"])


class GmailStatusResponse(BaseModel):
    connected: bool
    email: str | None = None
    status: str | None = None
    last_error: str | None = None


@router.get("/status", response_model=GmailStatusResponse)
def gmail_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> GmailStatusResponse:
    account = db.scalar(select(GmailAccount).order_by(GmailAccount.updated_at.desc()))
    if account is None:
        return GmailStatusResponse(connected=False)
    return GmailStatusResponse(
        connected=account.status == "connected",
        email=account.email,
        status=account.status,
        last_error=account.last_error,
    )


@router.get("/connect")
def gmail_connect(request: Request, _: User = Depends(require_admin)) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    request.session["gmail_oauth_state"] = state
    return RedirectResponse(authorization_url(state))


@router.get("/callback")
def gmail_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> GmailStatusResponse:
    expected = request.session.pop("gmail_oauth_state", None)
    user_id = request.session.get("user_id")
    if not user_id:
        raise UnauthorizedError()
    if not code or not state or state != expected:
        raise AppError("Invalid OAuth state", status_code=400, code="oauth_state")
    flow = build_flow()
    flow.fetch_token(code=code)
    refresh = flow.credentials.refresh_token
    if not refresh:
        raise AppError("Google did not return a refresh token", status_code=400, code="oauth_token")
    from uuid import UUID

    account = persist_refresh_token(db, refresh, actor_id=UUID(str(user_id)))
    return GmailStatusResponse(
        connected=True,
        email=account.email,
        status=account.status,
        last_error=account.last_error,
    )
