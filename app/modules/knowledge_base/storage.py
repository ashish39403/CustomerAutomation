from __future__ import annotations

from pathlib import Path

from app.core.config import settings


def _root() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def put_bytes(object_key: str, data: bytes) -> None:
    path = _root() / object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def get_bytes(object_key: str) -> bytes:
    path = _root() / object_key
    if not path.is_file():
        source = Path(object_key)
        if source.is_file():
            return source.read_bytes()
        raise FileNotFoundError(object_key)
    return path.read_bytes()


def delete_bytes(object_key: str) -> None:
    path = _root() / object_key
    if path.is_file():
        path.unlink()
