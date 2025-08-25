#!/usr/bin/env bash
set -euo pipefail

FOLDER_ID="1MCWsR8Q_VGlEIbnwiIHEdUdb9JNGnUkr" # Google Drive folder: alpha_rover

if ! command -v rclone >/dev/null 2>&1; then
  echo "[error] rclone not installed. Install: sudo apt-get install -y rclone"
  exit 2
fi

mkdir -p "$HOME/.config/rclone"

# Create a remote skeleton (no token yet). Reconnect triggers OAuth.
if ! rclone listremotes | grep -q '^gdrive:'; then
  rclone config create gdrive drive scope=drive root_folder_id="$FOLDER_ID" config_is_local=true --non-interactive || true
fi

echo "[info] Starting OAuth in your browser (or copy the URL)."
echo "      If headless, the command prints a link to open elsewhere."
rclone config reconnect gdrive: --auto-confirm

echo "[test] Listing the Drive root for the configured folder ID"
rclone lsd gdrive: || { echo "[error] rclone remote test failed"; exit 1; }

echo "[ok] rclone is configured for Google Drive folder $FOLDER_ID"

