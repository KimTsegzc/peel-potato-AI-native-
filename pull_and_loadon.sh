#!/usr/bin/env bash
set -euo pipefail

# One-shot server deploy helper:
# 1) git pull target branch
# 2) run Deployer/load_on_ubuntu.sh
#
# Usage examples:
#   bash pull_and_loadon.sh
#   BRANCH=main bash pull_and_loadon.sh
#   FORCE_BOOTSTRAP=1 bash pull_and_loadon.sh

APP_USER="${APP_USER:-xiexin}"
APP_DIR="${APP_DIR:-/srv/xiexin-da-agent}"
BRANCH="${BRANCH:-xiexin-vite-proto}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
FORCE_BOOTSTRAP="${FORCE_BOOTSTRAP:-0}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo -E \
    APP_USER="$APP_USER" \
    APP_DIR="$APP_DIR" \
    BRANCH="$BRANCH" \
    GIT_REMOTE="$GIT_REMOTE" \
    FORCE_BOOTSTRAP="$FORCE_BOOTSTRAP" \
    bash "$0" "$@"
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "[ERROR] Not a git repo: $APP_DIR"
  echo "[HINT] Clone repository first, then rerun."
  exit 1
fi

cd "$APP_DIR"

echo "[STEP] Pull latest code"
git fetch "$GIT_REMOTE"
git checkout "$BRANCH"
git pull --ff-only "$GIT_REMOTE" "$BRANCH"

echo "[STEP] Run load_on_ubuntu"
APP_USER="$APP_USER" \
APP_DIR="$APP_DIR" \
BRANCH="$BRANCH" \
FORCE_BOOTSTRAP="$FORCE_BOOTSTRAP" \
bash Deployer/load_on_ubuntu.sh

echo "[DONE] Deploy finished"
echo "[INFO] Branch: $BRANCH"
echo "[INFO] Commit: $(git rev-parse --short HEAD)"
