from __future__ import annotations

from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


def chat_model(model: str | None = None, *, temperature: float = 0) -> ChatOpenAI:
    if not settings.llm_api_key:
        raise RuntimeError("No API key configured for chat models")
    return ChatOpenAI(
        model=model or settings.chat_model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=temperature,
        timeout=60,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8), reraise=True)
def invoke(model: ChatOpenAI, prompt: str):
    return model.invoke(prompt)
