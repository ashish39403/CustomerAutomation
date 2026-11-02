from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

log = structlog.get_logger("storage")


def _bucket() -> str:
    return settings.neon_storage_bucket or "knowledgebase"


def s3_enabled() -> bool:
    return bool(
        settings.aws_endpoint_url_s3
        and settings.aws_access_key_id
        and settings.aws_secret_access_key
        and _bucket()
    )


@lru_cache
def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.aws_endpoint_url_s3,
        region_name=settings.aws_region or "us-east-2",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def _local_root() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def put_bytes(object_key: str, data: bytes, content_type: str | None = None) -> None:
    if s3_enabled():
        extra: dict[str, str] = {}
        if content_type:
            extra["ContentType"] = content_type
        _client().put_object(Bucket=_bucket(), Key=object_key, Body=data, **extra)
        log.info("storage.put", backend="s3", key=object_key, bytes=len(data))
        return
    path = _local_root() / object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    log.info("storage.put", backend="local", key=object_key, bytes=len(data))


def get_bytes(object_key: str) -> bytes:
    if s3_enabled():
        try:
            response = _client().get_object(Bucket=_bucket(), Key=object_key)
            return response["Body"].read()
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in {"NoSuchKey", "404", "NotFound"}:
                raise
    path = _local_root() / object_key
    if path.is_file():
        return path.read_bytes()
    source = Path(object_key)
    if source.is_file():
        return source.read_bytes()
    raise FileNotFoundError(object_key)


def delete_bytes(object_key: str) -> None:
    if s3_enabled():
        _client().delete_object(Bucket=_bucket(), Key=object_key)
        log.info("storage.delete", backend="s3", key=object_key)
    path = _local_root() / object_key
    if path.is_file():
        path.unlink()
