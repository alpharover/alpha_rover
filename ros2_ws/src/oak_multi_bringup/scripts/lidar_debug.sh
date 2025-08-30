#!/usr/bin/env bash
set -euo pipefail

echo "[+] LiDAR debug: rear sensor (/airy_201/rslidar_points)"

echo "\n-- Topic info (verbose) --"
ros2 topic info -v /airy_201/rslidar_points || true

echo "\n-- Sample message header + dims --"
ros2 topic echo --once /airy_201/rslidar_points | sed -n '1,40p' || true

echo "\n-- Frequency (5s window) --"
timeout 6 ros2 topic hz /airy_201/rslidar_points || true

echo "\n-- TF check (base_link -> airy_rear) --"
timeout 3 ros2 run tf2_ros tf2_echo base_link airy_rear || true

echo "\n-- nvblox params (use_lidar, lidar dims) --"
ros2 param get /nvblox_node use_lidar || true
ros2 param get /nvblox_node lidar_width || true
ros2 param get /nvblox_node lidar_height || true
ros2 param get /nvblox_node use_non_equal_vertical_fov_lidar_params || true

echo "\n-- Subscribers to rear LiDAR --"
ros2 topic info -v /airy_201/rslidar_points | sed -n '/Subscribers:/,$p' || true

echo "\n-- Done."

