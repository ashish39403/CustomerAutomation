# CI/CD Pipeline

GitHub Actions se **lint → tests → docker build → GHCR push → SSH deploy**, aur running containers Docker Compose me.

## Files

| File | Kya karta hai |
|---|---|
| `.github/workflows/ci.yml` | Har push/PR pe: ruff lint, pytest (Postgres 18 service + alembic), Docker build. `main` pe: image GHCR me push. |
| `.github/workflows/deploy.yml` | Manual button + `main` push pe: server pe SSH karke `docker compose pull && up -d`. |
| `Dockerfile` | uv sync, non-root user, `entrypoint.sh` jo `alembic upgrade head` chalata hai. |
| `docker/entrypoint.sh` | Migrations. Sirf api container chalata hai; worker pe `RUN_MIGRATIONS=0` (race avoid). |
| `docker-compose.yml` | `api` + `worker` + `qdrant`, optional `postgres` (`docker compose up postgres`). |
| `.dockerignore` | tests / frontend / dev-files image ke bahar. |

## CI flow (har PR/push)

1. **lint** — `uv sync --frozen` + `ruff check .` (E501 off hai — AI prompt strings intentionally lambi hain).
2. **test** — `postgres:18-alpine` service (`test/test/customerautomation`) → `alembic upgrade head` → `uv run pytest -q`.
3. **build** — Dockerfile build, push nahi (GHA layer cache).
4. **push** (sirf `main`) — `ghcr.io/<owner>/customerautomation:sha-xxxx` + `:latest` (GHCR lowercase rule pakka).

## Deploy setup (ek baar)

`Settings > Secrets and variables > Actions` me:

**Variables (non-secret):**

| Name | Example |
|---|---|
| `DEPLOY_HOST` | `203.0.113.10` |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_DIR` | `/opt/customerautomation` |

**Secrets:**

| Name | Note |
|---|---|
| `SSH_PRIVATE_KEY` | poora private key; public half server ke `~/.ssh/authorized_keys` me |

Server pe **ek baar** GHCR login (PAT me `read:packages` scope):

```bash
docker login ghcr.io -u <github-username> -p <PAT>
```

Server ke `docker-compose.yml` me images pull se aaye:

```yaml
api:
  image: ghcr.io/<owner>/customerautomation:latest
worker:
  image: ghcr.io/<owner>/customerautomation:latest
```

(`<owner>` lowercase — e.g. `ashish/customerautomation`.)

`DEPLOY_HOST`/`DEPLOY_USER` set nahi hain to deploy job khud skip hota hai — CI pehle hi 3 checks pe fail ya pass hoga.

## Local Docker

```bash
docker compose up --build
docker compose logs -f api    # startup + alembic logs
docker compose ps             # health check status
docker compose up -d postgres # offline dev ke liye (DATABASE_URL: postgresql://postgres:postgres@localhost:5432/co)
```

## Important

- `GOOGLE_TOKEN_ENCRYPTION_KEY` kabhi badalna ho to naye key se tokens re-encrypt karke hi deploy karo — warna `gmail refresh token decrypt failed` waps aayega (aaj wala issue).
- Migrations api container ke start pe chalti hain; server ke `.env` me `DATABASE_URL` (Neon) hona chahiye. Deploy script sirf new image `pull` karta hai — migrations `entrypoint.sh` se khud ho jate hain.
