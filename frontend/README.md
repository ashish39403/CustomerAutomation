# Support Admin — dashboard

React + Vite + TypeScript frontend for the AI customer support system, built with
Tailwind CSS v4, shadcn/ui, TanStack Query and React Router. Talks to the FastAPI
backend (`/api/v1`); the session is an HttpOnly cookie (`ca_session`) set by
`POST /api/v1/auth/login`.

## Run

```bash
# backend, from the repo root (port 8000)
uv run fastapi dev app/main.py

# frontend, in a second terminal
cd frontend
npm install
npm run dev           # http://localhost:5173  (matches the default CORS origin)
```

Other scripts: `npm run build` (typecheck + bundle), `npm run preview`,
`npm run test` (vitest, run once), `npm run test:watch`, `npm run typecheck`.

Log in with the seeded dashboard account — `admin@local` (or the display name,
e.g. `admin`) and `DASHBOARD_PASSWORD` from the backend `.env`.

## Configuration

`VITE_API_URL` is the only public value. Leave it empty to use same-origin
requests — in dev, Vite proxies `/api` to `http://127.0.0.1:8000`, so no CORS is
needed and the cookie just works. Set an absolute URL (e.g.
`http://localhost:8000`) only when calling a backend on another origin, which
then needs CORS with credentials (the backend already allows
`http://localhost:5173`). No secrets belong in the frontend bundle.

## Wiring

Connected to the live backend today:

| Method | Path | Where in the UI |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Login page (email or display name) |
| POST | `/api/v1/auth/logout` | Log out button |
| GET | `/api/v1/auth/me` | Session probe + user chip |
| GET | `/api/v1/health/ready` | Overview → System status |
| GET | `/api/v1/gmail/status` | Overview → Gmail account row |
| GET | `/api/v1/gmail/connect` | Overview → "Connect Gmail" (admin, full-page OAuth redirect) |
| GET | `/api/v1/jobs?status=&limit=&offset=` | Overview → Recent jobs |
| POST | `/api/v1/jobs/{id}/retry` | Overview → Retry button on dead jobs (admin) |

Wired but pending a later backend phase (they answer 404 today, and the pages
show a friendly "not available yet" state instead of an error):

| Method | Path | Where in the UI |
| --- | --- | --- |
| GET | `/api/v1/stats` | Overview stat cards |
| GET | `/api/v1/tickets?status=&page=` | Tickets page |
| GET | `/api/v1/tickets/{id}` | Ticket detail |
| POST | `/api/v1/tickets/{id}/reply` | Reply box in ticket detail |

## Structure

```
src/
  lib/       api.ts (single fetch client + normalizers), types.ts, tickets.ts
             (pure filter/sort/pagination), theme.tsx (dark mode), auth.tsx
             (session state + route guard), hooks.ts, format.ts, time.ts
  ui/        shadcn/ui components (button, card, input, textarea, badge, table,
             skeleton, separator, alert, collapsible, spinner, empty)
  ...        StatCard, TicketTable, JobTable, SystemStatus, MessageThread,
             ReplyBox, Pagination, Layout, states (loading/error/unavailable)
  pages/     LoginPage, OverviewPage, TicketsPage, TicketDetailPage, NotFoundPage
  lib/*.test.ts    unit tests (API client, filter logic, normalizers)
```

Notes:

- Overview, tickets list and detail all poll every 15 s.
- Replies: Enter sends, Shift+Enter newline, Esc clears/closes panels.
- HashRouter so deep links survive being served by FastAPI's static files
  (no SPA fallback on the backend).
- `components.json` is standard shadcn config; primitives import `cn` from the
  npm package. Icons come from lucide-react.
