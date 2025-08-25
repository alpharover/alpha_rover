#!/usr/bin/env bash
set -euo pipefail

TAG_MODE=${1:-weekly} # weekly|manual
BASE_DIR="$HOME/alpha_ops"
INCLUDE_FILE="$BASE_DIR/data_paths.txt"
EXCLUDE_FILE="$HOME/.alpha-backupignore"
ENV_FILE="$BASE_DIR/restic.env"

if ! command -v restic >/dev/null 2>&1; then
  echo "[error] restic not installed. Install: sudo apt-get install -y restic"
  exit 2
fi
if ! command -v rclone >/dev/null 2>&1; then
  echo "[error] rclone not installed. Install: sudo apt-get install -y rclone"
  exit 2
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "[error] $ENV_FILE not found. Run restic_init.sh first."
  exit 2
fi
set -a; source "$ENV_FILE"; set +a

if [ ! -s "$HOME/.config/rclone/rclone.conf" ]; then
  echo "[error] rclone not configured. Run: $HOME/alpha_ops/setup_rclone.sh"
  exit 2
fi

if [ ! -s "$INCLUDE_FILE" ]; then
  echo "[warn] $INCLUDE_FILE is empty or missing; nothing to back up"
  exit 0
fi

TAGS=("alpha_orin" "$TAG_MODE")
ARGS=(--files-from "$INCLUDE_FILE" --exclude-file "$EXCLUDE_FILE" --tag "${TAGS[*]}")

echo "[restic] repo=$RESTIC_REPOSITORY tag=${TAGS[*]}"
restic -r "$RESTIC_REPOSITORY" version

echo "[restic] starting backup"
restic -r "$RESTIC_REPOSITORY" backup "${ARGS[@]}"

echo "[restic] pruning old snapshots"
restic -r "$RESTIC_REPOSITORY" forget --keep-weekly 8 --keep-monthly 6 --prune

echo "[restic] verify snapshots"
restic -r "$RESTIC_REPOSITORY" snapshots

