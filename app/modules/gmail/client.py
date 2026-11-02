from __future__ import annotations

from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.modules.gmail.crypto import decrypt_token
from app.modules.jobs.errors import TransientJobError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailAuthError(Exception):
    """Refresh token is invalid or revoked."""


def credentials_from_refresh_token(refresh_token: str) -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def service_from_encrypted_token(encrypted_token: str):
    try:
        creds = credentials_from_refresh_token(decrypt_token(encrypted_token))
    except Exception as exc:
        message = str(exc).lower()
        if "invalid_grant" in message or "revoked" in message:
            raise GmailAuthError(str(exc)) from exc
        raise TransientJobError(str(exc)) from exc
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


@retry(
    retry=retry_if_exception_type(TransientJobError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.4, max=6),
    reraise=True,
)
def gmail_execute(request: Any) -> dict[str, Any]:
    try:
        return request.execute()
    except HttpError as exc:
        if exc.resp.status in {429, 500, 502, 503, 504}:
            raise TransientJobError(str(exc)) from exc
        raise
