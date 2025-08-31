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
```

Pin exact SHAs after hardware validation.

---

## Sensor configuration (single source of truth)
- LiDAR: `alpha_configs/lidar_airy.yaml` (already present; includes vertical angle table + HTTP endpoints).
- OAK: `alpha_configs/oak_cams.yaml` (added), fill serials if required.

---

## AIRY LiDAR bringup (host)
- Use `alpha_lidar_airy/reorder_node` to validate dims and apply row reorder; publishes canonical topics:
  - `/alpha/lidar/front/points`
  - `/alpha/lidar/rear/points`

Runbooks exist in `alpha_ws/src/alpha_lidar_airy/AGENTS.md` and `alpha_ws/src/alpha_bringup/launch/startup.launch.py`.

---

## LiDAR acceptance test (runtime)
- Package: `alpha_testing`, script: `lidar_accept`.
- Pass criteria: front/rear publish 96×900 with header skew ≤ 20 ms.

Run:
```
cd ~/alpha_rover/alpha_ws
colcon build --symlink-install --packages-select alpha_testing
source install/setup.bash
ros2 run alpha_testing lidar_accept
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

