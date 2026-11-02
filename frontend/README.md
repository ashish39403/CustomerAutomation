# Support Admin — dashboard

React + Vite + TypeScript frontend for the AI customer support system, built with
Tailwind CSS v4, shadcn/ui, TanStack Query and React Router. Talks to the FastAPI
backend; the session is an HttpOnly cookie (`ca_session`) set by the login call.

## Run

```bash
# backend, from the repo root (see the port note below)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010

# frontend, in a second terminal
cd frontend
npm install
npm run dev           # http://localhost:5173 (proxies to the backend)
```

Other scripts: `npm run build` (typecheck + bundle), `npm run preview`,
`npm run test` (vitest, run once), `npm run test:watch`, `npm run typecheck`.

Log in with the seeded dashboard account — `admin@local` and the `password`
value from the repo-root `.env` (the backend reads it as `DASHBOARD_PASSWORD` /
`PASSWORD`). Operators log in with `SEED_OPERATOR_EMAIL` /
`SEED_OPERATOR_PASSWORD`.

> **Port note:** the default dev port **8000 is occupied on this machine** by an
> unrelated local service, so the backend runs on **8010** and the Vite dev
> proxy targets `http://127.0.0.1:8010` (`frontend/vite.config.ts`). On a clean
> machine any port works — just keep the proxy target in sync with the
> backend port.

## Configuration

`VITE_API_URL` is the only public value. Leave it empty (usual case) to use
same-origin requests: in dev, Vite proxies `/api` **and** `/health` to the
backend, so no CORS is needed and the session cookie just works. Set an
absolute URL only when calling a backend on another origin, which then needs
CORS with credentials (the backend already allows `http://localhost:5173`).
No secrets belong in the frontend bundle.

## Wiring — every backend endpoint the UI uses is live

The backend serves each router under both `/api` and `/api/v1`; this client
uses the `/api` form.

| Method | Path | Where in the UI | Notes |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | Login page | email or display name |
| POST | `/api/auth/logout` | Log out button | |
| GET | `/api/auth/me` | Session probe + user chip | user object is unwrapped |
| GET | `/api/stats` | Overview stat cards | `today_total` is authoritative |
| GET | `/api/tickets` | Tickets page | server-side pagination, `q` search, status filter |
| GET | `/api/tickets/{id}` | Ticket detail | thread + classification + reasoning |
| POST | `/api/tickets/{id}/reply` | Reply box | Enter sends; answers with the new message |
| PATCH | `/api/tickets/{id}/draft` | Reply box → Save draft | write-only; not loaded back by the API |
| POST | `/api/tickets/{id}/escalate` | Ticket detail → actions | |
| POST | `/api/tickets/{id}/resolve` | Ticket detail → actions | |
| POST | `/api/tickets/{id}/reopen` | Ticket detail → actions | |
| POST | `/api/tickets/{id}/assign` | client function exists | needs a user UUID; no user picker yet |
| GET | `/api/jobs` | Overview → Recent jobs | `status`/`limit`/`offset` |
| POST | `/api/jobs/{id}/retry` | Overview → Retry (dead jobs) | admin |
| GET | `/api/gmail/status` | Overview → System status | **admin returns 403 for operators** |
| GET | `/api/gmail/connect` | Overview → Connect Gmail | admin, full-page OAuth redirect |
| GET | `/api/documents` | Knowledge page | list, all roles |
| POST | `/api/documents` | Knowledge → Upload | admin, multipart (`file`, optional `replace_id`) |
| DELETE | `/api/documents/{id}` | Knowledge → delete | admin, queues the removal |
| GET | `/health`, `/health/ready` | System status card | public, at the root — not under `/api` |

Ticket ids are **UUID strings** throughout; the ticket statuses the API emits
are only `pending`, `auto_replied`, `handed_off` (and `auto_replied` is always
empty because auto-send is disabled server-side).

## Structure

```
src/
  lib/       api.ts (single fetch client + normalizers), types.ts, tickets.ts
             (pure helpers), theme.tsx (dark mode), auth.tsx (session + guard),
             hooks.ts, format.ts, time.ts
  ui/        shadcn/ui components (button, card, input, textarea, badge, table,
             skeleton, separator, alert, collapsible, spinner, empty)
  ...        StatCard, TicketTable, JobTable, SystemStatus, MessageThread,
             ReplyBox, Pagination, Layout, states (loading/error/unavailable)
  pages/     LoginPage, OverviewPage, TicketsPage, TicketDetailPage,
             DocumentsPage, NotFoundPage
  lib/*.test.ts    unit tests (API client, filter logic, normalizers)
```

Notes:

- Listing pages poll every 15 s via TanStack Query; ticket lists are paginated
  **server-side** (status filter, `q` search) and the URL carries page/filter.
- Replies: Enter sends, Shift+Enter newline, Esc clears/closes panels.
- HashRouter so deep links survive being served by FastAPI's static files
  (no SPA fallback on the backend).
- `components.json` is standard shadcn config; primitives import `cn` from the
  npm package. Icons come from lucide-react.
