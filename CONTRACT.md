# CONTRACT.md — API contract (source of truth)

Both sides (FastAPI backend, React dashboard) must match this file exactly.
If code and this file disagree, this file wins and the differing side gets fixed.
If this file itself must change, change it here first and record the reason in
`INTEGRATION_LOG.md`.

- All JSON field names are **snake_case** on both sides.
- Base URLs: backend `http://localhost:8000` (dev), dashboard `http://localhost:5173` (dev).
  The dashboard reads its base URL from `VITE_API_URL` (empty = same origin, Vite proxies `/api`).
- Auth is an **HttpOnly session cookie** named `ca_session` (Starlette `SessionMiddleware`).
  No token is ever stored in JS. `SameSite=Lax` for local dev, `SameSite=Lax` +
  `Secure` in production. Cookie max-age: 7 days.
- Error body shape for every non-2xx (except 422): `{"detail": "<human message>", "code": "<machine code>"}`.
  Validation errors (422) use `{"detail": [<pydantic error>, ...], "code": "validation_error"}`.

## Status vocabulary (tickets)

| API value | Meaning |
| --- | --- |
| `pending` | waiting for triage / not yet answered |
| `auto_replied` | answered automatically by the bot |
| `handed_off` | a human owns the reply (escalated, failed send, or replied from the dashboard) |

The `status` query filter accepts these three plus `all` (default `all`).
Any other value → 422.

## Endpoints

### `GET /health` — public

Liveness probe. **No auth.**

- 200 → `{"status": "ok"}`

Related public probe: `GET /health/ready` → 200 `{"status": "ok", "database": {...}, "qdrant": {...}, "gmail": {...}}`
or 503 with the same body when the database is unreachable.

### `POST /api/auth/login` — public (the only unauthenticated `/api/*` route)

Request:

```json
{ "email": "admin", "password": "admin1234@@@" }
```

Credentials come from `.env` (`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`, with
`EMAIL` / `PASSWORD` as fallbacks) and are seeded into the database at startup.

- 200 → sets `ca_session` cookie and returns
  ```json
  { "user": { "id": "<uuid>", "email": "admin@local", "display_name": "admin", "role": "admin" } }
  ```
- 401 → `{"detail": "Invalid credentials", "code": "unauthorized"}` (wrong email or password)
- 422 → validation error (missing/empty fields)

### `POST /api/auth/logout` — session required

- 204 → clears the session cookie (empty body)

### `GET /api/auth/me` — session required

- 200 → the same user object as login
- 401 → `{"detail": "Not authenticated", "code": "unauthorized"}`

### `GET /api/stats` — session required

- 200 →
  ```json
  { "auto_replied": 12, "handed_off": 3, "pending": 5, "today_total": 7 }
  ```
  - `auto_replied` / `handed_off` / `pending`: all-time ticket counts per API status
    (same buckets the tickets filter uses, so filter counts always match these numbers).
  - `today_total`: tickets **created** today (UTC calendar day, `created_at >= date_trunc('day', now() at time zone 'utc')`).
- 401 without a valid session cookie.

### `GET /api/tickets?status=&page=&page_size=&q=` — session required

Query parameters (validated with Pydantic → 422 on bad values):

| param | type | default | rules |
| --- | --- | --- | --- |
| `status` | string | `all` | one of `all`, `pending`, `auto_replied`, `handed_off` |
| `page` | int | `1` | `>= 1` |
| `page_size` | int | `10` | `1..100` |
| `q` | string | – | case-insensitive substring match on `customer_email` **or** `subject`, trimmed, max 200 chars |

Stable sort: `updated_at DESC, id DESC`.

- 200 →
  ```json
  {
    "items": [
      {
        "id": "<uuid>",
        "customer_email": "amy@example.com",
        "subject": "Where is my order?",
        "status": "pending",
        "created_at": "2026-11-03T09:00:00+00:00",
        "updated_at": "2026-11-03T09:12:00+00:00"
      }
    ],
    "total": 23,
    "page": 1,
    "page_size": 10,
    "pages": 3
  }
  ```
  `items` may be empty (`"items": []`, `pages` >= 1) — the dashboard renders an empty state.
- 401 without a session.

### `GET /api/tickets/{id}` — session required

`id` is the ticket's UUID string (the same value the list returns and the route
param the dashboard uses).

- 200 →
  ```json
  {
    "id": "<uuid>",
    "customer_email": "amy@example.com",
    "subject": "Where is my order?",
    "status": "pending",
    "created_at": "2026-11-03T09:00:00+00:00",
    "updated_at": "2026-11-03T09:12:00+00:00",
    "messages": [
      { "id": "<uuid>", "author": "customer", "body": "Where is my order?", "created_at": "2026-11-03T09:00:00+00:00" },
      { "id": "<uuid>", "author": "bot", "body": "It ships tomorrow.", "created_at": "2026-11-03T09:00:30+00:00" },
      { "id": "<uuid>", "author": "human", "body": "Adding the tracking number.", "created_at": "2026-11-03T09:05:00+00:00" }
    ],
    "classification": "shipping",
    "reasoning": "Customer asked about delivery date."
  }
  ```
  - `messages` is ordered oldest → newest. `author` is one of `customer`, `bot`, `human`.
  - `classification` and `reasoning` are `null` when the bot has not classified the ticket yet.
- 404 → `{"detail": "Ticket not found", "code": "not_found"}` for an unknown **or** malformed id.
- 401 without a session.

### `POST /api/tickets/{id}/reply` — session required

Request:

```json
{ "body": "Your replacement ships today." }
```

`body` must be non-empty after trimming (1..10000 chars).

Side effects: the reply is sent through the Gmail client on the customer's
thread, stored as an outbound `human` message, and the ticket status becomes
`handed_off`.

- 200 → the saved message:
  ```json
  { "id": "<uuid>", "author": "human", "body": "Your replacement ships today.", "created_at": "2026-11-03T09:20:00+00:00" }
  ```
- 401 without a session, 404 unknown ticket, 422 empty/missing `body`,
  502 `{"detail": "Could not send the reply", "code": "gmail_send_failed"}` when Gmail rejects the send.

## Auxiliary endpoints (not part of the dashboard flow)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/gmail/status` | session (admin) | `{connected, email, status, last_error}` |
| GET | `/api/gmail/connect` | session (admin) | redirects to Google OAuth |
| GET | `/api/gmail/callback` | session | OAuth callback (`GOOGLE_REDIRECT_URI` in `.env`) |
| GET | `/api/jobs` | session | `{items, total}` job list |
| POST | `/api/jobs/{id}/retry` | session (admin) | retry a dead job |

## Auth rules summary

- `GET /health`, `GET /health/ready`, `POST /api/auth/login` → **no session required**.
- Every other `/api/*` route → 401 without a valid `ca_session` cookie.
- CORS: only origins listed in `CORS_ORIGINS` (`.env`, default `http://localhost:5173`)
  are allowed, with `allow_credentials=True` so the cookie is accepted cross-origin.
