from __future__ import annotations

from langchain_openai import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


def _client() -> OpenAIEmbeddings:
    if not settings.llm_api_key:
        raise RuntimeError("No API key configured for embeddings")
    return OpenAIEmbeddings(
        model=settings.embedding_model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8), reraise=True)
def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return _client().embed_documents(texts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8), reraise=True)
def embed_query(text: str) -> list[float]:
    return _client().embed_query(text)
