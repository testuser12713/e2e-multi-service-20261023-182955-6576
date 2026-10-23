#!/usr/bin/env bash
# Starts the whole product with one command: installs the dependencies of all three
# services, then runs the API, the worker and the web frontend side by side.
# Ctrl+C stops all of them; if one of them stops, the others are stopped too.
#
# Configuration comes from the environment or from a .env file next to this script
# (copy .env.example). Every value has a working default.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a
  . "$ROOT/.env"
  set +a
fi

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
# A relative path is resolved inside api/ and worker/, so both use <repo>/data/jobs.db.
export DATABASE_PATH="${DATABASE_PATH:-../data/jobs.db}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:${WEB_PORT}}"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:${API_PORT}}"
export WORKER_POLL_INTERVAL="${WORKER_POLL_INTERVAL:-1}"

# --- Python environment (one virtual environment for API and worker) ----------------
PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi
VENV="$ROOT/.venv"
if [ ! -d "$VENV" ]; then
  echo "==> Creating the Python virtual environment in .venv/"
  "$PYTHON_BIN" -m venv "$VENV"
fi
if [ -x "$VENV/bin/python" ]; then
  PY="$VENV/bin/python"
else
  PY="$VENV/Scripts/python.exe"
fi

# --- Install -------------------------------------------------------------------------
for service in api worker; do
  if [ -f "$ROOT/$service/requirements.txt" ]; then
    echo "==> Installing the dependencies of $service/"
    "$PY" -m pip install -q -r "$ROOT/$service/requirements.txt"
  fi
done
if [ -f "$ROOT/web/package.json" ]; then
  echo "==> Installing the dependencies of web/"
  (cd "$ROOT/web" && npm install --no-fund --no-audit)
fi

# --- Start ---------------------------------------------------------------------------
# Job control puts every service into its own process group, so stopping a service
# also stops the processes it started (npm -> vite).
set -m
NAMES=()
PIDS=()

cleanup() {
  trap - EXIT INT TERM
  for pid in ${PIDS[@]+"${PIDS[@]}"}; do
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

start_service() {
  local name="$1" dir="$2"
  shift 2
  if [ ! -d "$ROOT/$dir" ]; then
    echo "==> $dir/ not found, $name is not started" >&2
    return 0
  fi
  echo "==> Starting $name: $* (in $dir/)"
  (cd "$ROOT/$dir" && exec "$@") &
  NAMES+=("$name")
  PIDS+=("$!")
}

start_service api api "$PY" -m uvicorn main:app --port "$API_PORT"
start_service worker worker "$PY" main.py
start_service web web npm run dev -- --port "$WEB_PORT" --strictPort

if [ "${#PIDS[@]}" -eq 0 ]; then
  echo "Nothing to start." >&2
  exit 1
fi

echo
echo "API:      http://127.0.0.1:${API_PORT}  (health: /health)"
echo "Frontend: http://localhost:${WEB_PORT}"
echo "Press Ctrl+C to stop everything."
echo

while true; do
  for i in "${!PIDS[@]}"; do
    if ! kill -0 "${PIDS[$i]}" 2>/dev/null; then
      status=0
      wait "${PIDS[$i]}" || status=$?
      echo "==> ${NAMES[$i]} stopped (exit code $status), stopping the other services." >&2
      exit "$status"
    fi
  done
  sleep 1
done
