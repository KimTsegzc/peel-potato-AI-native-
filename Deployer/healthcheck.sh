#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:8501}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8765/health}"
BACKEND_CONFIG_URL="${BACKEND_CONFIG_URL:-http://127.0.0.1:8765/api/frontend-config}"

check_url() {
  local label="$1"
  local url="$2"
  echo "[INFO] Checking $label -> $url"
  curl -fsS "$url" >/tmp/xiexin_healthcheck.$$ || {
    echo "[FAIL] $label failed: $url"
    rm -f /tmp/xiexin_healthcheck.$$
    exit 1
  }
  echo "[PASS] $label OK"
  rm -f /tmp/xiexin_healthcheck.$$
}

check_url "frontend" "$FRONTEND_URL"
check_url "backend health" "$BACKEND_HEALTH_URL"
check_url "frontend config" "$BACKEND_CONFIG_URL"

echo "[PASS] All health checks passed"
