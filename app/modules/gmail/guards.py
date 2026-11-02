from __future__ import annotations

import re

from app.core.config import settings
from app.modules.gmail.schemas import NormalizedEmail, SkipReason

_AUTO_SUBJECT = re.compile(
    r"^(auto:|automatic reply|out of office|ooo:)",
    re.IGNORECASE,
)


def skip_reason(email: NormalizedEmail, mailbox_email: str) -> SkipReason | None:
    mailbox = mailbox_email.lower()
    sender = email.from_email.lower()
    headers = {key.lower(): value for key, value in email.headers.items()}

    if sender == mailbox:
        return SkipReason(code="self_sent", detail="mailbox sent this message")
    if sender in settings.excluded_sender_set:
        return SkipReason(code="excluded_sender", detail=sender)

    auto_submitted = headers.get("auto-submitted", "no").lower()
    if auto_submitted not in {"", "no"}:
        return SkipReason(code="auto_reply", detail="Auto-Submitted header")
    precedence = headers.get("precedence", "").lower()
    if precedence in {"bulk", "junk", "list"}:
        return SkipReason(code="auto_reply", detail="Precedence header")
    if headers.get("x-autoreply") or headers.get("x-autorespond"):
        return SkipReason(code="auto_reply", detail="autoreply header")
    if email.subject and _AUTO_SUBJECT.search(email.subject.strip()):
        return SkipReason(code="auto_reply", detail="automatic subject")
    return None
