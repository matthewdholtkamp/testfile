#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/matthewholtkamp/Documents/testfile"
PID_DIR="$REPO_DIR/tmp/control_server"
PID_FILE="$PID_DIR/server.pid"
LOG_FILE="$PID_DIR/server.log"

mkdir -p "$PID_DIR"

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    echo "Dashboard control server already running on PID $PID"
    exit 0
  else
    rm -f "$PID_FILE"
  fi
fi

cd "$REPO_DIR"
nohup python3 scripts/dashboard_control_server.py >>"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Started dashboard control server on PID $(cat "$PID_FILE")"
