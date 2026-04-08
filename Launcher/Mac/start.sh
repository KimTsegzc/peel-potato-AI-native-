#!/usr/bin/env bash
# XIEXin DA Agent — Mac / Mac Studio startup script
# Usage:
#   ./Launcher/Mac/start.sh
#   ./Launcher/Mac/start.sh --no-browser
#   ./Launcher/Mac/start.sh --port 8502

set -euo pipefail

# ── paths ────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.runtime"
FRONTEND_DIR="$REPO_ROOT/Front/react-ui"

FRONTEND_PORT=8501
BACKEND_PORT=8766
OPEN_BROWSER=true

# ── arg parse ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)       FRONTEND_PORT="$2"; shift 2 ;;
        --no-browser) OPEN_BROWSER=false; shift ;;
        *) echo "[start] unknown arg: $1"; shift ;;
    esac
done

phase() { echo "[start] $*"; }

mkdir -p "$RUNTIME_DIR"

# ── resolve python (prefer python3.11 → matches .venv311) ────────────────────
VENV_DIR="$REPO_ROOT/.venv311"
if [[ -x "$VENV_DIR/bin/python" ]]; then
    PYTHON="$VENV_DIR/bin/python"
elif command -v python3.11 &>/dev/null; then
    PYTHON="python3.11"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "[start] ERROR: no Python found. Install python3 via Homebrew (brew install python@3.11)." >&2
    exit 1
fi

# ── create venv if missing ────────────────────────────────────────────────────
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    phase "creating virtualenv at $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# ── install / sync Python deps ────────────────────────────────────────────────
phase "syncing Python dependencies"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -e "$REPO_ROOT"

# ── .env check ───────────────────────────────────────────────────────────────
if [[ ! -f "$REPO_ROOT/.env" ]]; then
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────────┐"
    echo "  │  WARNING: no .env file found at project root.               │"
    echo "  │  Create one with at least:                                  │"
    echo "  │    ALIYUN_BAILIAN_API_KEY=<your-key>                        │"
    echo "  │  The backend will start but LLM calls will fail without it. │"
    echo "  └─────────────────────────────────────────────────────────────┘"
    echo ""
fi

# ── kill stale processes on our ports ────────────────────────────────────────
for PORT in $BACKEND_PORT $FRONTEND_PORT; do
    OLD_PID=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
    if [[ -n "$OLD_PID" ]]; then
        phase "killing stale process on port $PORT (pid $OLD_PID)"
        kill -9 $OLD_PID 2>/dev/null || true
        sleep 0.5
    fi
done

# ── npm deps ──────────────────────────────────────────────────────────────────
if ! command -v npm &>/dev/null; then
    echo "[start] ERROR: npm not found. Install Node.js: brew install node" >&2
    exit 1
fi
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    phase "installing npm dependencies"
    (cd "$FRONTEND_DIR" && npm install --silent)
fi

# ── start backend ─────────────────────────────────────────────────────────────
BACKEND_LOG="$RUNTIME_DIR/backend-$BACKEND_PORT.out.log"
BACKEND_ERR="$RUNTIME_DIR/backend-$BACKEND_PORT.err.log"
BACKEND_PID_FILE="$RUNTIME_DIR/backend-$BACKEND_PORT.pid"

phase "starting backend on port $BACKEND_PORT"
cd "$REPO_ROOT"
"$PYTHON" -m apps.api.server --serve --port "$BACKEND_PORT" \
    >"$BACKEND_LOG" 2>"$BACKEND_ERR" &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
phase "backend pid=$BACKEND_PID  log=$BACKEND_LOG"

# ── start frontend ────────────────────────────────────────────────────────────
FRONTEND_LOG="$RUNTIME_DIR/frontend-$FRONTEND_PORT.out.log"
FRONTEND_ERR="$RUNTIME_DIR/frontend-$FRONTEND_PORT.err.log"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend-$FRONTEND_PORT.pid"

phase "starting frontend on port $FRONTEND_PORT"
(cd "$FRONTEND_DIR" && npm run dev -- --port "$FRONTEND_PORT" \
    >"$FRONTEND_LOG" 2>"$FRONTEND_ERR") &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"
phase "frontend pid=$FRONTEND_PID  log=$FRONTEND_LOG"

# ── health-check loop (--noproxy bypasses local http_proxy tunnels) ───────────
phase "waiting for backend health check..."
TIMEOUT=45
ELAPSED=0
until curl -sf --noproxy "127.0.0.1" "http://127.0.0.1:$BACKEND_PORT/health" &>/dev/null; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        echo "[start] ERROR: backend did not become healthy within ${TIMEOUT}s." >&2
        echo "  Check logs: $BACKEND_LOG  /  $BACKEND_ERR" >&2
        exit 1
    fi
done
phase "backend is healthy ✓"

# ── open browser ──────────────────────────────────────────────────────────────
if $OPEN_BROWSER; then
    phase "opening http://localhost:$FRONTEND_PORT"
    open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
fi

echo ""
echo "  XIEXin DA Agent is running."
echo "  Frontend : http://localhost:$FRONTEND_PORT"
echo "  Backend  : http://localhost:$BACKEND_PORT"
echo "  Logs     : $RUNTIME_DIR/"
echo ""
echo "  Stop with:  ./Launcher/Mac/stop.sh"
echo ""

# ── keep terminal alive; Ctrl+C shuts everything down ────────────────────────
phase "press Ctrl+C to stop all services"
trap 'echo; phase "stopping..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT TERM
wait
