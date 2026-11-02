from __future__ import annotations

import logging
import sys

import structlog

_SENSITIVE_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "database_url",
    "dsn",
    "refresh",
)


def _redact_secrets(
    _logger: object,
    _method: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    for key, value in list(event_dict.items()):
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS):
            event_dict[key] = "[redacted]"
        elif isinstance(value, str) and _looks_like_secret(value):
            event_dict[key] = "[redacted]"
    return event_dict


def _looks_like_secret(value: str) -> bool:
    prefixes = ("sk-", "npg_", "GOCSPX-", "1//", "eyJ")
    return value.startswith(prefixes) or "postgresql://" in value


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _redact_secrets,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
