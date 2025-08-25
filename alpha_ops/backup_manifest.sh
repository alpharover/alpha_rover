#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="$HOME/alpha_ops/manifests/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

echo "[manifest] writing to $OUT_DIR"

{
  echo "===== uname ====="; uname -a; echo
  echo "===== os-release ====="; cat /etc/os-release 2>/dev/null || true; echo
  echo "===== L4T/JetPack ====="; cat /etc/nv_tegra_release 2>/dev/null || dpkg -l | grep -i nvidia-l4t || true; echo
} > "$OUT_DIR/system.txt"

command -v apt >/dev/null 2>&1 && apt list --installed 2>/dev/null | sed -n '1,5000p' > "$OUT_DIR/apt-packages.txt" || true

python3 - <<'PY' > "$OUT_DIR/pip-freeze.txt" || true
import sys, subprocess
def freeze(p):
    try:
        out = subprocess.check_output([p, '-m', 'pip', 'freeze'], stderr=subprocess.DEVNULL, text=True)
        print(f"# {p}")
        print(out)
    except Exception:
        pass
for p in ['python3']:
    freeze(p)
PY

if command -v docker >/dev/null 2>&1; then
  docker images > "$OUT_DIR/docker-images.txt" || true
  docker ps -a > "$OUT_DIR/docker-containers.txt" || true
fi

if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi -q > "$OUT_DIR/nvidia-smi.txt" || true; fi

echo "[manifest] complete"

