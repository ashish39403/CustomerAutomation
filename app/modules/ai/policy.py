from __future__ import annotations

import re

from app.core.config import settings
from app.db.models.enums import Decision, TicketCategory
from app.modules.ai.schemas import Classification

# --- Frozen sets (faster membership, no mutation risk) ---
ESCALATE_CATEGORIES = frozenset({
    TicketCategory.REFUND,
    TicketCategory.PAYMENT,
    TicketCategory.COMPLAINT,
})

ESCALATE_FLAGS = frozenset({
    "legal", "threat", "chargeback", "pii", "account_security",
    "fraud", "injury", "personal_data", "cancellation", "angry_customer",
})

# --- Pre-compiled combined regexes (single pass instead of 7) ---
# Ek hi regex mein saare patterns + named groups => 1 scan per text
_OVERLAY_RE = re.compile(
    r"(?P<chargeback>chargeback|a-?to-?z|payment dispute)"
    r"|(?P<legal>\b(?:sue|lawyer|legal action|attorney)\b)"
    r"|(?P<threat>\b(?:kill|bomb|threaten)\b)"
    r"|(?P<injury>injur|hurt myself|safety incident)"
    r"|(?P<personal_data>gdpr|delete my data|personal data|ccpa)"
    r"|(?P<account_security>hacked|password|account stolen)"
    r"|(?P<prompt_injection>ignore (?:previous|all) instructions|system prompt)",
    re.I,
)

_FORBIDDEN_DRAFT = re.compile(
    r"(refund has been (?:issued|processed|sent)"
    r"|your (?:order|package) (?:has )?shipped"
    r"|will arrive on"
    r"|replacement has been (?:sent|shipped)"
    r"|we have cancelled)",
    re.I,
)


def overlay_risk_flags(text: str, flags: list[str]) -> list[str]:
    """Merge AI flags with regex-detected flags. Single regex pass."""
    # Copy only if we need to mutate; use set for O(1) dedupe
    found = set(flags)
    # finditer with named groups — ek hi scan, no sorted() overhead
    for m in _OVERLAY_RE.finditer(text):
        # lastgroup gives the matched alternative's name
        found.add(m.lastgroup)
    return list(found)  # caller ko order chahiye to sorted(found) karo


def decide(
    classification: Classification,
    *,
    evidence_count: int,
    grounding_ok: bool,
    skip_reply: bool = False,
) -> tuple[Decision, str]:
    # 1. Cheapest checks first (bool compare, no set ops)
    if skip_reply:
        return Decision.NO_REPLY, "message excluded from customer reply"

    # 2. Category check — set membership is O(1)
    if classification.category in ESCALATE_CATEGORIES:
        return Decision.ESCALATE, "category requires a human"

    # 3. Flags — set intersection only if flags non-empty
    if classification.risk_flags and (
        ESCALATE_FLAGS.intersection(classification.risk_flags)
    ):
        return Decision.ESCALATE, "risk flags require a human"

    # 4. Remaining cheap checks
    if classification.needs_live_order_data:
        return Decision.ESCALATE, "live order data is required"

    # prompt_injection not in ESCALATE_FLAGS => alag check
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
    # Short-circuit: agar draft mein forbidden claim hi nahi, evidence scan skip
    m = _FORBIDDEN_DRAFT.search(draft)
    if m is None:
        return True
    # Sirf tab evidence scan karo jab draft mein claim mile
    return _FORBIDDEN_DRAFT.search(evidence_text) is not None