#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv311"
FRONTEND_DIR="$ROOT_DIR/Gateway/Front/react-ui"
PYTHON_BIN="${PYTHON_BIN:-python3}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[ERROR] Missing command: $1" >&2
    exit 1
  }
}

need_cmd "$PYTHON_BIN"
need_cmd curl
need_cmd sudo

echo "[INFO] Root dir: $ROOT_DIR"

echo "[INFO] Installing Ubuntu packages"
sudo apt-get update
sudo apt-get install -y \
  git \
  curl \
  ca-certificates \
  build-essential \
  python3 \
  python3-venv \
  python3-pip \
  nginx

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "[INFO] Installing Node.js 20 via NodeSource"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

echo "[INFO] Python version: $($PYTHON_BIN --version)"
echo "[INFO] Node version: $(node --version)"
echo "[INFO] npm version: $(npm --version)"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[INFO] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools

if [[ -f "$ROOT_DIR/requirements.txt" ]]; then
  echo "[INFO] Installing Python dependencies from requirements.txt"
  pip install -r "$ROOT_DIR/requirements.txt"
fi

if [[ -f "$ROOT_DIR/pyproject.toml" ]]; then
  echo "[INFO] Installing project package in editable mode"
  pip install -e "$ROOT_DIR"
fi

if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
  echo "[INFO] Installing frontend dependencies with npm ci"
  npm --prefix "$FRONTEND_DIR" ci
else
  echo "[INFO] Installing frontend dependencies with npm install"
  npm --prefix "$FRONTEND_DIR" install
fi

echo "[INFO] Building frontend assets"
npm --prefix "$FRONTEND_DIR" run build

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "[WARN] .env not found. Creating from template."
  cp "$ROOT_DIR/Deployer/env.production.example" "$ROOT_DIR/.env"
  echo "[WARN] Edit $ROOT_DIR/.env before starting services."
fi

echo "[INFO] Bootstrap complete"
echo "[INFO] Next steps:"
echo "       1. edit $ROOT_DIR/.env"
echo "       2. copy systemd templates from Deployer/systemd/"
echo "       3. copy nginx config from Deployer/nginx/"
