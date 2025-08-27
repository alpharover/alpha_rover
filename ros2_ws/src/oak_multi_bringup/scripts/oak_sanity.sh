#!/bin/bash

# Lightweight sanity checker for OAK multi-sensor stack.
# Verifies single instances of key nodes/processes and Foxglove port state.

set -e

if [ -z "$ROS_DISTRO" ]; then
  source /opt/ros/humble/setup.bash
fi

source "$HOME/ros2_ws/install/setup.bash" 2>/dev/null || true

# Reset the ROS 2 daemon to avoid stale graph
ros2 daemon stop >/dev/null 2>&1 || true
sleep 0.5
ros2 daemon start >/dev/null 2>&1 || true
sleep 0.5

dup=0

echo "[sanity] Checking ROS 2 nodes..."
nodes=$(ros2 node list 2>/dev/null || true)
echo "$nodes"

check_node_once() {
  local name="$1"
  local count
  count=$(echo "$nodes" | grep -c "^$name$" || true)
  if [ "$count" -gt 1 ]; then
    # Cross-check exact process count for the corresponding binary
    local proc=""
    case "$name" in
      "/foxglove_bridge") proc="foxglove_bridge" ;;
      "/nvblox_node") proc="nvblox_node" ;;
      "/pc_reorder") proc="pc_reorder" ;;
      "/rslidar_sdk_node") proc="rslidar_sdk_node" ;;
    esac
    local pcnt=0
    if [ -n "$proc" ]; then
      pcnt=$(pgrep -xc "$proc" 2>/dev/null || echo 0)
    fi
    if [ "$pcnt" -gt 1 ]; then
      echo "[sanity][warn] Duplicate node+proc: $name x$count, proc=$proc x$pcnt"
      dup=$((dup+1))
    else
      echo "[sanity][info] Graph shows $count '$name' but $pcnt '$proc' processes; likely stale entries"
    fi
  fi
}

check_node_once "/robot_state_publisher"
check_node_once "/nvblox_node"
check_node_once "/foxglove_bridge"
check_node_once "/pc_reorder"

echo "[sanity] Checking processes (exact matches)..."
pgrep -xa nvblox_node || true
pgrep -xa foxglove_bridge || true
pgrep -xa rslidar_sdk_node || true
pgrep -xa pc_reorder || true
pgrep -fa "python3 .*lidar_tools.pc_repack" || true

echo "[sanity] Checking Foxglove port 8765..."
ss -lnt 2>/dev/null | awk '/LISTEN/ && /:8765/ {print}' || true

if [ "$dup" -gt 0 ]; then
  echo "[sanity] Detected $dup duplicate node groups"
  exit 2
fi

echo "[sanity] OK"
exit 0
