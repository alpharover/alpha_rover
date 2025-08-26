#!/usr/bin/env bash
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
say()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERR]${NC}  $*"; }

fatal=0

say "OAK Preflight Check"

# 1) ROS 2 environment and CLI
if ! command -v ros2 >/dev/null 2>&1; then
  err "ros2 CLI not found in PATH. Source ROS: source /opt/ros/humble/setup.bash"
  exit 2
fi

# shellcheck disable=SC1091
# Temporarily disable nounset; ROS setup uses unset vars
set +u
source /opt/ros/humble/setup.bash >/dev/null 2>&1 || true
set -u
ws="$HOME/ros2_ws"
if [ -f "$ws/install/setup.bash" ]; then
  # shellcheck disable=SC1090
  set +u; source "$ws/install/setup.bash" || true; set -u
fi

ok "ROS distro: ${ROS_DISTRO:-unknown}"

# 2) Required packages present
required_pkgs=(oak_multi_bringup rslidar_sdk rslidar_msg)
[ -d "$ws/src/oak_nvblox_bringup" ] && required_pkgs+=(oak_nvblox_bringup)

missing_pkgs=()
for p in "${required_pkgs[@]}"; do
  if ! ros2 pkg list | grep -qx "$p"; then missing_pkgs+=("$p"); fi
done
if [ ${#missing_pkgs[@]} -gt 0 ]; then
  err "Missing packages in current environment: ${missing_pkgs[*]}"
  say "Run: cd ~/ros2_ws && colcon build --packages-select ${required_pkgs[*]} --symlink-install && source ~/ros2_ws/install/setup.bash"
  fatal=1
else
  ok "Packages present: ${required_pkgs[*]}"
fi

# 3) rslidar vendor present
if [ -f "$ws/src/rslidar_sdk/src/rs_driver/CMakeLists.txt" ]; then
  ok "rslidar vendor present (rslidar_sdk/src/rs_driver)"
else
  err "rslidar vendor missing: $ws/src/rslidar_sdk/src/rs_driver"
  say "The launcher will attempt auto-restore from legacy snapshot."
  fatal=1
fi

# 4) Network sanity (eno1 + LiDARs)
if ip -4 addr show dev eno1 >/dev/null 2>&1; then
  ip -4 addr show dev eno1 | sed 's/^/  /'
else
  warn "Interface eno1 not found (expected wired NIC for LiDARs)"
fi

lidar_script="$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py"
if [ -x "$lidar_script" ]; then
  if ! "$lidar_script" status --lidar both >/dev/null 2>&1; then
    warn "LiDAR status unreachable; ensure network to 192.168.1.200/201"
  else
    ok "LiDAR web status reachable"
  fi
else
  warn "oak_lidar.py not executable: $lidar_script"
fi

# 5) Foxglove port
if ss -lnt 2>/dev/null | grep -q ":8765"; then
  ok "Foxglove already listening on :8765"
else
  say "Foxglove port 8765 free"
fi

# 6) If anything fatal, exit nonzero
if [ $fatal -ne 0 ]; then
  exit 1
fi

ok "Preflight passed"
exit 0
