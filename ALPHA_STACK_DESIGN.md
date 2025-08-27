# Alpha Stack: ROS 2 R&D Architecture Plan

## 1) Purpose
- Build a clean, scalable, and reliable ROS 2 stack for Alpha Orin (Jetson) that fuses dual depth cameras and dual 3D LiDAR with NVBlox, uses Isaac ROS Visual SLAM for pose, and feeds Nav2 for autonomous navigation.
- Optimize for Jetson GPU using NVIDIA Isaac ROS where possible; keep launch flows simple and deterministic (no shell watchers or self-checks).
- Support future expansion (extra sensors, multi-machine with the robot’s RPi4, additional mapping/perception nodes) without rework.

## 2) Guiding Principles
- Simplicity first: prefer ROS 2 Launch orchestration with clear TimerAction delays over fragile shell logic.
- Composable and layered: isolate hardware, VSLAM, mapping, nav, and visualization into separate bringup packages.
- Deterministic startup: no topic watchers; bring up TF and sensors, wait a fixed window, then start downstream consumers.
- Observability: consistent QoS presets, logs, and a small set of obvious topics for sanity checks and visualization.
- Coexistence: this stack stands alongside the existing “oak” stack until phased out.

## 3) Hardware + Network
- Compute: Jetson Orin (alpha_orin) — primary compute (VSLAM, NVBlox, Nav2).
- Base controller: Raspberry Pi 4 (future) — chassis-level device drivers, wheel odometry, motor control; will connect via the same wired switch.
- Sensors: Dual RoboSense AIRY (front=200, rear=201); Dual depth cameras (OAK‑D Pro, OAK‑D SR).
- Network: Wired Ethernet switch for LiDARs, RPi4, and Jetson. Typical private subnet (e.g., 192.168.1.x).

## 4) Frames and Conventions
- Base frames: `base_link` (robot body), `odom`, `map` (VSLAM global frame). Fixed frame for viz: `base_link` or `map` depending on use.
- Cameras: `oak_d_pro` and `oak_d_sr` frames; calibrated extrinsics to `base_link` via URDF/static transforms.
- LiDARs: `airy_front`, `airy_rear` frames; calibrated to `base_link` via URDF/static transforms.
- NVBlox: `global_frame`: `map` (once VSLAM is available), `pose_frame`: `base_link`.

## 5) High-Level Dataflow

```
OAK‑D Pro/SR (stereo)  ──> Isaac ROS Visual SLAM ──> TF (map/odom -> base_link)
                                               │
AIRY 3D LiDAR(s) ──> Repack (pc_reorder)  ──>  NVBlox  ──> TSDF/ESDF/Grids ──> Nav2 costmaps
                                               │
                                               └─> Mesh/markers to Foxglove (via foxglove_bridge)
```

## 6) Packages (new)
1. `alpha_description`
   - URDF/Xacro for chassis + sensor mounts (cameras, LiDARs) with frames.
   - Robot-specific parameters (link inertias optional for sim).

2. `alpha_hw_bringup`
   - Launch: depth cameras (OAK‑D Pro/SR), AIRY LiDAR drivers (`rslidar_sdk`), and `robot_state_publisher`.
   - Static transforms for any frames not in URDF.
   - Optional: repacker/reorderer (`lidar_tools_cpp/pc_reorder`) for AIRY → NVBlox row ordering.

3. `alpha_vslam_bringup`
   - Isaac ROS Visual SLAM (stereo); IMU optional for scale/robustness.
   - Parameters for camera intrinsics, baseline, and stereo config.
   - Publishes `tf` and/or `nav_msgs/Odometry` in `map`/`odom` frames.

4. `alpha_mapping_bringup`
   - NVBlox node with LiDAR + optional depth integration.
   - Parameters for voxel size, integrate rates, queue lengths, and asymmetric LiDAR vertical model.
   - Creates TSDF markers for Foxglove; ESDF/occupancy for Nav2.

5. `alpha_nav_bringup`
   - Nav2 bringup with NVBlox costmap plugins.
   - Lifecycle manager to bring nodes through configure/activate.
   - Local planner configuration and robot footprint.

6. `alpha_viz_bringup`
   - `foxglove_bridge` with QoS overrides for large clouds and TF.
   - Optional recording profiles (rosbag2) for target topic sets.

7. `alpha_stack_bringup`
   - Top-level orchestrator launch that composes the above into ready-to-run modes.

## 7) Launch Architecture

### alpha_stack_bringup/launch/alpha_stack.launch.py
- LaunchArguments
  - `lidar_mode`: `rear|front|both` (default `rear`).
  - `lidar_only`: `true|false` (default `false`).
  - `use_repack`: `true|false` (default `true`) — AIRY row reorder.
  - `angle_csv`: path to AIRY vertical angle CSV.
  - `voxel_size`: NVBlox voxel size (default `0.05`).
  - `lidar_integrate_hz`: NVBlox integrate rate (default `10.0`).
  - `global_frame`: `map|base_link` (default `map`, once VSLAM enabled; use `base_link` until then).

- Groups
  - TF + URDF: `robot_state_publisher`.
  - Sensors: OAK‑D Pro/SR; rslidar drivers for selected LiDAR(s).
  - Repack: `pc_reorder` nodes as needed; fixed topic names `/airy_20x/repacked_points`.
  - TimerAction(10.0): start NVBlox with remaps to repacked topics and the selected frame config.
  - Foxglove: `foxglove_bridge` (direct process or Node if available).

- No topic watchers, no PID locks; rely on ROS launch to create/destroy children. Use fixed 10 s delay before NVBlox to avoid startup races.

### Minimal pseudocode
```
LaunchDescription([
  robot_state_publisher,
  group_sensors(depth_pro, depth_sr, lidar_200/201),
  optional(pc_reorder for selected LiDAR),
  TimerAction(period=10.0, actions=[nvblox_node]),
  foxglove_bridge,
])
```

## 8) Topics, Remaps, QoS
- LiDAR input
  - Raw: `/airy_200/rslidar_points`, `/airy_201/rslidar_points` (organized clouds, BEST_EFFORT, depth 1).
  - Repacked: `/airy_200/repacked_points`, `/airy_201/repacked_points` (organized, row-ordered, BEST_EFFORT).
- NVBlox
  - Subscribes to configured input topic (repacked or raw).
  - Outputs: `/nvblox_node/tsdf_layer_marker` (MarkerArray), `/nvblox_node/static_esdf_pointcloud`, occupancy grids.
  - QoS: input `SENSOR_DATA`; markers best_effort is fine for Foxglove.
- TF
  - `/tf`: BEST_EFFORT
  - `/tf_static`: RELIABLE + TRANSIENT_LOCAL
- Foxglove QoS file
  - PointCloud2 topics set to BEST_EFFORT, depth=1.
  - TF static RELIABLE + TRANSIENT_LOCAL.

## 9) Parameters (initial defaults)
- NVBlox
  - `voxel_size`: 0.05–0.10 (bigger voxel → faster integration/streaming).
  - `integrate_lidar_rate_hz`: 5.0–10.0 (cap CPU/GPU load).
  - `maximum_input_queue_length`: 3 (favor low latency).
  - AIRY: `lidar_width`: 900, `lidar_height`: 96, `use_non_equal_vertical_fov_lidar_params`: true,
    `min_angle_below_zero_elevation_rad`: small negative (e.g., -0.001), `max_angle_above_zero_elevation_rad`: ~1.5707963.
- Repack (`pc_reorder`)
  - `angle_csv`: per-channel vertical angles (ensures correct row ordering for NVBlox).
  - `qos_depth`: 1; `throttle_n`: 1 (optionally 2–3 for load shedding).
- Visual SLAM (future)
  - Stereo intrinsics and baseline; IMU parameters if available.
  - Output TF in `map` frame; provide odometry to downstream modules.

## 10) Multi-Machine (Jetson + RPi4)
- DDS config
  - Choose Cyclone DDS or FastDDS; pin to the wired NIC and disable Wi‑Fi multicast for reliability.
  - Provide example `CYCLONEDDS_URI` or FastDDS XML with `allowlist` interface and reduced discovery traffic.
- Namespaces
  - Jetson publishes main perception stack under `/alpha`.
  - RPi4 base publishes under `/base` (wheel odom, joint states). TF connects frames across namespaces.
- Time sync
  - Optionally use Chrony/NTP on the switch; or rely on ROS 2 time if skew is acceptable.

## 11) Observability + Dev Ergonomics
- Logs
  - Store stdout/stderr under `~/log/alpha_stack/YYYYmmdd-HHMMSS/` via launch log dirs.
- Visualization
  - Foxglove: port 8765; fixed frame `map` (with VSLAM) or `base_link` (pre‑VSLAM).
  - Panels: TSDF markers, ESDF pointcloud, camera RGB/depth, TF tree, diagnostics.
- Recording
  - Profiles: minimal (TF + LiDAR + TSDF markers) and full (add depth images, VSLAM).
- Sanity
  - Lightweight `alphactl sanity` command that lists nodes/processes and checks Foxglove port; no restarts.

## 12) CLI Wrapper (`alphactl`)
- `alphactl map [lidar:=rear|front|both] [voxel_size:=0.07] [rate:=5.0]`
  - Runs `ros2 launch alpha_stack_bringup alpha_stack.launch.py` with provided args.
- `alphactl sensors` — TF + sensors + repack only (no NVBlox/Nav2).
- `alphactl nav` — Full stack with Nav2 (after SLAM is integrated).
- `alphactl stop` — Kill known processes if needed (fallback; normally Ctrl+C launch).
- `alphactl sanity` — Quick status (no mutations).

## 13) Phased Delivery Plan
- Phase 1 (parity with today)
  - Implement `alpha_stack_bringup/alpha_stack.launch.py` to start TF + rear LiDAR + repack, delay 10 s, start NVBlox, start Foxglove.
  - Keep `oak` intact for baseline; validate TSDF stability and performance.

- Phase 2 (add VSLAM)
  - Add `alpha_vslam_bringup` with Isaac ROS Visual SLAM for OAK‑D Pro/SR; publish TF in `map`.
  - Switch NVBlox `global_frame` to `map`; validate drift/loop closures.

- Phase 3 (add Nav2)
  - Add `alpha_nav_bringup` with NVBlox costmap plugin and lifecycle manager.
  - Validate route planning and obstacle avoidance.

## 14) Migration + Coexistence Strategy
- Keep both stacks side-by-side until the Alpha Stack meets or exceeds current behavior.
- `oak` remains for quick A/B tests.
- New development standardizes on Alpha Stack launches and parameters.

## 15) Open Questions + Future Work
- Dual‑LiDAR fusion inside NVBlox: supported patterns or pre‑fusion strategy?
- IMU integration for VSLAM robustness; time synchronization needs.
- Map persistence: saving/loading NVBlox layers and Nav2 costmaps.
- Remote ops: Teleop, UI, and remote bagging.

## 16) Minimal Acceptance Tests (per phase)
- Phase 1
  - TSDF markers visible in Foxglove within 15 s of launch; stable at >1 Hz; no duplicate processes.
  - CPU/GPU utilization within expected limits; no growing queues.
- Phase 2
  - VSLAM TF published; NVBlox map stable during movement; re-localization works.
- Phase 3
  - Nav2 can plan around obstacles; costmap reacts to LiDAR and depth; waypoint following works.

---

Appendix A: Example NVBlox Args (known-good on Jetson)
- `voxel_size:=0.07` `lidar_integrate_hz:=5.0` `maximum_input_queue_length:=3` `layer_streamer_bandwidth_limit_mbps:=10.0`

Appendix B: Example Foxglove QoS
- BEST_EFFORT for PointCloud2; RELIABLE + TRANSIENT_LOCAL for `/tf_static`.

Appendix C: Example AIRY Repack Config
- `angle_csv:=$HOME/alpha_rover/channel_distance_table.csv`
- `input_topic:/airy_201/rslidar_points` → `output_topic:/airy_201/repacked_points`

