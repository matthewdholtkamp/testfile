#!/bin/zsh
set -euo pipefail

PLIST_PATH="$HOME/Library/LaunchAgents/com.tbiatlas.controlserver.plist"
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"
echo "Removed LaunchAgent: $PLIST_PATH"
