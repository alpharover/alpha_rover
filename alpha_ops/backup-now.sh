#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/alpha_ops"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/backup-$STAMP.log"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "[backup-now] $(date -Iseconds) starting"

# Basic resource guard: skip if system is under heavy load
CPUS=$(getconf _NPROCESSORS_ONLN || echo 4)
LOAD1=$(awk '{print $1}' /proc/loadavg)
MAX_LOAD=$(awk -v c="$CPUS" 'BEGIN { printf "%.2f", c * 0.80 }')
echo "[guard] load1=$LOAD1 max=$MAX_LOAD cpus=$CPUS"
awk -v l="$LOAD1" -v m="$MAX_LOAD" 'BEGIN { exit (l>m)?1:0 }' || { echo "[guard] High load; deferring backup"; exit 0; }

"$BASE_DIR/backup_repos.sh" || echo "[warn] repo push step had issues"
"$BASE_DIR/backup_manifest.sh" || echo "[warn] manifest step had issues"
"$BASE_DIR/backup_data.sh" manual || { echo "[error] data backup failed"; exit 1; }

echo "[backup-now] $(date -Iseconds) complete"

