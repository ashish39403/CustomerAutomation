#!/bin/sh
set -e

# Apply DB migrations once per deployment. The API container runs them by
# default (RUN_MIGRATIONS=1); the worker container sets RUN_MIGRATIONS=0 so
# two containers never race on the same migration. If the database is only
# briefly unreachable we keep the app bootable — /health/ready will report
# the database status and the worker retries until the DB is reachable.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    if alembic upgrade head; then
        echo "entrypoint: alembic upgrade head OK"
    else
        echo "entrypoint: WARNING — alembic upgrade head failed, starting app anyway" >&2
    fi
fi

exec "$@"
