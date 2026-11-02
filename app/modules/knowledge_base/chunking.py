from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class Chunk:
    index: int
    text: str
    source_locator: str
    content_hash: str


_HEADING = re.compile(r"(?m)^(#{1,3} .+)$")


def chunk_document(text: str, *, title: str) -> list[Chunk]:
    sections = _split_markdown_sections(text, title)
    chunks: list[Chunk] = []
    size = settings.knowledge_chunk_characters
    overlap = settings.knowledge_chunk_overlap
    for heading, body in sections:
        content = f"{heading}\n\n{body}".strip()
        if not content:
            continue
        if len(content) <= size:
            chunks.append(_make(len(chunks), content, heading))
            continue
        start = 0
        part = 1
        while start < len(content):
            end = min(start + size, len(content))
            piece = content[start:end].strip()
            if piece:
                locator = heading if part == 1 else f"{heading} #{part}"
                chunks.append(_make(len(chunks), piece, locator))
                part += 1
            if end == len(content):
                break
            start = max(end - overlap, start + 1)
    return chunks


def _split_markdown_sections(text: str, title: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [(title, text.strip())]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append((title, preamble))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = match.group(1).strip()
        body = text[match.end() : end].strip()
        sections.append((heading, body))
    return sections


def _make(index: int, text: str, locator: str) -> Chunk:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Chunk(index=index, text=text, source_locator=locator[:512], content_hash=digest)
