# INTEGRATION_LOG.md — integration journal

Contract: `CONTRACT.md` (source of truth). Rules: phase by phase, one commit per
phase (`phase N: <name>`), contract wins over either side, no hard-coded URLs or
secrets (backend `.env`, frontend `VITE_API_URL`).

**Environment note:** the backend and frontend agents were editing this same
working tree while the integration ran (backend `app/`, frontend `frontend/src/`).
Every phase below therefore re-reads both sides right before touching them, and
fixes whatever disagrees with `CONTRACT.md`.

---

## Phase 0 — Contract and boot

**What changed**
- Wrote `CONTRACT.md`: the 7 pinned endpoints plus the auxiliary routes, snake_case
  bodies, status vocabulary (`pending` / `auto_replied` / `handed_off`), cookie rules.
- `app/main.py`: mounted the health router at the **root** (`GET /health`), which is
  what the contract pins (it used to be reachable only at `/api/v1/health`).
- `.gitignore`: added `node_modules/` before the first commit.

**Tested**
- `curl http://127.0.0.1:8000/health` → `200 {"status":"ok"}`.
- Dashboard dev server serves the login page: `GET http://localhost:5173/` → 200,
  `/src/main.tsx` and `/src/pages/LoginPage.tsx` compile through Vite → 200.
- `npm run typecheck` → clean (after removing an unused `LoginResponse` import that
  was failing `tsc -b`).
- Backend `uv run pytest` → 24 passed, 1 failed (see open issues).

**Failed / fixes**
- *Duplicate dev server:* a Vite server was already bound to `5173`; `npm run dev`
  fell back to `5174`. Killed the duplicate so the contract port `5173` stays canonical.
- *Unused import* `LoginResponse` in `frontend/src/lib/api.ts` broke `tsc -b` → removed.
- *Unit tests red (5):* `api.test.ts` expected `/api/...` while `api.ts` called
  `/api/v1/...`. This is the Phase-1 prefix deviation, fixed there (contract wins).
- **No browser available in this environment** — "no console errors" was verified by
  Vite successfully transforming `main.tsx` + `LoginPage.tsx` and by a clean `tsc -b`,
  not by a real browser session.

---

## Phase 1 — CORS and auth

**What changed**
- Backend `app/main.py`: added a `_require_session` middleware — every `/api/*`
  path except `POST /api/auth/login` (and its `/api/v1` alias) answers
  `401 {"detail":"Not authenticated","code":"unauthorized"}` without a session.
  Middleware order is CORS → session → auth check, so CORS headers still apply to 401s.
- CORS already reads `CORS_ORIGINS` from `.env` with `allow_credentials=True`.
- Login already reads `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD` (`EMAIL`/`PASSWORD`
  fallbacks) from `.env`, seeds them at startup and returns the `ca_session` cookie
  (HttpOnly, SameSite=Lax, Secure in production).
- Frontend `frontend/src/lib/api.ts`: dropped the internal `/api/v1` prefix — every
  path now matches the contract exactly (`/api/auth/login`, `/api/auth/me`,
  `/api/auth/logout`, `/api/stats`, `/api/tickets…`, `/api/jobs…`, `/api/gmail/status`,
  root `/health/ready`). Doc comments, `types.ts` comments, `api.test.ts` expectations
  and the `UnavailableState` endpoint labels were updated to the same paths.

**Tested**
- Wrong password → `401 {"detail":"Invalid credentials","code":"unauthorized"}`.
- Correct password → `200` + `set-cookie: ca_session=…; path=/; Max-Age=604800; httponly; samesite=lax`.
- `GET /api/stats` with no cookie → `401`.
- Full browser path (through the Vite proxy on `5173`): login → `200` + cookie,
  `/api/stats` with cookie → `200 {"auto_replied":0,"handed_off":0,"pending":3,"today_total":3}`,
  without cookie → `401`.
- CORS: `Origin: http://localhost:5173` → `access-control-allow-origin` echoed +
  `allow-credentials: true`; `Origin: http://evil.example` → **no** ACAO header;
  preflight `OPTIONS /api/auth/login` → allowed methods/headers.
- `npm run typecheck` clean, `npm run test` → 24/24 passed.

**Failed / fixes**
- First login curl hit a reloading server (timeout) and PowerShell mangled the inline
  JSON body (`422 json_invalid`) → re-ran with the body in a file (`-d @file`).

---

## Phase 2 — Stats / Overview

**What changed**
- `CONTRACT.md`: added the **internal → API status mapping** table (the backend
  gained a distinct `auto_replied` state in `002_auto_replied_status.py`, so the
  contract now records which internal states bucket into `pending` / `auto_replied` /
  `handed_off`). The same sets in `app/api/routes/tickets.py` feed both `/api/stats`
  and the `/api/tickets` filter, so counts match by construction.
- Frontend `frontend/src/lib/types.ts`: `StatsResponse` gained `today_total`.
- Frontend `frontend/src/pages/OverviewPage.tsx`:
  - "Total today" now reads `stats.today_total` from the API (server-side count of
    tickets created today, UTC) instead of summing the other three cards client-side.
  - Re-added the **error branch**: a non-404 stats failure (backend down, 5xx) renders
    `ErrorState` with `apiErrorMessage(...)` + a Retry button instead of blank cards.
    (This code had been lost in a parallel agent's rewrite; re-applied.)

**Tested**
- `GET /api/stats` (session cookie) → `{"auto_replied":5,"handed_off":1,"pending":0,"today_total":0}`.
- Direct SQL against the same DB with the identical mapping →
  `{"auto_replied":5,"handed_off":1,"pending":0,"today_total":0}` — **exact match**
  (internal counts: `auto_replied`×5, `escalated`×1).
- `npm run typecheck` → clean; `npm run test` → 30/30 passed (includes the stats
  fixture with `today_total` and the `/api/stats` path assertion).
- Vite transforms `OverviewPage.tsx` → 200 (the error branch compiles in dev).
- Error path (code-verified, no browser): backend unreachable → `fetch` throws
  `ApiError(0, "Network error — could not reach the API")` → `isNotImplemented` is
  false (only 404) → `statsFailed` → `ErrorState` with that message + Retry;
  react-query `refetchInterval: 15_000` auto-retries, so the cards recover on their
  own once the backend is back.

**Failed / fixes**
- Early SQL helper used the pre-`AUTO_REPLIED` mapping (`replied` → auto_replied) and
  disagreed with the API (`SQL: auto_replied 0 / API: 5`) → the helper was updated to
  the current mapping; the mismatch was in the helper, not the API.
- **Limitation:** no browser automation in this environment — the backend-down →
  error UI → recovery loop was verified by code path + typecheck + Vite transform,
  not by a live browser session.

---

## Phase 3 — Tickets list

**What changed**
- No code changes needed this phase: the backend routes
  (`GET /api/tickets?status=&page=&page_size=&q=`) and the frontend server-side
  wiring (landed in `e570906`) already match the contract. Verified only.

**Tested** (all with a real session cookie, backend on `:8000`)
- Filter counts vs `/api/stats` — exact match:
  `stats={"auto_replied":5,"handed_off":1,"pending":0}` vs list totals
  `pending=0, auto_replied=5, handed_off=1, all=6`.
- Pagination: `page_size=4` → page 1 (4 ids) + page 2 (2 ids), **0 overlap**,
  `updated_at DESC` order confirmed; `total=6, pages=2` on both pages.
- Beyond-range page (`page=9`) → `200 {"items":[], ...}` (empty state, not an error).
- Search: `q=ashish` → 4 hits, all matching `customer_email`;
  `q=order` → 1 hit matching `subject` — both fields covered, case-insensitive.
- Validation: `status=bogus` → `422` (`literal_error`, `code: validation_error`);
  `page=0` → `422` (`ge: 1`).
- Frontend: `TicketsPage` sends `status` / `page` / `page_size` / `q` to the server
  (300ms debounce, page reset on filter/search change, distinct empty vs no-match
  states, server-owned `pages` for `Pagination`). Vite transform → 200;
  `tsc -b` clean, `npm run test` 30/30 (run at Phase 2, nothing changed since).

**Failed / fixes**
- None.

---

## Phase 4 — Ticket detail and 404

**What changed**
- Frontend `frontend/src/pages/TicketDetailPage.tsx`: a 404 on the detail endpoint
  used to render the misleading *"The ticket pipeline is not part of the backend yet."*
  (the `isNotImplemented` branch treats any 404 as "endpoint missing"). Per the
  contract a detail 404 means **ticket not found**, so the page now always shows
  `apiErrorMessage(...)` → *"Ticket not found (HTTP 404)"* + Retry. The 404-no-retry
  predicate in `retry:` is kept (never retry a missing ticket).

**Tested**
- `GET /api/tickets/{uuid}` → 200 with the contract shape: `messages` ordered
  oldest → newest (verified by comparing the timestamp order), `author` values in
  `{customer, human}` observed, `classification` + `reasoning` present on a
  classified ticket (nullable per contract when absent), UUID string ids throughout.
- Unknown UUID → `404 {"detail":"Ticket not found","code":"not_found"}` — exact body.
- Malformed id (`not-a-uuid`) → same 404 body (not a 422).
- Detail without cookie → `401 {"detail":"Not authenticated","code":"unauthorized"}`.
- Frontend: ids are `string` in `types.ts` (no `Number()` coercion), `fetchTicket`
  hits `/api/tickets/{id}` with `encodeURIComponent`. `tsc -b` clean,
  `npm run test` 30/30, Vite transform of `TicketDetailPage.tsx` → 200.

**Failed / fixes**
- See "What changed" — the 404 message mismatch was found during this phase's review
  and fixed before committing.

---

## Phase 5 — Human reply

**What changed**
- No code changes: backend `reply_to_ticket` (`app/modules/tickets/service.py`) and
  the frontend `ReplyBox` already match the contract. Verified only.

**Tested**
- Safe cases (all exact contract bodies):
  - `{"body":"   "}` → `422` (`string_too_short`, stripped before validation);
    `{}` → `422` (`Field required`).
  - Unknown ticket → `404 {"detail":"Ticket not found","code":"not_found"}`.
  - No cookie → `401 {"detail":"Not authenticated","code":"unauthorized"}`.
- **Live Gmail send** (Gmail connected as `demosydeny3590@gmail.com`; recipient was
  the agents' test account `extraction311@gmail.com`, both messages clearly marked
  "Integration test … please ignore"):
  - `POST /api/tickets/{id}/reply` → `200` with the exact saved message shape:
    `{"id":"<uuid>","author":"human","body":"…","created_at":"…"}`.
  - Thread detail afterwards: last message `author=human` with the same body
    (stored as outbound human message) — and `GET /api/tickets/{id}` still 200.
  - **Status transition verified on a second ticket:** before `status=auto_replied`
    → after reply `status=handed_off` (internal `replied` → API `handed_off` per the
    contract mapping). `/api/stats` moved consistently afterwards.
- 502 path is implemented (`gmail_send_failed` on rejected/unknown send or no
  connected account) but not exercised live — forcing a Gmail rejection would risk
  the real mailbox.
- Frontend `ReplyBox`: trims the body client-side, `postReply(id, body)` →
  `POST /api/tickets/{id}/reply` with `{body}`, invalidates `ticket`/`tickets`/
  `stats` on success, shows `apiErrorMessage` (so a 502 renders
  "Could not send the reply (HTTP 502)") in a destructive alert.

**Failed / fixes**
- None.

---

## Phase 6 — In-process poller + live polling

**What changed**
- `app/core/config.py`: `worker_in_process: bool = True` — the API process also
  runs the jobs worker (which drives the Gmail poller), so
  `fastapi dev app/main.py` alone starts the whole system.
- `app/main.py`: lifespan starts/stops a daemon thread running the same `tick()`
  as the standalone `python -m app.worker` (worker id `api:<hex8>`), gated by the
  flag. Job leases make running both safe.
- `tests/conftest.py`: sets `WORKER_IN_PROCESS=false` **before** importing the app,
  so pytest never starts a worker or hits the real Gmail mailbox. (This file also
  carries the backend agent's autouse `_cleanup_test_gmail_accounts` fixture, added
  in the same shared working tree — committed together here.)
- Frontend: **no change needed** — every page/component already polls with
  `refetchInterval: REFRESH_MS` (15s) and TanStack Query v5 defaults handle
  pause/refresh (see Tested).

**Tested**
- Fresh boot logs `worker.in_process_started worker_id=api:7e347bff`, then
  `jobs.claimed` (by `api:7e347bff`) for `process_email` and `poll_gmail`, plus
  `gmail.poll_complete` events. A **second server boot in a parallel shell** logged
  `worker.in_process_started api:e3df7d09` — the feature is code-driven, not
  specific to my shell.
- **End-to-end ingest:** sent a test email from the plus-alias
  `demosydeny3590+ca-test@gmail.com` into the connected mailbox (marker
  `ca-phase6-42225f3a`, gmail id `1a1a60da2fd77020`) → watcher confirmed the
  in-process worker claimed the `poll_gmail` job (`locked_by='api:7e347bff'`) and
  **tickets were created** with those markers
  (`customer=demosydeny3590+ca-test@gmail.com`; the script ran twice, so a second
  marker `ca-phase6-fe1a958e` also produced a ticket).
- **Coexistence:** standalone `python -m app.worker` and the API's in-process
  worker both claim jobs without double-completing (leases). Observed one
  `uq_tickets_gmail_thread_id` UniqueViolation when both ingested the same message
  → job retry recovered it (attempts 2 succeeded).
- **Frontend:** `tsc -b` clean; `npm run test` 30/30. All pages and
  `SystemStatus` use `refetchInterval: REFRESH_MS` (15s). Pause-on-hidden /
  refresh-on-focus verified against TanStack Query v5 defaults read from
  `@tanstack/query-core` `.d.ts`: `refetchIntervalInBackground` defaults to
  **false** (interval stops while the tab is hidden) and `refetchOnWindowFocus`
  defaults to **true** (refetch when the tab returns) — no custom code needed.

**Failed / fixes / open issues**
- **Gmail poll outage 10:19–10:30 UTC** (`gmail refresh token decrypt failed`,
  poll jobs died after retries): another agent inserted a fake *connected* account
  `support-7f8f5dd82f@harborandpine.test` with plaintext `test-token`, and
  `enqueue_poll_if_due()` selects a connected account **without ORDER BY**, so poll
  jobs targeted the fake account and Fernet decrypt failed. The fake account has
  since been deleted (its poll jobs remain `dead` with `gmail account missing`)
  and the real account's token decrypts OK — polls succeed again
  (`poll_gmail` succeeded 10:31:40 and 10:32:20 UTC). **Latent bug (open):**
  `enqueue_poll_if_due` should order deterministically and/or skip accounts whose
  token is not Fernet-shaped.
- `ai.classifier_failed: 'Settings' object has no attribute 'classifier_timeout_s'`
  — the backend agent's in-flight (uncommitted) `classifier.py` references a
  setting not yet present in `config.py`. Not contract-related; their edit to fix.
- **Backend pytest: 32 passed, 2 failed** — both classified, neither is a Phase 6
  regression:
  - `tests/test_jobs.py::test_reaper_recovers_expired_lease` →
    `AssertionError: assert 'running' == 'retry_wait'` (line 69). The reaper itself
    works (`jobs.lease_expired` logged; `reap_expired_leases() >= 1` passed); a
    **concurrently running worker** (standalone `app.worker` or a dev server's
    in-process worker) re-claims the requeued test job between the reaper and the
    assertion. The full-suite run shows the in-process worker claiming `test.noop`
    jobs mid-run. The test assumes no live worker exists — ran twice, failed both
    times (reported per rule, no fix loop). Suggested: run pytest with servers
    stopped, or give tests an isolated DB.
  - `tests/test_policy.py::test_refund_always_escalates` →
    `assert 'refund' in 'category requires a human'`: the backend agent's
    **uncommitted** `policy.py` rewrite returns a generic category reason. The
    decision is still `ESCALATE` (behavior correct, reason string differs);
    owner should align reason or test when committing.
- Environment churn: a WatchFiles reloader was once wedged (missed `app/main.py`
  edits) requiring a manual backend restart; multiple agents run competing servers
  on `:8000` (ghost PID-0 `LISTENING` rows appear in `netstat`). Always re-read
  files before editing and re-verify after commits.
- **Limitation:** no browser automation in this environment — pause-on-hidden was
  verified from library defaults + code, not by a live hidden tab.

---

## Phase 7 — Production checks + final report

**What changed** — no code changes; verification only.

**Tested**
- **A. Public probes (no cookie):** `GET /health` → `200 {"status":"ok"}`;
  `GET /health/ready` → `200 {"status":"ok","database":{...},"qdrant":{...},"gmail":{...}}`.
- **B. Auth sweep (no cookie):** 7 GET + 3 POST protected routes
  (`/api/auth/me`, `/api/stats`, `/api/tickets`, detail, `/api/gmail/status`,
  `/api/jobs`, `/api/documents`, reply, escalate, job retry) → **all 401**
  `{"detail":"Not authenticated","code":"unauthorized"}`.
- **C. CORS:** allowed origin `http://localhost:5173` →
  `access-control-allow-origin: http://localhost:5173` +
  `access-control-allow-credentials: true`; disallowed origin
  `http://evil.example` → **no** ACAO header. Origins come from `.env`
  `CORS_ORIGINS` via `settings.cors_origin_list` (nothing hard-coded).
- **D. Production boot:** `APP_ENV=production` + `uvicorn app.main:app --port 8010`
  → `/health` 200; login 200 sets
  `ca_session=…; path=/; Max-Age=604800; httponly; samesite=lax; **secure**`
  (HttpOnly, SameSite=Lax, Secure only in production, 7-day max-age — exact
  contract); wrong password → `401 {"detail":"Invalid credentials","code":"unauthorized"}`;
  `/api/stats` with the cookie → 200. Clean shutdown afterwards.
- **E. Frontend production build:** `npm run build` (`tsc -b && vite build`) →
  pass (`dist/` emitted, 17.4s).
- **F. No hard-coded secrets:** no backend URL / password literals in
  `frontend/src`; no literal dashboard password in `app/`; `.env` is git-ignored
  and untracked (`git ls-files .env` → empty).
- **Final smoke of the seven pinned endpoints** on the running dev server:
  `/health` 200 · login 200 · `/api/stats` 200 · list 200
  (`total=3 pages=2 items=2`) · detail 200 (2 messages, authors `bot,customer`) ·
  reply with empty body → 422 exact body · dashboard `:5173` → 200.

**Failed / fixes** — none this phase.

---

# FINAL REPORT

### Phases passed

| Phase | Result | Evidence / commit |
| --- | --- | --- |
| 0 Contract & boot | ✅ | `CONTRACT.md` written; `GET /health` at root → 200; both dev servers up |
| 1 CORS & auth | ✅ | login/logout/me, cookie rules, 401/422 bodies exact — `0d2615b` |
| 2 Stats | ✅ | `/api/stats` == direct SQL; OverviewPage error branch — `4575cc8` |
| 3 Tickets list | ✅ | filter totals == stats; pagination 0-overlap; `q` search; 422s — `76707f6` |
| 4 Ticket detail | ✅ | 200/404/401 exact; frontend 404 message fixed — `1238a39` |
| 5 Human reply | ✅ | 422/404/401 exact; 2 live Gmail sends → 200; `auto_replied`→`handed_off` — `f67cd5c` |
| 6 In-process poller | ✅ | worker `api:7e347bff` claimed jobs; test email → ticket created; frontend 15s polling + pause-on-hidden (TanStack defaults); `tsc` clean, vitest 30/30 — `795e03d` |
| 7 Production checks | ✅ | checks A–F + 7-endpoint final smoke (this section) |

Backend pytest: **32 passed, 2 failed** — both failures classified as environment /
other-agent issues (see open issues 2–3), not contract or Phase 6 regressions.

### Contract deviations + reasons

The contract was changed **first**, in `CONTRACT.md`, then reported here:

1. **Phase 2 — status mapping table + `today_total`** (commit `4575cc8`): the
   backend gained a distinct internal `auto_replied` state
   (`002_auto_replied_status.py`), so the contract now records which internal
   states bucket into `pending` / `auto_replied` / `handed_off`, and documents
   `today_total` as a server-side UTC-day count. The same sets feed `/api/stats`
   and the `/api/tickets` filter, so counts match by construction.
2. **Phase 0 — `GET /health` at the root** (folded into the baseline/phase-1
   commit): the route used to exist only at `/api/v1/health`; the contract pins
   the root path, so the mount was moved to match.

Everything else was fixed **on the code side to match the contract** (no contract
change): frontend `today_total` usage, ticket-detail 404 message, UUID string
ids, server-side pagination/search, 422/401/404/502 bodies. Both sides now match
`CONTRACT.md` for all seven pinned endpoints and the auxiliary routes.

### Open issues

1. **`enqueue_poll_if_due()` picks a connected Gmail account with no `ORDER BY`**
   (`app/modules/jobs/worker.py`). Test runs insert fake connected accounts
   (`…@harborandpine.test`, plaintext `test-token`) and poll jobs then target
   them → `gmail refresh token decrypt failed` / `gmail account missing` dead
   jobs (poll outage 10:19–10:30 UTC on 2026-11-04, self-recovered after the
   fake account was cleaned up). Fix: deterministic ordering + skip accounts
   whose token is not Fernet-shaped.
2. **`tests/test_jobs.py::test_reaper_recovers_expired_lease` fails while any
   worker is live** — `assert 'running' == 'retry_wait'` (line 69): the reaper
   works (`jobs.lease_expired` logged), but a concurrently running worker
   (standalone `python -m app.worker` or a dev server's in-process worker)
   re-claims the requeued test job between the reaper and the assertion.
   Reproduced twice. Fix: run pytest with servers stopped, or give tests an
   isolated database.
3. **`tests/test_policy.py::test_refund_always_escalates`** —
   `assert 'refund' in 'category requires a human'`: caused by the backend
   agent's **uncommitted** `policy.py` rewrite. The decision is still
   `ESCALATE` (behavior correct); owner should align the reason string or the
   test when committing.
4. **`ai.classifier_failed: 'Settings' object has no attribute 'classifier_timeout_s'`**
   — the backend agent's in-flight `classifier.py` references a setting not yet
   added to `config.py`. Not contract-related.
5. **502 reply path not exercised live** (`gmail_send_failed` is implemented but
   forcing a Gmail rejection would risk the real mailbox).
6. **Two workers can ingest the same Gmail message concurrently** →
   `uq_tickets_gmail_thread_id` UniqueViolation; recovered by job retry (no data
   loss). A dedupe-before-insert would remove the retry noise.
7. **No browser automation in this environment** — error states and
   pause-on-hidden were verified via code path + `tsc` + vitest + Vite
   transforms, not a live browser session.

### Exact local run commands

```bash
# --- Backend (from the repo root; all secrets/URLs come from .env) ---
uv run fastapi dev app/main.py        # http://127.0.0.1:8000
#   starts the API + seeds + the in-process jobs worker (Gmail poller) automatically
uv run python -m app.worker           # OPTIONAL standalone worker (safe alongside;
                                      #  job leases prevent double-claims)

# --- Frontend (separate terminal) ---
cd frontend
npm install
npm run dev                           # http://localhost:5173 (Vite proxies /api → :8000;
                                      #  base URL from VITE_API_URL, empty = same origin)

# --- Tests ---
uv run pytest -q                      # backend suite (stop servers first — open issue 2)
cd frontend
npm run typecheck                     # tsc -b
npm run test                          # vitest (30 tests)
npm run build                         # production build

# --- Login (creds seeded from .env DASHBOARD_USERNAME / DASHBOARD_PASSWORD) ---
curl -c cookies.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin","password":"<DASHBOARD_PASSWORD>"}'
# then: curl -b cookies.txt http://127.0.0.1:8000/api/stats
```

*Environment note: the backend, frontend and other agents shared this working
tree throughout; every phase re-read both sides immediately before touching them
and committed only its own files (`git add <paths>`, never `git add -A`).*
