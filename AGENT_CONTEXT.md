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
- `oak start` — cameras + AIRY LiDARs (no NVBlox)
- `oak map [--lidar front|rear|both]` — cleanup → TF/sensors → LiDAR RUN → wait 10s → NVBlox → Foxglove
- `oak map --lidar-only --lidar rear` — LiDAR-only mapping (recommended for testing)
- `oak foxglove` — sensors + Foxglove
- `oak stop` — stop/cleanup (kills known processes, clears stale PIDs)
- `oak sanity` — quick status of nodes/processes and Foxglove port (no mutations)

Entrypoints:
- `~/.local/bin/oak -> ~/ros2_ws/src/oak_multi_bringup/scripts/oak`
- Main launcher: `~/ros2_ws/src/oak_multi_bringup/scripts/launch_all.sh`

NVblox defaults can be tuned via `NVBLOX_ARGS` env var, e.g.:
```
export NVBLOX_ARGS="voxel_size:=0.07 lidar_integrate_hz:=5.0 maximum_input_queue_length:=3 layer_streamer_bandwidth_limit_mbps:=10.0"
```
Then run `oak stop && oak map --lidar-only --lidar rear`.

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
- WebSocket at `ws://<jetson-ip>:8765` (bridge runs via direct `ros2 run`)
- Fixed frame: `base_link` (pre‑VSLAM) or `map` (post‑VSLAM)
- Important topics: `/nvblox_node/tsdf_layer_marker`, `/nvblox_node/static_esdf_pointcloud`

## Backups & Ops
- Google Drive remote: `gdrive` (configured)
- Restic repo: `rclone:gdrive:restic-alpha_orin`
- Ops scripts: `~/alpha_ops/*.sh` (see `alpha_ops/README.md`)
- Sudo askpass: configured via `~/.config/alpha_ops/secrets.env` and shell alias
 - On-demand backup (code + data): `~/alpha_ops/backup-now.sh`
 - Manual Git push (code only): `cd ~/alpha_rover && git push origin main`

## Known Decisions / Gotchas
- `rslidar_sdk/src/rs_driver` is vendored (no nested submodule) to ensure builds work offline and after workspace moves/clones.
- `launch_all.sh` always builds LiDAR packages and auto-heals `rs_driver` if missing.
- Simplified `oak map` path avoids topic watchers and duplicate guards; relies on fixed 10s LiDAR stabilization delay before NVBlox.
- NVBlox logs are captured at `~/ros2_ws/log_nvblox_map.txt` for quick triage.

## New Session Checklist (Agent)
1) Verify paths and `oak`:
   - `ls -la ~ | egrep 'alpha_ops|ros2_ws'`
   - `type -a oak` (expect it in `~/.local/bin` resolving to `oak_multi_bringup/scripts/oak`)
2) Load ROS 2 env: `source /opt/ros/humble/setup.bash`
3) Build essentials: `cd ~/ros2_ws && colcon build --packages-select oak_multi_bringup rslidar_sdk rslidar_msg --symlink-install`
4) Skim `launch_all.sh` for sequencing and flags.
5) Launch: `oak start` or `oak map`; verify topics with `ros2 topic list`.
6) For mapping validation: open Foxglove and add `/nvblox_node/tsdf_layer_marker`.
7) If mapping looks sparse: adjust `NVBLOX_ARGS`, then `oak stop && oak map --lidar-only --lidar rear`.

## One-Command Overview
Run `~/alpha_ops/agent-hello.sh` to print a concise project overview and key health checks.

## Roadmap Reference
- For future architecture (VSLAM → NVBlox → Nav2), see `ALPHA_STACK_DESIGN.md`.
