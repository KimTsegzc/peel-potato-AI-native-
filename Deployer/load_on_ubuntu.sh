#!/usr/bin/env bash
set -euo pipefail

# Usage (as root):
#   bash Deployer/load_on_ubuntu.sh
# Optional overrides:
#   APP_USER=xiexin APP_DIR=/srv/xiexin-da-agent BRANCH=xiexin-vite-proto bash Deployer/load_on_ubuntu.sh

APP_USER="${APP_USER:-xiexin}"
APP_DIR="${APP_DIR:-/srv/xiexin-da-agent}"
GIT_URL="${GIT_URL:-https://github.com/KimTsegzc/xiexin-da-agent.git}"
BRANCH="${BRANCH:-xiexin-vite-proto}"

install_node20() {
  local current_major="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0)"
  if [[ ! "$current_major" =~ ^[0-9]+$ ]]; then
    current_major=0
  fi

  if [[ "$current_major" -ge 20 ]] && command -v npm >/dev/null 2>&1; then
    return 0
  fi

  echo "[INFO] Preparing Node.js 20 installation"
  dpkg --configure -a || true
  apt-get -f install -y || true

  if dpkg -s nodejs >/dev/null 2>&1 || dpkg -s npm >/dev/null 2>&1 || dpkg -s libnode-dev >/dev/null 2>&1; then
    echo "[INFO] Removing conflicting distro Node packages"
    apt-get remove -y nodejs npm libnode-dev nodejs-doc || true
    apt-get autoremove -y || true
  fi

  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "[ERROR] Please run as root." >&2
  exit 1
fi

echo "[INFO] APP_USER=$APP_USER"
echo "[INFO] APP_DIR=$APP_DIR"
echo "[INFO] GIT_URL=$GIT_URL"
echo "[INFO] BRANCH=$BRANCH"

echo "[STEP] Install base packages"
apt-get -o Acquire::ForceIPv4=true update
apt-get install -y git curl ca-certificates sudo nginx software-properties-common python3 python3-pip

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "[INFO] python3.11 not found, installing via deadsnakes PPA"
  if add-apt-repository -y ppa:deadsnakes/ppa \
      && apt-get -o Acquire::ForceIPv4=true update \
      && apt-get install -y python3.11 python3.11-venv python3.11-dev; then
    echo "[INFO] python3.11 installed"
  else
    echo "[WARN] Unable to install python3.11 from deadsnakes, fallback to system python3"
  fi
fi

install_node20

PYTHON_BIN="$(command -v python3.11 || command -v python3 || true)"
NPM_BIN="$(command -v npm || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[ERROR] python3 not found after install" >&2
  exit 1
fi
if [[ -z "$NPM_BIN" ]]; then
  echo "[ERROR] npm not found after install" >&2
  exit 1
fi

echo "[INFO] Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"
echo "[INFO] Using Node: $(node --version)"
echo "[INFO] Using npm: $(npm --version)"

"$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
  raise SystemExit("Python 3.10+ required")
print("[INFO] Python requirement check passed (>=3.10)")
PY

id -u "$APP_USER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$APP_USER"
mkdir -p /srv

echo "[STEP] Clone/update repository"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone -b "$BRANCH" "$GIT_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch --all
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "[STEP] Preflight + bootstrap"
su - "$APP_USER" -c "cd '$APP_DIR' && bash Deployer/preflight_ubuntu.sh"
su - "$APP_USER" -c "cd '$APP_DIR' && PYTHON_BIN=$PYTHON_BIN bash Deployer/bootstrap_ubuntu.sh"

echo "[STEP] Prepare runtime dir"
mkdir -p "$APP_DIR/.runtime"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/.runtime"

echo "[STEP] Ensure .env"
su - "$APP_USER" -c "cd '$APP_DIR' && [ -f .env ] || cp Deployer/env.production.example .env"
if ! grep -Eq '^(ALIYUN_BAILIAN_API_KEY|DASHSCOPE_API_KEY)=' "$APP_DIR/.env"; then
  echo "[WARN] .env has no API key yet. Edit now: nano $APP_DIR/.env"
fi

echo "[STEP] Install systemd units"
cp "$APP_DIR/Deployer/systemd/xiexin-backend.service" /etc/systemd/system/
cp "$APP_DIR/Deployer/systemd/xiexin-frontend.service" /etc/systemd/system/

# Patch ExecStart with actual host paths
PY_PATH="$(readlink -f "$APP_DIR/.venv311/bin/python" || true)"
NPM_PATH="$(command -v npm || true)"

if [[ -n "$PY_PATH" ]]; then
  sed -i "s|^ExecStart=.*orchestrator.py.*|ExecStart=${PY_PATH} ${APP_DIR}/orchestrator.py --serve --host 0.0.0.0 --port 8765|" /etc/systemd/system/xiexin-backend.service
else
  echo "[ERROR] Python executable not found at $APP_DIR/.venv311/bin/python" >&2
  exit 1
fi

if [[ -n "$NPM_PATH" ]]; then
  sed -i "s|^ExecStart=.*npm.*|ExecStart=${NPM_PATH} run dev -- --host 0.0.0.0 --port 8501|" /etc/systemd/system/xiexin-frontend.service
else
  echo "[ERROR] npm executable not found" >&2
  exit 1
fi

systemctl daemon-reload
systemctl enable --now xiexin-backend xiexin-frontend

echo "[STEP] Configure nginx"
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cp "$APP_DIR/Deployer/nginx/xiexin-da-agent.conf" /etc/nginx/sites-available/xiexin-da-agent
ln -sf /etc/nginx/sites-available/xiexin-da-agent /etc/nginx/sites-enabled/xiexin-da-agent

# Optional: avoid conflicting server_name "_" warning
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "[STEP] Health check"
su - "$APP_USER" -c "cd '$APP_DIR' && bash Deployer/healthcheck.sh"

echo "[DONE] Services status"
systemctl --no-pager --full status xiexin-backend xiexin-frontend nginx || true

echo
echo "[INFO] Access:"
echo "  - http://<public-ip>/"
echo "  - http://<public-ip>:8765/health"
echo "[INFO] Tencent Cloud security group: allow TCP 80 and TCP 8765"
