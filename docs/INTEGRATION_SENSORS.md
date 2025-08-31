# ALPHA Rover — Sensors Integration Playbook (Adapted) — v2.3+

Audience: Codex agent and developers on Jetson.
Goal: Bring up AIRY LiDAR + OAK cameras, integrate NVBlox + Visual SLAM in containers, wire startup gates/orchestration, and keep the repo reproducible.

This document adapts the ALPHA Codex Agent Playbook to the current repo conventions (configs live under `alpha_configs/` root, no `alpha_configs/sensors/` subdir).

---

## Preconditions
- Jetson (Ubuntu 22.04 + ROS 2 Humble) with Docker + NVIDIA runtime.
- Repo checked out: `~/alpha_rover` (default branch `trunk`).
- Tooling: `python3-vcstool`, `colcon`, `rosdep` installed and initialized.

---

## Third‑party sources (host) via manifests
Create manifest for sensor drivers (LiDAR only in source; depthai via apt):

`alpha_ws/third_party/manifests/sensors.repos`

Then, if/when needed:

```
cd alpha_ws/third_party
vcs import src < manifests/sensors.repos
rosdep install -i -r --from-paths src --rosdistro humble -y
cd ../..  # back to alpha_ws
# Build workspace including both core and third_party sources
colcon build --symlink-install --base-paths src third_party/src
source install/setup.bash
```

Pin exact SHAs after hardware validation.

---

## Sensor configuration (single source of truth)
- LiDAR: `alpha_configs/lidar_airy.yaml` (already present; includes vertical angle table + HTTP endpoints).
- OAK: `alpha_configs/oak_cams.yaml` (added), fill serials if required.

---

## AIRY LiDAR bringup (host)
- Use `alpha_lidar_airy` launch with the C++ backend (default) to validate dims and apply row reorder; publishes canonical topics:
  - `/alpha/lidar/front/points`
  - `/alpha/lidar/rear/points`

Runbooks exist in `alpha_ws/src/alpha_lidar_airy/AGENTS.md` and `alpha_ws/src/alpha_bringup/launch/startup.launch.py`.
Default backend is `cpp`; switch with `backend:=numpy` if needed.

Optional HTTP control (mode service):
- The mode service can toggle AIRY Run/Standby via HTTP. It supports two config paths:
  - Legacy `http.endpoints.{run,standby}` in `alpha_configs/lidar_airy.yaml` (path/method/body/headers).
  - Optional `airy_http` block (disabled by default) with per-device base URLs and payloads.
- You can enable verification and adjust retries via node params:
  - `verify_after_set` (bool, default false): after HTTP set, GET `setting_data.json` to verify `OpM`.
  - `http_retries` (int, default 0) and `http_backoff_ms` (int, default 150).
- The node always falls back to the legacy UI form flow (Parameter_Setting.html) if configured endpoints fail.

Example run (dry-run by default unless you set `http_enabled:=true`):
```
ros2 run alpha_lidar_airy mode_service_node \
  --ros-args \
  -p network_config:=alpha_configs/network.yaml \
  -p http_enabled:=true \
  -p verify_after_set:=true \
  -p http_retries:=1 \
  -p http_backoff_ms:=200

# Standby then Run
ros2 service call /alpha/ui/cmd/lidar_mode alpha_utils/srv/SetLidarMode "{target: 'both', op_mode: 0}"
ros2 service call /alpha/ui/cmd/lidar_mode alpha_utils/srv/SetLidarMode "{target: 'both', op_mode: 1}"
```

---

## LiDAR acceptance test (runtime)
- Package: `alpha_testing`, script: `lidar_accept`.
- Timestamp policy: `/alpha/lidar/*/points` preserves the sensor header stamp.
- Pass criteria (after 10 s warm‑up):
  - Dimensions exactly 96×900
  - Relative skew (`/points` vs `/points_raw`) ≤ 12 ms (P95), ≤ 6 ms (P50)
  - Absolute skew (`now − /points.header.stamp`) reported as informational

Run:
```
cd ~/alpha_rover/alpha_ws
colcon build --symlink-install --packages-select alpha_testing
source install/setup.bash
ros2 run alpha_testing lidar_accept --warmup-s 10 --relative-max-skew-ms 12 --window-s 20
```

---

## OAK cameras bringup (host)
- Preferred: apt-installed `depthai_ros_driver`.
- Launch: `ros2 launch alpha_oak oak_bringup.launch.py` remaps to `/alpha/cam/{front,rear}/image_color` and `/camera_info`.

Basic checks:
```
ros2 topic echo -n 1 /alpha/cam/front/camera_info
ros2 topic hz /alpha/cam/front/image_color -w 30
```

---

## Isaac ROS containers (NVBlox + Visual SLAM)
- Lock file: `deploy/IMAGES.lock`
- Compose: `deploy/compose.mapping.yaml`, `deploy/compose.vslam.yaml`
- Pin script: `scripts/pin_isaac_image.sh`

Start services:
```
cd ~/alpha_rover/deploy
docker compose -f compose.mapping.yaml --env-file IMAGES.lock up -d
# later
docker compose -f compose.vslam.yaml --env-file IMAGES.lock up -d
```

Mapping startup is gated by LiDAR readiness:
- Gate topic: `/alpha/gates/lidar_ready` (std_msgs/Bool), published by `alpha_bringup/lidar_ready_gate` at 2 Hz.
- True only after 10 s warm‑up AND each `/alpha/lidar/{front,rear}/points` rate ≥ 9 Hz over a 3 s window.
- Orchestrator/Sequencer should start NVBlox only when the gate is true.

ROS domains & discovery:
- Standardize domains across environments; see `docs/DEPLOY_ENV.md` for values and service integration.

---

## Definition of Done (sensors scope)
- `sensors.repos` exists with rslidar_sdk/rslidar_msg entries; SHAs pinned post-validation.
- `alpha_lidar_airy` publishes 96×900 clouds; acceptance passes.
- `alpha_oak` publishes camera image + camera_info at configured FPS.
- Isaac compose files run with a real pinned image digest.

---

## Notes & constraints
- Do not vendor third‑party code into `alpha_ws/src`.
- Keep Isaac packages in containers only.
- Canonical topics are stable; update dependents if changed.
- Time skew enforcement: ≤ 20 ms.
- RoboSense driver: do not set an explicit `name` for `rslidar_sdk_node` in launch; rely on per‑instance `namespace` to avoid duplicate nodes/topics in the ROS graph.
 - Reorder node QoS: use SensorData QoS (Best Effort) for both subscriptions and publishers.
 - Reorder node backends: default `backend: numpy` with a future `cpp` backend; fallback `python` remains.
 - Metrics: reorder publishes diagnostics to `/diagnostics` with backend, latency, rate, and pad/truncate counters.
