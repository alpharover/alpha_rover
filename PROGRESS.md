LiDAR → NVBlox Integration: Current Progress (2025‑08‑26)
=========================================================

Summary
- Goal: LiDAR‑only integration of rear RoboSense AIRY (201) into NVBlox with visible TSDF/ESDF; isolate from depth cameras.
- Status: TSDF markers now visible via repacked/row‑reordered LiDAR input. Performance is improving but still choppy due to integration/streaming load; significant queue drops are observed. ESDF remains sparse at low rate under LiDAR‑only loads.

What’s working
- Driver publishes organized PointCloud2: `height=96`, `width=900`, `frame_id=airy_rear`, QoS Best Effort.
- TF correct: `base_link ↔ airy_rear` from URDF.
- NVBlox accepts LiDAR input with correct AIRY intrinsics and asymmetric vertical model.
- TSDF visible: `/nvblox_node/tsdf_layer_marker` shows voxels in Foxglove when using repacked input.

Key changes this session
- LiDAR‑only launch improvements: `ros2_ws/src/oak_nvblox_bringup/launch/nvblox_lidar_only.launch.py`
  - Node name unified to `/nvblox_node`.
  - Correct AIRY intrinsics at startup: `lidar_width=900`, `lidar_height=96`, `use_non_equal_vertical_fov_lidar_params=true`, `min_angle_below_zero_elevation_rad=-0.001`, `max_angle_above_zero_elevation_rad=1.5707963`.
  - Ranges per spec: `lidar_min_valid_range_m=0.10`, `lidar_max_valid_range_m=60.0`.
  - Launch args to tune performance at node start: `voxel_size`, `max_queue_len`, `lidar_integrate_hz`, `streamer_mbps`.
- Fast C++ repack added: `ros2_ws/src/lidar_tools_cpp` (`pc_reorder`)
  - Reorders the 96 rows using `alpha_rover/channel_distance_table.csv` (per‑ring vertical angles) to match NVBlox’s vertical model.
  - Supports low‑latency mode: QoS depth=1 and `throttle_n` (forward every Nth frame).
- Python repack retained for reference: `ros2_ws/src/lidar_tools/lidar_tools/pc_repack.py` (now supports optional angle CSV too), but C++ path is default when repack is enabled.
- Driver point type reduced to XYZI for interoperability and lower bandwidth: `ros2_ws/src/rslidar_sdk/CMakeLists.txt` (`POINT_TYPE XYZI`).
- oak stop robustness: kills lingering `static_transform_publisher` so sessions end cleanly: `ros2_ws/src/oak_multi_bringup/scripts/launch_all.sh`.

Repro: LiDAR‑only with low‑latency preset
1) Stop + build
   - `oak stop`
   - `cd ~/alpha_rover/ros2_ws && colcon build --packages-select lidar_tools_cpp oak_nvblox_bringup --symlink-install && source install/setup.bash`
2) Start stack
   - `oak map --lidar-only --lidar rear`  (ensures AIRY leaves Standby and spins at 10 Hz)
3) Launch NVBlox with C++ repack and big voxels
   - `ros2 launch oak_nvblox_bringup nvblox_lidar_only.launch.py \
      voxel_size:=0.35 max_queue_len:=3 lidar_integrate_hz:=5.0 streamer_mbps:=3.0 \
      use_repack:=true use_cpp_repack:=true repack_throttle_n:=2 \
      repack_out_frame:=airy_rear repack_angle_csv:=/home/alpha_orin/alpha_rover/channel_distance_table.csv \
      lidar_points_topic:=/airy_201/rslidar_points`
4) Visualize
   - Foxglove fixed frame: `base_link`
   - Add `/nvblox_node/tsdf_layer_marker` (and optional `/nvblox_node/static_esdf_pointcloud`).

Observations and logs
- NVBlox logs show `ros/lidar ~6–7 Hz`, many pointcloud drops under heavy load. After applying throttle + queue size 1–3 and larger voxels, drops reduce and TSDF persistence is improved.
- TSDF marker refresh can still appear flickery at high publish rates; `streamer_mbps` and downsampling help.
- Early driver warnings (`ERRCODE_WRONGMSOPBLKID`) correlate with Airy at 0 RPM; resolved by ensuring RUN/high‑performance mode.

Tuning knobs (at launch; live changes won’t resize layers)
- `voxel_size` (m): 0.3–0.5 recommended for smooth debug on Jetson.
- `max_queue_len`: 1–3 to prefer newest frames and avoid catch‑up loops.
- `lidar_integrate_hz`: 3–6 to cap NVBlox work.
- `streamer_mbps`: 1–5 to reduce marker churn in Foxglove.
- `repack_throttle_n`: 2–3 to forward ~5–3.3 Hz into NVBlox.

Open issues
- ESDF: remains sparse/slow under LiDAR‑only loads; consider disabling while tuning TSDF.
- Marker flicker: inherent to visualization of large updates; we can switch to mesh or TSDF layer visualization (non‑marker) if needed.
- Queue pressure: still present in some configs; continue balancing throttle/rates/voxel size.

Next session plan
1) Add `tsdf_only` launch switch to disable ESDF/mesh while tuning.
2) Benchmark variants (5 min each):
   - A: voxel 0.5, throttle 3, integrate 3 Hz, queue 1
   - B: voxel 0.35, throttle 2, integrate 5 Hz, queue 1
   - C: voxel 0.3, throttle 2, integrate 5 Hz, queue 2
   Collect: drops/sec, marker rate, CPU in jtop.
3) If stable: re‑enable ESDF at low rate; test `global_frame=map` with static TF.
4) Validate rear/front swap and full `oak map` with cameras re‑enabled.

Key files (added/modified)
- Launches & config
  - `ros2_ws/src/oak_nvblox_bringup/launch/nvblox_lidar_only.launch.py`
  - `ros2_ws/src/oak_nvblox_bringup/config/nvblox_from_oak.yaml`
- Repackers
  - Python: `ros2_ws/src/lidar_tools/lidar_tools/pc_repack.py`
  - C++: `ros2_ws/src/lidar_tools_cpp/src/pc_reorder.cpp` (package `lidar_tools_cpp`)
- Driver
  - `ros2_ws/src/rslidar_sdk/CMakeLists.txt` (POINT_TYPE XYZI)
  - `ros2_ws/src/rslidar_sdk/config/config_airy_201.yaml` (rear ports, ROS time)
- OAK scripts
  - `ros2_ws/src/oak_multi_bringup/scripts/launch_all.sh` (cleanup enhancements)
  - `ros2_ws/src/oak_multi_bringup/urdf/oak_sensors.urdf.xacro` (frames)

Quick diagnostics
- Topic rates: `ros2 topic hz /airy_201/rslidar_points`, `/nvblox_node/tsdf_layer_marker`
- Drops: `tail -f ~/alpha_rover/ros2_ws/log_nvblox_map.txt | rg -n "Dropped an item|Rates statistics|Delay statistics" -i`
- Cloud shape: `ros2 topic echo -n1 /airy_201/rslidar_points | rg -n "height:|width:"`


Update — 2025‑08‑27: Repack now default in `oak map`
---------------------------------------------------

- `oak map` now launches NVBlox with LiDAR repack enabled by default (no manual NVBlox launch required).
  - C++ repack (`lidar_tools_cpp/pc_reorder`) row‑reorders AIRY range image using `alpha_rover/channel_distance_table.csv`.
  - Defaults: `use_repack=true`, `use_cpp_repack=true`, `repack_throttle_n=1`, `repack_qos_depth=1`.
  - Customize NVBlox at launch via env var `NVBLOX_ARGS`, e.g.:
    - `export NVBLOX_ARGS="voxel_size:=0.10 lidar_integrate_hz:=10.0 streamer_mbps:=10.0"`
    - Then run `oak map --lidar-only --lidar rear`.
- Visualization guidance:
  - Foxglove: add `/nvblox_node/tsdf_layer_marker` (Marker) or `/nvblox_node/static_esdf_pointcloud` (PointCloud2).
  - RViz: can render `/nvblox_node/tsdf_layer` and `/nvblox_node/mesh` directly.
- Note: Ensure only one NVBlox instance is running. Multiple instances publishing to `/nvblox_node/*` can cause alternating voxel sizes.

Shutdown robustness
- `oak stop` now also kills:
  - lingering `pc_reorder`/`pc_repack` repackers
  - stray `robot_state_publisher` instances
  - leftover probe nodes used during debugging (`probe_pc`/`probe_raw`)
  - any other `launch_all.sh` instances to avoid hanging terminals with `rclcpp signal_handler` lines
