#!/usr/bin/env bash
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()  { echo -e "${GREEN}[OK]${NC}   $*"; }
warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

ssot_dir="$HOME/alpha_rover"
ws_dir="$HOME/alpha_rover/ros2_ws"
ops_dir="$HOME/alpha_rover/alpha_ops"

say "Alpha Rover — Agent Hello"
echo "- SSoT:        $ssot_dir"
echo "- ros2_ws:     $ws_dir (symlink: $HOME/ros2_ws)"
echo "- alpha_ops:   $ops_dir (symlink: $HOME/alpha_ops)"

# ROS distro
if [ -n "${ROS_DISTRO:-}" ]; then
  ok "ROS distro:   $ROS_DISTRO"
else
  warn "ROS not sourced; run: source /opt/ros/humble/setup.bash"
fi

# oak command
if command -v oak >/dev/null 2>&1; then
  oak_bin=$(command -v oak)
  oak_src=$(readlink -f "$oak_bin" || echo "$oak_bin")
  ok "oak command:  $oak_bin -> $oak_src"
else
  warn "oak not on PATH; expected symlink in ~/.local/bin"
fi

# Packages present
if command -v colcon >/dev/null 2>&1; then
  say "Packages (filtered):"
  (cd "$ws_dir" && colcon list | egrep "oak_multi_bringup|oak_nvblox_bringup|rslidar_|sensor_health_monitor" || true)
fi

# rs_driver vendor presence
if [ -f "$ws_dir/src/rslidar_sdk/src/rs_driver/CMakeLists.txt" ]; then
  ok "rs_driver vendored in rslidar_sdk/src/rs_driver"
else
  warn "rs_driver missing; launcher will attempt auto-restore from legacy snapshot"
fi

# Network snapshot
say "Network snapshot (eno1, wl*, foxglove):"
ip -4 addr show dev eno1 2>/dev/null | sed 's/^/  /' || true
ip -4 addr show | egrep -m1 "^\d+: wl|wlan" -A2 | sed 's/^/  /' || true
if command -v ss >/dev/null 2>&1 && ss -lnt | grep -q ":8765"; then
  ok "Foxglove listening on :8765"
else
  warn "Foxglove not detected on :8765"
fi

# JSON summary (machine-readable)
echo
say "JSON summary:"
cat <<JSON
{
  "ssot": "${ssot_dir}",
  "ros2_ws": "${ws_dir}",
  "alpha_ops": "${ops_dir}",
  "ros_distro": "${ROS_DISTRO:-unknown}",
  "oak_bin": "$(command -v oak 2>/dev/null || echo "not-found")",
  "oak_src": "${oak_src:-unknown}",
  "rslidar_vendor": $( [ -f "$ws_dir/src/rslidar_sdk/src/rs_driver/CMakeLists.txt" ] && echo true || echo false ),
  "foxglove_port_8765": $( ss -lnt 2>/dev/null | grep -q ":8765" && echo true || echo false )
}
JSON

say "See AGENT_CONTEXT.md for full details."

