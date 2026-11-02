from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from app.modules.gmail.schemas import AttachmentMeta, NormalizedEmail


def header_value(headers: list[dict[str, str]], name: str) -> str:
    target = name.lower()
    for item in headers:
        if item.get("name", "").lower() == target:
            return item.get("value") or ""
    return ""


def decode_body(payload: dict[str, Any]) -> str | None:
    mime = (payload.get("mimeType") or "").split(";")[0].strip().lower()
    body = payload.get("body") or {}
    data = body.get("data")
    if mime == "text/plain" and data:
        return _b64(data)
    for part in payload.get("parts") or []:
        text = decode_body(part)
        if text:
            return text
    if mime == "text/html" and data:
        return _b64(data)
    return None


def attachment_meta(payload: dict[str, Any]) -> list[AttachmentMeta]:
    items: list[AttachmentMeta] = []
    filename = payload.get("filename")
    body = payload.get("body") or {}
    if filename:
        items.append(
            AttachmentMeta(
                filename=filename,
                mime_type=payload.get("mimeType"),
                size=body.get("size"),
            )
        )
    for part in payload.get("parts") or []:
        items.extend(attachment_meta(part))
    return items


def normalize_message(raw: dict[str, Any]) -> NormalizedEmail:
    payload = raw.get("payload") or {}
    headers = payload.get("headers") or []
    header_map = {
        item.get("name", ""): item.get("value", "")
        for item in headers
        if item.get("name")
    }
    from_email = parseaddr(header_value(headers, "From"))[1] or "unknown@unknown"
    to_raw = header_value(headers, "To")
    to_emails = [parseaddr(part)[1] for part in to_raw.split(",") if parseaddr(part)[1]]
    received = None
    internal = raw.get("internalDate")
    if internal:
        received = datetime.fromtimestamp(int(internal) / 1000, tz=UTC)
    elif header_value(headers, "Date"):
        try:
            received = parsedate_to_datetime(header_value(headers, "Date"))
        except (TypeError, ValueError):
            received = None
    return NormalizedEmail(
        gmail_message_id=raw["id"],
        gmail_thread_id=raw.get("threadId") or raw["id"],
        from_email=from_email.lower(),
        to_emails=to_emails,
        subject=header_value(headers, "Subject") or None,
        body_text=decode_body(payload),
        received_at=received,
        headers=header_map,
        attachments=attachment_meta(payload),
    )


def _b64(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")
