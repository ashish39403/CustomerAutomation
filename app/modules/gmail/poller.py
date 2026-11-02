from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import GmailAccount
from app.db.models.enums import GmailAccountStatus
from app.modules.gmail.client import GmailAuthError, gmail_execute, service_from_encrypted_token
from app.modules.gmail.ingest import ingest_email
from app.modules.gmail.normalize import normalize_message
from app.modules.jobs.errors import PermanentJobError, TransientJobError

log = structlog.get_logger("gmail")


def poll_account(db: Session, account_id: str) -> dict[str, int]:
    account = db.get(GmailAccount, UUID(account_id))
    if account is None or not account.encrypted_refresh_token:
        raise PermanentJobError("gmail account missing")
    try:
        service = service_from_encrypted_token(account.encrypted_refresh_token)
        profile = gmail_execute(service.users().getProfile(userId="me"))
        mailbox = (profile.get("emailAddress") or account.email).lower()
        message_ids, new_history_id = _collect_message_ids(service, account, profile)
        created = skipped = duplicates = missing = 0
        for message_id in message_ids:
            raw = _get_message(service, message_id)
            if raw is None:
                missing += 1
                continue
            email = normalize_message(raw)
            result = ingest_email(db, email, mailbox)
            if result.created:
                created += 1
            elif result.skipped:
                skipped += 1
            else:
                duplicates += 1
        account.email = mailbox
        account.status = GmailAccountStatus.CONNECTED.value
        account.history_id = new_history_id or account.history_id
        account.last_history_sync_at = datetime.now(UTC)
        account.last_error = None
        log.info(
            "gmail.poll_complete",
            account_id=account_id,
            created=created,
            skipped=skipped,
            duplicates=duplicates,
            missing=missing,
        )
        return {
            "created": created,
            "skipped": skipped,
            "duplicates": duplicates,
            "missing": missing,
        }
    except GmailAuthError as exc:
        account.status = GmailAccountStatus.NEEDS_REAUTHORIZATION.value
        account.last_error = str(exc)[:4000]
        raise PermanentJobError("gmail needs reauthorization") from exc
    except TransientJobError:
        raise
    except HttpError as exc:
        if exc.resp.status in {401, 403}:
            account.status = GmailAccountStatus.EXPIRED.value
            account.last_error = str(exc)[:4000]
            raise PermanentJobError("gmail auth expired") from exc
        raise TransientJobError(str(exc)) from exc


def _collect_message_ids(service, account: GmailAccount, profile: dict) -> tuple[list[str], str | None]:
    profile_history = str(profile.get("historyId") or "") or None
    if account.history_id and account.last_history_sync_at is not None:
        try:
            ids: list[str] = []
            page_token = None
            while True:
                kwargs = {
                    "userId": "me",
                    "startHistoryId": account.history_id,
                    "historyTypes": ["messageAdded"],
                }
                if page_token:
                    kwargs["pageToken"] = page_token
                data = gmail_execute(service.users().history().list(**kwargs))
                for event in data.get("history") or []:
                    for added in event.get("messagesAdded") or []:
                        message = added.get("message") or {}
                        message_id = message.get("id")
                        labels = message.get("labelIds") or []
                        if message_id and (not labels or "INBOX" in labels or "UNREAD" in labels):
                            ids.append(message_id)
                page_token = data.get("nextPageToken")
                if not page_token:
                    return _unique(ids), str(data.get("historyId") or profile_history or "")
        except HttpError as exc:
            if exc.resp.status != 404:
                raise
            log.info("gmail.history_expired", account_id=str(account.id))
    return _backfill(service), profile_history


def _get_message(service, message_id: str) -> dict | None:
    try:
        return gmail_execute(
            service.users().messages().get(userId="me", id=message_id, format="full")
        )
    except HttpError as exc:
        if exc.resp.status == 404:
            log.info("gmail.message_missing", gmail_message_id=message_id)
            return None
        raise


def _backfill(service) -> list[str]:
    data = gmail_execute(
        service.users().messages().list(
            userId="me",
            maxResults=settings.gmail_backfill_max,
            q="in:inbox",
        )
    )
    return [item["id"] for item in data.get("messages") or [] if item.get("id")]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
