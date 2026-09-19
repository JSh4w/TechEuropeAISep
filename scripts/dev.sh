#!/usr/bin/env bash
# Start the map prototype: Temporal dev server (if not already running), worker and web UI.
# Works on macOS (bash 3.2) and Linux. Ctrl+C stops everything this script started. Logs: out/logs/.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$PATH:$HOME/.temporalio/bin"

WEB_DIR=sandbox/map_session/web
WEB_PORT="${WEB_PORT:-3000}"
LOGS=out/logs
mkdir -p "$LOGS"

set -m     # give each background job its own process group, so stopping it also stops its children
PIDS=""
stop_all() {
  trap - INT TERM EXIT
  echo
  echo "==> Stopping"
  for pid in $PIDS; do kill -TERM -- "-$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop_all INT TERM EXIT

wait_for() {  # wait_for <name> <seconds> <command...>
  local name=$1 secs=$2; shift 2
  local i=0
  until "$@" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge "$secs" ]; then echo "!! $name didn't start; see $LOGS/" >&2; exit 1; fi
    sleep 1
  done
}

# 1. Temporal (reuse one that's already running)
if temporal operator cluster health >/dev/null 2>&1; then
  echo "==> Temporal already running"
else
  echo "==> Starting Temporal (history persists in out/temporal.db)"
  temporal server start-dev --db-filename out/temporal.db --log-level error >"$LOGS/temporal.log" 2>&1 &
  PIDS="$PIDS $!"
  wait_for Temporal 30 temporal operator cluster health
fi

# 2. Worker
echo "==> Starting worker"
uv run python sandbox/map_session/worker.py >"$LOGS/worker.log" 2>&1 &
PIDS="$PIDS $!"

# 3. Web UI
[ -d "$WEB_DIR/node_modules" ] || (cd "$WEB_DIR" && npm ci --no-audit --no-fund)
echo "==> Starting web UI"
(cd "$WEB_DIR" && exec npx next dev -p "$WEB_PORT") >"$LOGS/web.log" 2>&1 &
PIDS="$PIDS $!"
wait_for "Web UI" 90 curl -sf -o /dev/null "http://localhost:$WEB_PORT"

echo
echo "  App:          http://localhost:$WEB_PORT"
echo "  Temporal UI:  http://localhost:8233"
echo "  Logs:         $LOGS/  (worker + web shown below; Ctrl+C stops everything)"
echo
if [ "$(uname)" = Darwin ]; then open "http://localhost:$WEB_PORT"; fi

tail -n +1 -f "$LOGS/worker.log" "$LOGS/web.log" &
PIDS="$PIDS $!"
wait
