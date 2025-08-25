#!/usr/bin/env bash
set -euo pipefail

UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNIT_DIR"

systemctl --user daemon-reload || true

echo "[enable] Enabling weekly timer alpha-backup.timer"
systemctl --user enable --now alpha-backup.timer

echo "[linger] Ensuring user services run when logged out (optional)"
if sudo -n true 2>/dev/null; then
  sudo -n loginctl enable-linger "$USER" || true
else
  echo "[info] No passwordless sudo; if desired run: sudo loginctl enable-linger $USER"
fi

echo "[status] systemctl --user list-timers | grep alpha-backup"
systemctl --user list-timers --all | grep alpha-backup || true

