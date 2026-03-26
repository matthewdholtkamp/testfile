#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/matthewholtkamp/Documents/testfile"
PLIST_PATH="$HOME/Library/LaunchAgents/com.tbiatlas.controlserver.plist"
APP_SUPPORT_DIR="$HOME/Library/Application Support/TBIAtlas"
LOG_DIR="$HOME/Library/Logs/TBIAtlas"
SERVER_COPY="$APP_SUPPORT_DIR/dashboard_control_server.py"
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents" "$APP_SUPPORT_DIR"

cp "$REPO_DIR/scripts/dashboard_control_server.py" "$SERVER_COPY"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.tbiatlas.controlserver</string>
    <key>ProgramArguments</key>
    <array>
      <string>/usr/bin/python3</string>
      <string>$SERVER_COPY</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/matthewholtkamp</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
      <key>HOME</key>
      <string>/Users/matthewholtkamp</string>
      <key>ATLAS_CONTROL_REPO</key>
      <string>matthewdholtkamp/testfile</string>
      <key>ATLAS_CONTROL_WORKFLOW</key>
      <string>ongoing_literature_cycle.yml</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/launchagent.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/launchagent.err</string>
  </dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/com.tbiatlas.controlserver"

echo "Installed and started LaunchAgent: $PLIST_PATH"
