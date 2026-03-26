#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/matthewholtkamp/Documents/testfile"
PID_FILE="$REPO_DIR/tmp/control_server/server.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Dashboard control server is not running"
  exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "Stopped dashboard control server PID $PID"
else
  echo "No running process found for PID $PID"
fi
rm -f "$PID_FILE"
