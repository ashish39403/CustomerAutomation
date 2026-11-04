# CI Pipeline (GitHub Actions)

**Abhi sirf CI hai** (lint + tests + docker build). Deployment/GHCR push server setup hone pe add honga.

## Files

| File | Kya karta hai |
|---|---|
| `.github/workflows/ci.yml` | Har push/PR pe: ruff lint, pytest (Postgres 18 service + alembic), Docker build (push nahi). |
| `Dockerfile` | uv sync, non-root user, `entrypoint.sh` jo `alembic upgrade head` chalata hai. |
| `docker/entrypoint.sh` | Migrations. Sirf api container chalata hai; worker pe `RUN_MIGRATIONS=0` (race avoid). |
| `docker-compose.yml` | `api` + `worker` + `qdrant`, optional `postgres` (`docker compose up postgres`). |
| `.dockerignore` | tests / frontend / dev-files image ke bahar. |

## CI flow (har PR/push pe 3 checks)

1. **lint** — `uv sync --frozen` + `ruff check .` (E501 off hai — AI prompt strings intentionally lambi hain).
2. **test** — `postgres:18-alpine` service (`test/test/customerautomation`) → `alembic upgrade head` → `uv run pytest -q`.
3. **build** — Dockerfile build hota hai, push nahi (GHA layer cache).

Triggers: `push main`, koi bhi `pull_request`, manual `workflow_dispatch`.

## Future (jab deployment aaye)

Es cheez ka plan ready hai (`main` pe): image GHCR push (`:<sha>` + `:latest`) + SSH deploy (`docker compose pull && up -d`). Us waqt ye chahiye hoga:

- repo Variables: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_DIR`
- secret: `SSH_PRIVATE_KEY`
- server pe GHCR login (PAT with `read:packages`)

## Local Docker

```bash
docker compose up --build
docker compose logs -f api    # startup + alembic logs
docker compose ps             # health check status
docker compose up -d postgres # offline dev ke liye (DATABASE_URL: postgresql://postgres:postgres@localhost:5432/co)
```

## Important

- `GOOGLE_TOKEN_ENCRYPTION_KEY` kabhi badalna ho to naye key se tokens re-encrypt karke hi deploy karo — warna `gmail refresh token decrypt failed` waps aayega (aaj wala issue).
- Migrations api container ke start pe chalti hain; `.env` me `DATABASE_URL` (Neon) hona chahiye.
