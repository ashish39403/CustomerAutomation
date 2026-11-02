from __future__ import annotations

from datetime import UTC, datetime

import structlog
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditEvent, GmailAccount
from app.db.models.enums import ActorType, GmailAccountStatus
from app.modules.gmail.client import SCOPES, gmail_execute, service_from_encrypted_token
from app.modules.gmail.crypto import encrypt_token

log = structlog.get_logger("gmail")


def build_flow() -> Flow:
    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError("Google OAuth client is not configured")
    redirect = settings.google_redirect_uri or "http://localhost:8000/api/v1/gmail/callback"
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect,
    )


def authorization_url(state: str) -> str:
    flow = build_flow()
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return url


def persist_refresh_token(db: Session, refresh_token: str, *, actor_id=None) -> GmailAccount:
    encrypted = encrypt_token(refresh_token)
    service = service_from_encrypted_token(encrypted)
    profile = gmail_execute(service.users().getProfile(userId="me"))
    email = (profile.get("emailAddress") or "").lower()
    history_id = str(profile.get("historyId") or "") or None
    account = db.scalar(select(GmailAccount).where(GmailAccount.email == email))
    if account is None:
        account = GmailAccount(email=email)
        db.add(account)
    account.encrypted_refresh_token = encrypted
    account.status = GmailAccountStatus.CONNECTED.value
    account.scopes = " ".join(SCOPES)
    account.history_id = history_id
    account.last_history_sync_at = None
    account.last_error = None
    account.updated_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_type=ActorType.USER.value if actor_id else ActorType.SYSTEM.value,
            actor_id=actor_id,
            event_type="gmail.connected",
            event_data_json={"email": email},
        )
    )
    db.commit()
    db.refresh(account)
    log.info("gmail.connected", email=email, account_id=str(account.id))
    return account


def seed_from_env(db: Session) -> None:
    import os

    if os.environ.get("PYTEST_VERSION"):
        return
    if not settings.google_refresh_token or not settings.google_token_encryption_key:
        return
    existing = db.scalar(
        select(GmailAccount).where(GmailAccount.status == GmailAccountStatus.CONNECTED.value)
    )
    if existing is not None:
        return
    try:
        persist_refresh_token(db, settings.google_refresh_token)
    except Exception as exc:
        log.warning("gmail.seed_failed", error=str(exc))
