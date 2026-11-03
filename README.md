# Customer Automation

One company, one Gmail inbox. Customer mail becomes a ticket. A background worker classifies it, drafts a reply from your knowledge base, and sends that reply when the case is routine. Refunds, payments, complaints, and risky mail are left for a person.

The operator UI is not in this repository. `frontend/` and `dashboard/` stay on your machine.

## What runs

| Piece | Role |
| --- | --- |
| API | FastAPI on port 8000. Login, tickets, knowledge uploads, Gmail status. |
| Worker | Polls Gmail, classifies, drafts, sends or hands off. |
| Postgres | Tickets, users, messages, and the job queue. |
| Qdrant | Search index for the knowledge base. |
| Object storage | Original uploaded files (S3-compatible). |

The model writes the draft. Python decides whether it is sent.

## What happens to a new email

1. The worker reads the connected inbox.
2. A new message becomes a ticket on the existing Gmail thread.
3. The classifier labels it. The drafter answers from retrieved knowledge-base passages.
4. A routine, grounded reply is sent on that thread. The ticket shows up as `auto_replied`.
5. Anything else is handed to a human (`handed_off`) and is not auto-sent:
   - refund, payment, or complaint
   - risk flags such as legal, threat, chargeback, fraud, or account security
   - no matching knowledge-base evidence
   - a draft that claims a refund, shipment, or cancellation the knowledge base does not support

A human can still reply, escalate, resolve, or reopen a ticket through the API.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Postgres (Neon or any Postgres you can reach)
- Qdrant
- An OpenAI-compatible chat and embeddings endpoint
- A Google OAuth client with Gmail access

## First run

```powershell
uv sync
copy .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, from the same folder:

```powershell
uv run python -m app.worker
```

Fill `.env` before the first boot. The names are in `.env.example`. At minimum set `DATABASE_URL`, `APP_SECRET_KEY`, `DASHBOARD_PASSWORD`, `SEED_OPERATOR_PASSWORD`, the model key and base URL, Qdrant, object storage, and the Google OAuth values. Do not commit `.env`.

On startup the API creates two users if they are missing:

| Who | Email | Password |
| --- | --- | --- |
| Admin | `DASHBOARD_ADMIN_EMAIL` (default `admin@local`). You can also sign in with `DASHBOARD_USERNAME`. | `DASHBOARD_PASSWORD` |
| Operator | `SEED_OPERATOR_EMAIL` (default `operator@local`) | `SEED_OPERATOR_PASSWORD` |

The session is an HttpOnly cookie named `ca_session`. The same routes are mounted at `/api` and `/api/v1`.

Check the process with `GET /health` and `GET /health/ready`.

## Connect the inbox

1. Put the Google client id, secret, and `GOOGLE_REDIRECT_URI` in `.env`. The default redirect is `http://localhost:8000/api/v1/gmail/callback`.
2. Sign in as admin.
3. Open the Gmail connect flow from `GET /api/gmail/status` (admin only) and approve the mailbox.
4. Leave the worker running. It polls on `POLL_INTERVAL_SECONDS`.

Send a test message to that inbox from another account. Within a poll or two, a routine question should get a bot reply on the same thread. A refund or complaint should become a ticket and wait.

## Knowledge base

Upload a PDF, txt, or markdown file through the documents API while signed in as admin. The worker stores the file, chunks it, and indexes it in Qdrant. The bot can only answer from those passages.

The first time the app uses a collection it creates payload indexes on `active` and `document_id`. Qdrant Cloud rejects a filtered search until those indexes exist.

## Tests

```powershell
uv run pytest
```

## Docker

`docker compose up --build` starts the API, the worker, and a local Qdrant. Postgres stays wherever `DATABASE_URL` points. Copy `.env.example` to `.env` first.

## Layout

```
app/            API, worker, Gmail, tickets, knowledge base, AI policy
app/db/         SQLAlchemy models and Alembic migrations
tests/          API and policy tests
knowledge_docs/ seed articles loaded by the worker
.env.example    every setting, with empty secrets
```
