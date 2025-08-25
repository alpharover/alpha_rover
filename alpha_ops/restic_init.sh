#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/alpha_ops"
ENV_FILE="$BASE_DIR/restic.env"

if ! command -v restic >/dev/null 2>&1; then
  echo "[error] restic not installed. Install: sudo apt-get install -y restic"
  exit 2
fi
if ! command -v rclone >/dev/null 2>&1; then
  echo "[error] rclone not installed. Install: sudo apt-get install -y rclone"
  exit 2
fi

mkdir -p "$BASE_DIR"
if [ ! -f "$ENV_FILE" ]; then
cat > "$ENV_FILE" <<'ENV'
# Restic + rclone environment
export RESTIC_REPOSITORY="rclone:gdrive:restic-alpha_orin"
export RESTIC_PASSWORD="9909"
export RCLONE_CONFIG="$HOME/.config/rclone/rclone.conf"
ENV
  chmod 600 "$ENV_FILE"
  echo "[info] Wrote $ENV_FILE (contains your backup passphrase). Keep it safe."
fi

set -a; source "$ENV_FILE"; set +a

echo "[check] rclone remote"
if ! rclone lsd gdrive: >/dev/null 2>&1; then
  echo "[error] rclone remote gdrive: not working. Run setup_rclone.sh first."
  exit 2
fi

echo "[check] restic repo: $RESTIC_REPOSITORY"
if restic -r "$RESTIC_REPOSITORY" snapshots >/dev/null 2>&1; then
  echo "[ok] restic repository already initialized"
else
  echo "[init] initializing restic repository"
  restic -r "$RESTIC_REPOSITORY" init
  echo "[ok] initialized"
fi

