from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if "-pooler." in settings.database_url:
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.sqlalchemy_database_url, **_engine_kwargs)

direct_engine = create_engine(
    settings.sqlalchemy_direct_url,
    pool_pre_ping=True,
    poolclass=NullPool,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
