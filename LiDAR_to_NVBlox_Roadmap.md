LiDAR → NVBlox Roadmap and Rationale
===================================

Purpose
- Document the current end‑to‑end LiDAR→NVBlox pipeline, decisions, and tuning strategy so another system (e.g., GPT‑5 Pro) can reason about further improvements.

High‑Level Flow
- Hardware (AIRY rear) → rslidar_sdk (ROS 2) → PointCloud2 (organized 96×900) → Row reorder (per‑ring angles) → NVBlox (LiDAR projective integration) → TSDF/ESDF outputs → Foxglove.

Key Interfaces & Topics
- Input cloud: `/airy_201/rslidar_points` (sensor_msgs/PointCloud2)
  - QoS: Best Effort, SensorDataQoS; organized: `height=96`, `width=900`, `frame_id=airy_rear`.
- NVBlox subscriber (remap): `pointcloud ← /airy_201/repacked_points` (or raw)
- Outputs:
  - TSDF marker: `/nvblox_node/tsdf_layer_marker` (visualization_msgs/Marker)
  - TSDF blocks: `/nvblox_node/tsdf_layer` (nvblox_msgs/VoxelBlockLayer)
  - ESDF pointcloud: `/nvblox_node/static_esdf_pointcloud` (sensor_msgs/PointCloud2)

Files & Launch Points
- Driver
  - `ros2_ws/src/rslidar_sdk/CMakeLists.txt` — `POINT_TYPE XYZI` (reduced payload; previously `XYZIRT`).
  - `ros2_ws/src/rslidar_sdk/config/config_airy_201.yaml` — rear sensor, ROS time, ports (MSOP 6700, DIFOP 7789).
- Repack / Row‑reorder
  - Python: `ros2_ws/src/lidar_tools/lidar_tools/pc_repack.py` (optionally reorders rows from angle CSV; also can flatten)
  - C++: `ros2_ws/src/lidar_tools_cpp/src/pc_reorder.cpp` (fast row reorder + throttle_n + QoS depth)
  - Vertical angles CSV: `alpha_rover/channel_distance_table.csv`
- NVBlox
  - Main LiDAR‑only launch: `ros2_ws/src/oak_nvblox_bringup/launch/nvblox_lidar_only.launch.py`
    - Applies AIRY intrinsics at startup:
      - `lidar_width=900`, `lidar_height=96`
      - `use_non_equal_vertical_fov_lidar_params=true`
      - `min_angle_below_zero_elevation_rad=-0.001` (strictly negative per NVBlox check), `max_angle_above_zero_elevation_rad=1.5707963`
      - `lidar_min_valid_range_m=0.10`, `lidar_max_valid_range_m=60.0`
    - Performance launch args:
      - `voxel_size` (applies at node start; default 0.30)
      - `max_queue_len` → `maximum_input_queue_length` (favor low latency)
      - `lidar_integrate_hz` → `integrate_lidar_rate_hz`
      - `streamer_mbps` → `layer_streamer_bandwidth_limit_mbps`
      - `use_repack`, `use_cpp_repack`, `repack_throttle_n`, `repack_angle_csv`
  - Shared defaults: `ros2_ws/src/oak_nvblox_bringup/config/nvblox_from_oak.yaml`
- Orchestration
  - OAK CLI: `ros2_ws/src/oak_multi_bringup/scripts/oak`
  - Main launcher: `ros2_ws/src/oak_multi_bringup/scripts/launch_all.sh` (ensures TF + LiDAR RUN; kills stragglers on stop)
  - TF/URDF: `ros2_ws/src/oak_multi_bringup/urdf/oak_sensors.urdf.xacro`

Design Decisions & Rationale
1) AIRY intrinsics and vertical model
   - AIRY provides 96 channels and ~0.4° azimuth bins → 900 columns. We set `lidar_height=96`, `lidar_width=900`.
   - NVBlox requires a strictly negative `min_angle_below_zero_elevation_rad`; AIRY doesn’t scan below horizon, so we use `-0.001` to pass the check without filtering data.
   - Non‑equal vertical FOV model is enabled to avoid assuming evenly spaced rings.

2) Row reordering by per‑ring angles
   - NVBlox’s projective integrator expects a consistent vertical ordering. We build a permutation of rows using `channel_distance_table.csv` and reorder the range image accordingly.
   - C++ node `pc_reorder` does this without Python overhead; it also supports `throttle_n` to cap input rate.

3) QoS and stamping
   - Input QoS Best Effort (SensorDataQoS) is standard for LiDAR; NVBlox subscribes with SensorDataQoS.
   - Driver uses ROS time for header stamps to avoid TF extrapolation when no PTP/PTP sync.

4) Performance philosophy (Jetson)
   - Fix stutter by prioritizing latency over throughput: small `maximum_input_queue_length` (1–3) and decimation via `throttle_n` and `integrate_lidar_rate_hz`.
   - Reduce work via large `voxel_size` (0.3–0.5) and limited `streamer_mbps` for marker bandwidth.
   - ESDF is expensive; disable during TSDF tuning then re‑enable.

5) Stability measures
   - `oak` ensures LiDAR leaves Standby (0 RPM) before driver start; missing RUN can cause MSOP errors (`WRONGMSOPBLKID`).
   - `oak stop` kills lingering processes including `static_transform_publisher` and Python repack.

Current Pain Points & Hypotheses
- Marker “flicker” is likely due to high update churn and marker clear/readd cycles; reducing streamer bandwidth and frame rate helps.
- Persistent queue drops come from input > processing capacity; lowering ingress rate (`throttle_n`), integration rate, and queue size helps more than raising queue size.
- ESDF underperforms with LiDAR‑only loads on Jetson at small voxels; disable ESDF until TSDF is smooth.

Recommended Experiments (low→high cost)
1) Low‑latency baseline (TSDF‑only): voxel_size 0.5, throttle_n 3, integrate 3 Hz, queue 1.
2) Scale precision: voxel_size 0.35, throttle 2, integrate 5 Hz, queue 1.
3) Re‑enable ESDF at low rate; compare update/delay logs and Foxglove smoothness.
4) Visualize `/nvblox_node/tsdf_layer` or `/nvblox_node/mesh` as alternatives to `tsdf_layer_marker` for smoother visualization.

Operational Recipes
- Start LiDAR‑only mapping (rear):
  - `oak map --lidar-only --lidar rear`
  - Then launch NVBlox with repack: see `nvblox_lidar_only.launch.py` args.
- Confirm organized cloud: `ros2 topic echo -n1 /airy_201/rslidar_points | rg -n "height:|width:"`
- Monitor health: `tail -f ~/alpha_rover/ros2_ws/log_nvblox_map.txt | rg -n "Dropped an item|Rates statistics|Delay statistics" -i`

Open Questions for Further Work
- Can we feed per‑ring vertical angles directly to NVBlox (beyond min/max and non‑equal flag)? If not, is reordering sufficient?
- Would switching to TSDF layer streaming (non‑marker) reduce flicker significantly in Foxglove?
- Can GPU parameters (NVBlox CUDA stream type, block memory) be tuned for Jetson?

Appendix: Relevant Paths
- `alpha_rover/channel_distance_table.csv` — per‑ring vertical angles
- `ros2_ws/src/lidar_tools_cpp/src/pc_reorder.cpp` — fast row reorder
- `ros2_ws/src/oak_nvblox_bringup/launch/nvblox_lidar_only.launch.py` — LiDAR‑only NVBlox
- `ros2_ws/src/rslidar_sdk/config/config_airy_201.yaml` — driver config (rear)
- `ros2_ws/src/oak_multi_bringup/scripts/launch_all.sh` — orchestration & cleanup

