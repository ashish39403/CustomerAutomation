import os
from collections.abc import Iterator

# The in-process jobs worker would poll the real Gmail mailbox during tests.
# Set before `app.main` (and thus `app.core.config`) is imported.
os.environ.setdefault("WORKER_IN_PROCESS", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import GmailAccount
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(autouse=True)
def _cleanup_test_gmail_accounts() -> Iterator[None]:
    """Tests insert fake GmailAccounts (encrypted_refresh_token="test-token").

    If left behind, the poll_gmail job picks them up and Fernet decrypt fails,
    so remove everything reusing the @harborandpine.test domain after each test.
    """
    yield
    with SessionLocal() as db:
        db.execute(
            delete(GmailAccount).where(GmailAccount.email.like("%@harborandpine.test"))
        )
        db.commit()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
