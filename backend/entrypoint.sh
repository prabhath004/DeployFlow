#!/bin/sh
set -e

case "$1" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    exec python -m app.workers.deployment_worker
    ;;
  migrate)
    exec alembic upgrade head
    ;;
  api-with-migrate)
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  *)
    # Pass through any other command (sh, alembic revision ..., etc.)
    exec "$@"
    ;;
esac
