#!/usr/bin/env bash

set -euo pipefail

PID_FILE="/tmp/e-commerce-start_servers.pids"

terminate_process_group() {
    local pid="$1"

    if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
        return
    fi
    if ! kill -0 "$pid" >/dev/null 2>&1; then
        return
    fi

    kill -TERM "-$pid" >/dev/null 2>&1 || kill -TERM "$pid" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "$pid" >/dev/null 2>&1; then
        kill -KILL "-$pid" >/dev/null 2>&1 || kill -KILL "$pid" >/dev/null 2>&1 || true
    fi
}

if command -v tmux >/dev/null 2>&1; then
    tmux kill-session -t fastapi_template >/dev/null 2>&1 || true
fi

if [ ! -f "$PID_FILE" ]; then
    exit 0
fi

while IFS='=' read -r key value; do
    case "$key" in
        BACKEND_PID|FRONTEND_PID)
            terminate_process_group "$value"
            ;;
    esac
done < "$PID_FILE"

rm -f "$PID_FILE"
