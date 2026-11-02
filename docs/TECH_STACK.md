# Technical Stack
## AI E-commerce Customer Support Automation

**Architecture style:** modular monolith + independent worker process  
**Deployment target:** one Linux VPS/EC2 instance using Docker Compose for V1

---

## 1. Stack summary

| Layer | Choice | Responsibility |
|---|---|---|
| Frontend | React + TypeScript + Vite | Internal support dashboard |
| UI | Tailwind CSS + shadcn/ui | Accessible, consistent UI components |
| API | FastAPI | REST API, OAuth callbacks, dashboard operations |
| Runtime | Python 3.14.x only after dependency compatibility checks | Backend and worker |
| Package management | uv | Python dependency and environment management |
| Validation | Pydantic v2 | Request/response and AI output schemas |
| AI orchestration | LangChain | Typed model calls, chains, and tool boundaries |
| RAG pipeline | LangChain + Qdrant | Document loading, chunking, embedding, retrieval, grounded drafting |
| LLM | OpenAI API-compatible provider | Classification and answer drafting |
| Relational DB | Neon PostgreSQL | Tickets, messages, settings, audit, job queue |
| ORM / migrations | SQLAlchemy 2.x + Alembic | Persistence and schema migrations |
| Vector DB | Qdrant | Knowledge-base chunk embeddings and similarity search |
| Embeddings | Provider-compatible embedding model | Embed query and document chunks |
| Object storage | Neon Object Storage | Original knowledge-base files and optional email attachments |
| Email | Gmail API + OAuth 2.0 | Inbox polling, thread retrieval, reply sending |
| Background work | PostgreSQL-backed durable job queue + worker | Polling, AI processing, indexing, retries |
| Frontend data | TanStack Query | Server state, caching, mutations |
| Forms | React Hook Form + Zod | Client-side form validation |
| Testing | pytest, httpx, Vitest, React Testing Library | Backend and frontend tests |
| Observability | structlog or stdlib structured logging; OpenTelemetry optional | Logs, traces, job correlation |
| Packaging/deploy | Docker + Docker Compose | Reproducible services and deployment |
| Reverse proxy/TLS | Caddy or Nginx | HTTPS termination and routing |
| CI | GitHub Actions | Lint, type checks, tests, build |

## 2. Important implementation decisions

### 2.1 FastAPI modular monolith
Keep one backend repository and one domain model. Run the API and worker as separate processes/containers from the same image. This avoids premature microservices while keeping long-running work out of request handlers.

### 2.2 PostgreSQL-backed job queue
Use a `jobs` table with atomic claiming (`FOR UPDATE SKIP LOCKED`), lease expiry, attempts, `available_at`, and retry scheduling. The API and worker share the same Neon database.

Do not implement a naive `SELECT pending; UPDATE running` sequence; concurrent workers could claim the same job. Use a single transactional claim operation.

No Redis/Celery in V1. Revisit only if throughput or scheduling requirements justify a dedicated broker.

### 2.3 Neon PostgreSQL
Use Neon for application data and durable jobs. Use SQLAlchemy with a pooled connection strategy suitable for the runtime. Keep migrations in Alembic and run them as a controlled deployment step, not independently from every app replica.

### 2.4 Qdrant
Qdrant stores vectors and metadata for knowledge-base chunks. PostgreSQL remains the source of truth for document metadata, ticket data, and indexing state. Store stable IDs linking Qdrant points to PostgreSQL document/chunk records.

### 2.5 Neon Object Storage
Store original uploaded files in a private bucket on Neon Object Storage. It is S3-compatible and branches with the Neon database, so each branch (dev, preview, production) gets its own isolated copy of files and objects — never point code at another branch's endpoint.

Use generated object keys, not user-provided paths. Access it with the S3 API via `boto3` using path-style addressing and SigV4 only. Neon injects branch-scoped, AWS-standard env vars (`AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`), so resolve endpoint, region, and credentials from those variables at startup. Private buckets require credentials for every operation; use short-lived presigned URLs only when direct browser upload/download is needed.

### 2.6 LangChain and model access
Use LangChain for AI orchestration and the RAG pipeline: chat model calls, structured-output classification, prompt templates, Qdrant retrieval, and draft generation. Keep chains, prompts, model configuration, Pydantic schemas, and deterministic business policy separate. The model may propose a classification or draft; Python code makes the send/escalation decision.

Prefer small, composable LangChain primitives (prompt templates, structured-output chat models, retrievers) over heavyweight multi-agent graphs for V1. The pipeline stays deterministic and auditable. All structured outputs are validated with Pydantic schemas; Pydantic remains the validation layer.

Use an OpenAI-compatible chat/embedding integration (`langchain-openai`) only if the selected provider genuinely supports the required chat and embedding endpoints. Do not assume every compatible gateway supports every OpenAI API feature. Keep provider/model names in environment configuration.

### 2.7 Gmail
Use a dedicated company/test support mailbox, not a personal inbox. Request the minimum Gmail scopes required. Store refresh tokens encrypted at rest and never expose them to the browser.

For V1, polling is simpler to operate than Gmail push notifications. Use Gmail history/sync APIs and persist a cursor/history ID so restarts do not silently skip mail. Handle history expiration by performing a safe resync.

## 3. Python dependencies

Pin and validate versions during implementation. Suggested dependency groups:

### Runtime
- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `pydantic-settings`
- `langchain`
- `langchain-openai`
- `langchain-qdrant`
- `langchain-text-splitters`
- `sqlalchemy`
- `psycopg[binary]` or `asyncpg` (choose one driver strategy)
- `alembic`
- `qdrant-client`
- `boto3` (S3 client for Neon Object Storage)
- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `httpx`
- `tenacity`
- `structlog`

### Development
- `pytest`
- `pytest-asyncio`
- `httpx`
- `ruff`
- `mypy` or `pyright`
- `coverage`

Do not add Celery, Redis, Kafka, or a workflow engine unless a concrete requirement appears. LangChain is the chosen AI orchestration and RAG layer.

## 4. Frontend dependencies

- `react`, `react-dom`, `typescript`, `vite`
- `tailwindcss`
- `shadcn/ui` components (Radix primitives)
- `lucide-react`
- `@tanstack/react-query`
- `react-router-dom`
- `react-hook-form`, `zod`, `@hookform/resolvers`
- `vitest`, `@testing-library/react`, `@testing-library/user-event`

Use a real API-backed dashboard. Seed data is acceptable only for local development and tests; do not present fabricated metrics or fake tickets as live production data.

## 5. Data ownership

| Data | System of record |
|---|---|
| Tickets, messages, status, audit events | PostgreSQL |
| Job state, attempts, leases | PostgreSQL |
| Document metadata and indexing status | PostgreSQL |
| Original KB files / stored attachments | Neon Object Storage |
| Embeddings and searchable chunk payloads | Qdrant |
| Gmail messages and threads | Gmail is external source; persist required normalized copy and IDs in PostgreSQL |
| AI prompts/configuration | Version-controlled application code/config |

## 6. Environment configuration

Use environment variables or a secrets manager. Commit only `.env.example` with placeholder values.

```dotenv
APP_ENV=development
APP_SECRET_KEY=
DATABASE_URL=
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=
LLM_MODEL=
EMBEDDING_MODEL=
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=customerautomation
AWS_ENDPOINT_URL_S3=
AWS_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
NEON_STORAGE_BUCKET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GOOGLE_TOKEN_ENCRYPTION_KEY=
GMAIL_POLL_INTERVAL_SECONDS=60
JOB_POLL_INTERVAL_SECONDS=2
```

The storage endpoint and S3 credentials are branch-scoped. Locally, pull them into `.env` with `neon env pull` (or run commands under `neon-env run -- ...`); they are injected automatically inside Neon Functions. The example above shows placeholder values only. Do not commit or reuse cross-branch credentials.

## 7. Security baseline

- Keep OAuth tokens, API keys, database URLs, and encryption keys server-side.
- Encrypt Gmail refresh tokens at application level before storing them.
- Use HTTPS in deployment and secure, HttpOnly, SameSite cookies for dashboard sessions.
- Protect OAuth state against CSRF and validate redirect URIs.
- Use a dedicated mailbox and least-privilege Gmail scopes.
- Validate upload size, MIME type, extension, and extracted content.
- Do not execute macros or embedded scripts from uploaded files.
- Treat email body text and retrieved documents as untrusted input; prompt injection must not grant tools or override policy.
- Do not expose arbitrary model tools for sending emails or changing orders.
- Require server-side authorization and state checks for every send action.
- Redact secrets and sensitive customer data from logs.
- Apply rate limits to login, OAuth, upload, and sensitive endpoints.
- Keep the Neon Object Storage bucket private, and keep Qdrant/Postgres inaccessible from the public internet.

## 8. Compatibility and version policy

Python 3.14.x is the desired runtime, but verify all native/third-party dependencies (especially Google libraries, database drivers, LangChain integrations, and document parsers) before locking it. If a required package is not stable on 3.14, use Python 3.13 for the project rather than losing time to runtime incompatibilities.

Commit lockfiles (`uv.lock` and frontend lockfile). Pin Docker base images to tested versions and update intentionally.
