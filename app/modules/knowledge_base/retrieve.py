from __future__ import annotations

from app.core.config import settings
from app.modules.knowledge_base.embeddings import embed_query
from app.modules.knowledge_base.qdrant import search


def retrieve(query: str, *, k: int | None = None) -> list[dict]:
    vector = embed_query(query)
    return search(vector, limit=k or settings.retrieval_k)
