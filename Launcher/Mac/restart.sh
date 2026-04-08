#!/usr/bin/env bash
# XIEXin DA Agent — Mac / Mac Studio restart script
# Usage:
#   ./Launcher/Mac/restart.sh
#   ./Launcher/Mac/restart.sh --port 8502
#   ./Launcher/Mac/restart.sh --no-browser

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

phase() { echo "[restart] $*"; }

phase "stopping..."
bash "$SCRIPT_DIR/stop.sh"

phase "waiting 400ms"
sleep 0.4

phase "starting..."
exec bash "$SCRIPT_DIR/start.sh" "$@"
