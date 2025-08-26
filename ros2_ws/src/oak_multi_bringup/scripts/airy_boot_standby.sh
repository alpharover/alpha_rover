#!/bin/bash
# Ensure RoboSense AIRY units enter Standby on boot
SCRIPT="$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py"
RETRIES=20
SLEEP=3

echo "[airy-boot-standby] starting... $(date)"
for i in $(seq 1 $RETRIES); do
  if [ -x "$SCRIPT" ]; then
    "$SCRIPT" standby && echo "[airy-boot-standby] set standby (attempt $i)" && exit 0
  fi
  echo "[airy-boot-standby] retry $i/$RETRIES..."
  sleep $SLEEP
done
echo "[airy-boot-standby] failed to set standby after $RETRIES attempts"
exit 1
