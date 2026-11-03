from __future__ import annotations

import re

from app.core.config import settings
from app.db.models.enums import Decision, TicketCategory
from app.modules.ai.schemas import Classification

ESCALATE_CATEGORIES = {
    TicketCategory.REFUND,
    TicketCategory.PAYMENT,
    TicketCategory.COMPLAINT,
}

ESCALATE_FLAGS = {
    "legal",
    "threat",
    "chargeback",
    "pii",
    "account_security",
    "fraud",
    "injury",
    "personal_data",
    "cancellation",
    "angry_customer",
}

_OVERLAY = (
    (re.compile(r"chargeback|a-?to-?z|payment dispute", re.I), "chargeback"),
    (re.compile(r"\b(sue|lawyer|legal action|attorney)\b", re.I), "legal"),
    (re.compile(r"\b(kill|bomb|threaten)\b", re.I), "threat"),
    (re.compile(r"injur|hurt myself|safety incident", re.I), "injury"),
    (re.compile(r"gdpr|delete my data|personal data|ccpa", re.I), "personal_data"),
    (re.compile(r"hacked|password|account stolen", re.I), "account_security"),
    (re.compile(r"ignore (previous|all) instructions|system prompt", re.I), "prompt_injection"),
)

_FORBIDDEN_DRAFT = re.compile(
    r"(refund has been (issued|processed|sent)|your (order|package) (has )?shipped|"
    r"will arrive on|replacement has been (sent|shipped)|we have cancelled)",
    re.I,
)


def overlay_risk_flags(text: str, flags: list[str]) -> list[str]:
    found = set(flags)
    for pattern, flag in _OVERLAY:
        if pattern.search(text):
            found.add(flag)
    return sorted(found)


def decide(
    classification: Classification,
    *,
    evidence_count: int,
    grounding_ok: bool,
    skip_reply: bool = False,
) -> tuple[Decision, str]:
    if skip_reply:
        return Decision.NO_REPLY, "message excluded from customer reply"
    if classification.category in ESCALATE_CATEGORIES:
        return Decision.ESCALATE, f"category {classification.category.value} requires a human"
    if set(classification.risk_flags) & ESCALATE_FLAGS:
        return Decision.ESCALATE, "risk flags require a human"
    if classification.needs_live_order_data:
        return Decision.ESCALATE, "live order data is required"
    if "prompt_injection" in classification.risk_flags:
        return Decision.ESCALATE, "prompt injection detected"
    if evidence_count == 0:
        return Decision.INSUFFICIENT_EVIDENCE, "no supporting knowledge-base evidence"
    if not grounding_ok:
        return Decision.ESCALATE, "draft failed grounding checks"
    if classification.confidence < settings.auto_send_min_confidence:
        return Decision.ESCALATE, "confidence too low for an automatic reply"
    if settings.auto_send_enabled:
        return Decision.AUTO_SEND, "grounded reply can be sent automatically"
    return Decision.NEEDS_REVIEW, "grounded draft ready for human approval"


def grounding_ok(draft: str, evidence_text: str) -> bool:
    if _FORBIDDEN_DRAFT.search(draft) and not _FORBIDDEN_DRAFT.search(evidence_text):
        return False
    return True
