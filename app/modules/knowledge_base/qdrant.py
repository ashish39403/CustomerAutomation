from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings


@lru_cache
def client() -> QdrantClient:
    if not settings.qdrant_url:
        raise RuntimeError("QDRANT_URL is not set")
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30)


def collection_name() -> str:
    return settings.qdrant_collection


def ensure_collection() -> None:
    qdrant = client()
    name = collection_name()
    if qdrant.collection_exists(name):
        return
    qdrant.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=settings.qdrant_vector_size, distance=Distance.COSINE),
    )


def point_id(document_id: UUID, version: int, chunk_index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"{document_id}:{version}:{chunk_index}"))


def upsert_points(points: list[PointStruct]) -> None:
    ensure_collection()
    client().upsert(collection_name=collection_name(), points=points)


def delete_document_points(document_id: UUID, version: int | None = None) -> None:
    ensure_collection()
    conditions = [FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
    if version is not None:
        conditions.append(FieldCondition(key="document_version", match=MatchValue(value=version)))
    client().delete(
        collection_name=collection_name(),
        points_selector=FilterSelector(filter=Filter(must=conditions)),
    )


def search(vector: list[float], *, limit: int | None = None) -> list[dict[str, Any]]:
    ensure_collection()
    results = client().query_points(
        collection_name=collection_name(),
        query=vector,
        limit=limit or settings.retrieval_k,
        query_filter=Filter(
            must=[FieldCondition(key="active", match=MatchValue(value=True))]
        ),
        with_payload=True,
    )
    hits = []
    for point in results.points:
        payload = point.payload or {}
        hits.append(
            {
                "id": str(point.id),
                "score": point.score,
                "text": payload.get("text") or "",
                "title": payload.get("title") or "",
                "source": payload.get("source") or "",
                "source_locator": payload.get("source_locator") or "",
                "document_id": payload.get("document_id"),
                "chunk_id": payload.get("chunk_id"),
            }
        )
    return hits
