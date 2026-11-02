from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr
from typing import Any

from googleapiclient.errors import HttpError

from app.modules.gmail.client import GmailAuthError, service_from_encrypted_token

AUTHOR_HEADER = "ca_author"
UNKNOWN_STATUSES = {408, 429, 500, 502, 503, 504}


class GmailSendRejected(Exception):
    """Gmail refused the send; it did not leave the mailbox."""


class GmailSendUnknown(Exception):
    """The request may have reached Gmail; reconcile before retrying."""


@dataclass(frozen=True, slots=True)
class SendResult:
    gmail_message_id: str
    thread_id: str


def build_reply_payload(
    *,
    mailbox: str,
    to: str,
    subject: str | None,
    body: str,
    thread_id: str,
    in_reply_to: str | None,
    references: str | None,
) -> dict[str, str]:
    message = MIMEText(body, "plain", "utf-8")
    message["To"] = to
    message["From"] = mailbox
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    title = (subject or "").strip()
    if title.lower().startswith("re:"):
        message["Subject"] = title
    elif title:
        message["Subject"] = f"Re: {title}"
    else:
        message["Subject"] = "Re: your message"
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8").rstrip("=")
    return {"raw": raw, "threadId": thread_id}


def send_thread_reply(
    encrypted_token: str,
    *,
    mailbox: str,
    to: str,
    subject: str | None,
    body: str,
    thread_id: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> SendResult:
    """Send once. Never retry this call — a retry can duplicate the email."""
    service = service_from_encrypted_token(encrypted_token)
    payload = build_reply_payload(
        mailbox=mailbox,
        to=to,
        subject=subject,
        body=body,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        references=references,
    )
    try:
        data = service.users().messages().send(userId="me", body=payload).execute()
    except GmailAuthError as exc:
        raise GmailSendRejected(str(exc)) from exc
    except HttpError as exc:
        status = getattr(exc.resp, "status", 500)
        if status in UNKNOWN_STATUSES:
            raise GmailSendUnknown(str(exc)) from exc
        raise GmailSendRejected(str(exc)) from exc
    except (TimeoutError, ConnectionError, OSError) as exc:
        raise GmailSendUnknown(str(exc)) from exc
    gmail_id = data.get("id")
    if not gmail_id:
        raise GmailSendUnknown("gmail returned no message id")
    return SendResult(gmail_message_id=gmail_id, thread_id=data.get("threadId") or thread_id)


def find_matching_outbound(
    encrypted_token: str,
    *,
    thread_id: str,
    mailbox: str,
    after: datetime,
) -> str | None:
    """Return a Gmail message id already sent from this mailbox on the thread."""
    try:
        service = service_from_encrypted_token(encrypted_token)
        data = service.users().threads().get(
            userId="me",
            id=thread_id,
            format="metadata",
            metadataHeaders=["From"],
        ).execute()
    except (GmailAuthError, HttpError, TimeoutError, ConnectionError, OSError):
        return None
    mailbox_l = mailbox.lower()
    after_ms = int(after.timestamp() * 1000) - 15_000
    for message in reversed(data.get("messages") or []):
        internal = int(message.get("internalDate") or 0)
        if internal and internal < after_ms:
            continue
        if _from_email(message).lower() == mailbox_l or mailbox_l in _from_header(message).lower():
            gmail_id = message.get("id")
            if gmail_id:
                return gmail_id
    return None


def _from_header(message: dict[str, Any]) -> str:
    headers = (message.get("payload") or {}).get("headers") or []
    for item in headers:
        if (item.get("name") or "").lower() == "from":
            return item.get("value") or ""
    return ""


def _from_email(message: dict[str, Any]) -> str:
    return parseaddr(_from_header(message))[1]
