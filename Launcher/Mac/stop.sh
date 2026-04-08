#!/usr/bin/env bash
# XIEXin DA Agent — Mac / Mac Studio stop script
# Usage:  ./Launcher/Mac/stop.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.runtime"
FRONTEND_PORT=8501
BACKEND_PORT=8766

phase() { echo "[stop] $*"; }

stop_by_pid_file() {
    local pid_file="$1"
    local label="$2"
    if [[ -f "$pid_file" ]]; then
        PID=$(cat "$pid_file")
        if kill -0 "$PID" 2>/dev/null; then
            phase "stopping $label (pid $PID)"
            kill "$PID" 2>/dev/null || true
            sleep 0.5
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    fi
}

stop_by_port() {
    local port="$1"
    local label="$2"
    OLD_PID=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [[ -n "$OLD_PID" ]]; then
        phase "killing $label on port $port (pid $OLD_PID)"
        kill -9 $OLD_PID 2>/dev/null || true
    fi
}

stop_by_pid_file "$RUNTIME_DIR/backend-$BACKEND_PORT.pid"   "backend"
stop_by_pid_file "$RUNTIME_DIR/frontend-$FRONTEND_PORT.pid" "frontend"

# Fallback: kill anything still holding the ports
stop_by_port "$BACKEND_PORT"  "backend"
stop_by_port "$FRONTEND_PORT" "frontend"

phase "done."
