# Support Admin — dashboard

React + Vite + TypeScript frontend for the AI customer support system. Talks to the
FastAPI backend; session is a cookie set by `POST /api/auth/login`.

## Run

```bash
# backend, from the repo root (port 8000)
uv run fastapi dev app/main.py

# frontend, in a second terminal
cd frontend
npm install
npm run dev           # http://localhost:5173
```

Other scripts: `npm run build` (typecheck + bundle), `npm run preview`,
`npm run test` (vitest, run once), `npm run test:watch`.

## Configuration

`VITE_API_URL` is the only public value. Leave it empty to use same-origin
requests — in dev, Vite proxies `/api` to `http://127.0.0.1:8000`, so no CORS and
the session cookie just works. Set an absolute URL (e.g. `http://localhost:8000`)
only when calling a backend on another origin, which then needs CORS with
credentials. No secrets belong in the frontend bundle.

## API contract

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/auth/login` | `{ username, password }`, sets a session cookie |
| GET | `/api/stats` | `{ auto_replied, handed_off, pending }` |
| GET | `/api/tickets?status=&page=` | list of tickets (id, customer_email, subject, status, updated_at) |
| GET | `/api/tickets/{id}` | ticket with full message thread; optional `classification` and `reasoning` |
| POST | `/api/tickets/{id}/reply` | `{ body }`, sends a human reply |

Status values are `auto_replied`, `handed_off`, `pending` (plus `all` in the UI
filter). The client includes a small normalizer, so responses missing
`author`-style fields still render (aliases `role` / `sender` / `direction in-out`
are mapped to `customer | bot | human`).

## Structure

```
src/
  lib/       api.ts (single fetch client + normalizers), types.ts, tickets.ts (pure
             filter/sort/pagination logic), theme.tsx (dark mode), auth.tsx (session
             state + route guard), hooks.ts, format.ts, constants.ts
  ui/        Button, Input/Textarea, StatusBadge, Spinner, States (loading/empty/error), icons
  ...        StatCard, TicketTable, MessageThread, ReplyBox, Pagination, Layout
  pages/     LoginPage, OverviewPage, TicketsPage, TicketDetailPage, NotFoundPage
  lib/*.test.ts    unit tests (API client, filter logic)
```

Notes:

- Overview polls `stats` and recent tickets every 15 s (Ticket list/detail too).
- Replies: Enter sends, Shift+Enter newlines, Esc clears/closes panels.
- HashRouter is used so deep links survive being served by FastAPI's static files
  (no SPA fallback on the backend). Switch to BrowserRouter if the backend adds one.
- The "Log out" button clears local state; the cookie itself is only cleared
  server-side — add a `POST /api/auth/logout` endpoint when the backend has it.
