# Agent Context — Alpha Rover (alpha_orin)

This file gives a fast, minimal orientation for a new coding agent so it can navigate and work productively without rediscovering the project from scratch.

## Canonical Paths
- SSoT root: `~/alpha_rover`
- ROS 2 workspace: `~/alpha_rover/ros2_ws`
  - Convenience symlink: `~/ros2_ws -> ~/alpha_rover/ros2_ws`
- Ops scripts: `~/alpha_rover/alpha_ops`
  - Convenience symlink: `~/alpha_ops -> ~/alpha_rover/alpha_ops`

## Runtime Basics
- OS/ROS: Ubuntu 22.04 + ROS 2 Humble (`source /opt/ros/humble/setup.bash`)
- Build: `cd ~/ros2_ws && colcon build --symlink-install`
- Source: `source ~/ros2_ws/install/setup.bash`

## Quick Commands (OAK system)
- `oak start` — cameras + AIRY LiDARs
- `oak map [--lidar front|rear|both]` — mapping (nvblox) + Foxglove
- `oak foxglove` — sensors + Foxglove
- `oak stop` — stop/cleanup
- `oak lidar [status|standby|run] [--lidar front|rear|both]`

Entrypoints:
- `~/.local/bin/oak -> ~/ros2_ws/src/oak_multi_bringup/scripts/oak`
- Main launcher: `~/ros2_ws/src/oak_multi_bringup/scripts/launch_all.sh`

## Key Packages
- `oak_multi_bringup` — OAK cameras + TF + orchestration
- `oak_nvblox_bringup` — mapping launches
- `rslidar_sdk` — AIRY LiDAR driver (vendored `src/rs_driver` in-tree)
- `rslidar_msg` — LiDAR messages
- `sensor_health_monitor`, `oak_temp_bridge` — optional health/temps

## LiDAR Network
- Jetson NIC (wired): `eno1` at `192.168.1.10/24`
- AIRY front IP: `192.168.1.200` (ports: 6699 MSOP, 7788 DIFOP, 6688 IMU)
- AIRY rear IP: `192.168.1.201` (ports: 6700 MSOP, 7789 DIFOP, 6689 IMU)
- Device power mode via HTTP: see `scripts/oak_lidar.py`

## Foxglove
- WebSocket at `ws://<jetson-ip>:8765` (port guard in launcher avoids conflicts)

## Backups & Ops
- Google Drive remote: `gdrive` (configured)
- Restic repo: `rclone:gdrive:restic-alpha_orin`
- Ops scripts: `~/alpha_ops/*.sh` (see `alpha_ops/README.md`)
- Sudo askpass: configured via `~/.config/alpha_ops/secrets.env` and shell alias

## Known Decisions / Gotchas
- `rslidar_sdk/src/rs_driver` is vendored (no nested submodule) to ensure builds work offline and after workspace moves/clones.
- `launch_all.sh` always builds LiDAR packages and auto-heals `rs_driver` if missing.

## New Session Checklist (Agent)
1) Verify paths and `oak`:
   - `ls -la ~ | egrep 'alpha_ops|ros2_ws'`
   - `type -a oak` (expect it in `~/.local/bin` resolving to `oak_multi_bringup/scripts/oak`)
2) Load ROS 2 env: `source /opt/ros/humble/setup.bash`
3) Build essentials: `cd ~/ros2_ws && colcon build --packages-select oak_multi_bringup rslidar_sdk rslidar_msg --symlink-install`
4) Skim `launch_all.sh` for sequencing and flags.
5) Launch: `oak start` or `oak map`; verify topics with `ros2 topic list`.

## One-Command Overview
Run `~/alpha_ops/agent-hello.sh` to print a concise project overview and key health checks.

