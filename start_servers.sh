#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PID_FILE="/tmp/e-commerce-start_servers.pids"
BACKEND_LOG="/tmp/e-commerce-backend.log"
FRONTEND_LOG="/tmp/e-commerce-frontend.log"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

wait_for_http() {
    local name="$1"
    local url="$2"
    local pid="$3"
    local log_file="$4"

    for _ in $(seq 1 90); do
        if ! kill -0 "$pid" >/dev/null 2>&1; then
            echo "$name exited before becoming ready." >&2
            tail -n 40 "$log_file" >&2 || true
            return 1
        fi
        if curl --silent --fail --max-time 2 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done

    echo "Timed out waiting for $name at $url." >&2
    tail -n 40 "$log_file" >&2 || true
    return 1
}

require_command uv
require_command npm
require_command node
require_command curl
require_command setsid

if [ -f "$PID_FILE" ]; then
    "$ROOT_DIR/stop_servers.sh" >/dev/null 2>&1 || true
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

if [ ! -f "$FRONTEND_DIR/.env.local" ] && [ -f "$FRONTEND_DIR/.env.local.example" ]; then
    cp "$FRONTEND_DIR/.env.local.example" "$FRONTEND_DIR/.env.local"
fi

cd "$BACKEND_DIR"
uv sync --group dev --group test

uv run python - <<'PY'
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.apps.core.config import Settings

settings = Settings()
async_url = make_url(settings.DATABASE_URL)
sync_url = make_url(settings.SYNC_DATABASE_URL)

for name, url in {"DATABASE_URL": async_url, "SYNC_DATABASE_URL": sync_url}.items():
    if url.get_backend_name() != "postgresql":
        raise SystemExit(f"{name} must point to PostgreSQL.")

database_name = sync_url.database
if not database_name:
    raise SystemExit("SYNC_DATABASE_URL must include a PostgreSQL database name.")

admin_engine = create_engine(sync_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
quoted_database_name = database_name.replace('"', '""')
with admin_engine.connect() as connection:
    exists = connection.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
        {"database_name": database_name},
    ).scalar()
    if not exists:
        connection.exec_driver_sql(f'CREATE DATABASE "{quoted_database_name}"')
admin_engine.dispose()

redis_url = settings.REDIS_URL or (
    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
)
Redis.from_url(redis_url).ping()
PY

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    cd "$FRONTEND_DIR"
    npm ci
fi

rm -f "$BACKEND_LOG" "$FRONTEND_LOG"

setsid bash -lc "cd '$BACKEND_DIR' && uv run task migrate && exec uv run task start" \
    >"$BACKEND_LOG" 2>&1 < /dev/null &
BACKEND_PID=$!

setsid bash -lc "cd '$FRONTEND_DIR' && exec npm run dev" \
    >"$FRONTEND_LOG" 2>&1 < /dev/null &
FRONTEND_PID=$!

cat >"$PID_FILE" <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
BACKEND_LOG=$BACKEND_LOG
FRONTEND_LOG=$FRONTEND_LOG
EOF

if ! wait_for_http "backend" "http://127.0.0.1:8000/docs" "$BACKEND_PID" "$BACKEND_LOG"; then
    "$ROOT_DIR/stop_servers.sh" >/dev/null 2>&1 || true
    exit 1
fi

if ! wait_for_http "frontend" "http://127.0.0.1:3000" "$FRONTEND_PID" "$FRONTEND_LOG"; then
    "$ROOT_DIR/stop_servers.sh" >/dev/null 2>&1 || true
    exit 1
fi

echo "Backend started at http://127.0.0.1:8000/docs"
echo "Frontend started at http://127.0.0.1:3000"
echo "Logs:"
echo "  backend: $BACKEND_LOG"
echo "  frontend: $FRONTEND_LOG"
echo "Stop both services with ./stop_servers.sh"
