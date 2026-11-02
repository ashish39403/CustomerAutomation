from __future__ import annotations

from pydantic import BaseModel, Field

from app.db.models.enums import TicketCategory, TicketPriority


class Classification(BaseModel):
    category: TicketCategory
    summary: str
    priority: TicketPriority
    intent: str
    entities: dict[str, str] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    needs_live_order_data: bool = False


class DraftResult(BaseModel):
    draft_text: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
