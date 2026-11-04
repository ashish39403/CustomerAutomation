FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so code changes rebuild this layer only.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY app ./app
# The API seeds the knowledge base from this folder at startup.
COPY knowledge_docs ./knowledge_docs
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh \
    && groupadd --system app \
    && useradd --system --gid app app \
    && mkdir -p /app/data/uploads \
    && chown -R app:app /app/data

USER app

EXPOSE 8000

ENTRYPOINT ["entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
