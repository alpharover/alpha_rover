# OAK-D-Pro/SR Bringup + URDF

## Overview
This package launches Luxonis OAK cameras with clean namespaces and point clouds:
- `/oak_d_pro`: OAK-D-Pro-W (RGB+D) with colorized point cloud
- `/oak_d_sr`: OAK-D-SR (Depth-only) with XYZ point cloud

It also integrates dual Robosense AIRY LiDARs into the same TF tree via URDF
(`airy_front` and `airy_rear` frames), launched separately from the `rslidar_sdk` package.

## Launch

### Quick Start (Recommended)
1) Build and source
   - `cd ~/ros2_ws && colcon build --packages-select oak_multi_bringup --symlink-install`
   - `source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash`

2) Start TF (URDF via robot_state_publisher)
   - `ros2 launch oak_multi_bringup robot_state.launch.py`

3) Bring up cameras (split containers for stability)
   - Terminal A (Pro): `ros2 launch oak_multi_bringup oak_pro.launch.py`
   - Terminal B (SR):  `ros2 launch oak_multi_bringup oak_sr.launch.py`
   - Note: Both launches default to installed params under `share/oak_multi_bringup/config`. To override explicitly, pass `params_file:=<path>` (e.g., `.../config/oak_pro_only.yaml`, `.../config/oak_sr_only.yaml`).

4) Foxglove (optional)
   - `ros2 launch oak_multi_bringup foxglove_bridge.launch.py`
   - Connect to `ws://<robot-ip>:8765` and set Fixed Frame to `base_link`.

### Airy LiDARs (Front + Rear)
- Launch both AIRY sensors (in a new terminal):
  - `ros2 launch rslidar_sdk dual_airy_start.py`
- Frames align with URDF: `airy_front` (maps to `/airy_200/*` topics) and `airy_rear` (maps to `/airy_201/*`).
- For detailed network/ports config see `DUAL_AIRY_SETUP.md`.

### Combined (optional)
- Start both cameras in one container (use if stable on your system):
  - `ros2 launch oak_multi_bringup oak_multi.launch.py`
  - If you encounter instability, prefer the split method above.

### Tips
- Ensure each camera `camera.i_mx_id` in YAML matches your devices (defaults provided).
- Startup order: TF first, then cameras, then Foxglove for best results.
- If using a shared network, set `ROS_DOMAIN_ID` to avoid cross-talk.
- For USB reliability, use USB 3.x ports/cables and powered hubs when possible.
- Install DepthAI udev rules so cameras are accessible without sudo.

### Device already in use (X_LINK_DEVICE_ALREADY_IN_USE)
If you see an "already in use" error:
- Stop all related launches (CTRL-C) and wait 3–5s.
- Optionally `pkill -f 'ros2 launch .*oak_multi_bringup|component_container|foxglove_bridge'`.
- Power-cycle the affected OAK (unplug/replug or hub power toggle).
- Start cameras individually first (Pro-only, then SR-only) before running both.
- Avoid running the combined launch and single-cam launches at the same time.

## URDF TF (robot_state_publisher)
- URDF: `urdf/oak_sensors.urdf.xacro` publishes fixed transforms from `base_link` to:
  - `camera_rgb_camera_optical_frame` (Pro)
  - `camera_right_camera_optical_frame` (SR)
  - Robosense Airy LiDARs: `airy_front`, `airy_rear` (updated xyz/rpy)
- Launch TF via RSP:
  - `ros2 launch oak_multi_bringup robot_state.launch.py`
- Fully adopted: drivers no longer publish TFs; static TF publishers were removed from camera launches.

## Topics
- Images: `/oak_d_pro/camera/rgb/image_raw` (with `/oak_d_pro/camera/rgb/camera_info`)
- Depth: `/oak_d_pro/camera/stereo/image_raw` (encoding: 16UC1) with `/oak_d_pro/camera/stereo/camera_info`
- Point cloud: `/oak_d_pro/points` (sensor_msgs/PointCloud2, ~10 Hz)

SR topics:
- Depth: `/oak_d_sr/camera/stereo/image_raw` (16UC1) with `/oak_d_sr/camera/stereo/camera_info`
- Point cloud: `/oak_d_sr/points` (sensor_msgs/PointCloud2, ~10 Hz)

Airy topics:
- Front (`airy_front` frame): `/airy_200/rslidar_points`, `/airy_200/rslidar_imu`
- Rear (`airy_rear` frame): `/airy_201/rslidar_points`, `/airy_201/rslidar_imu`

## QoS (Foxglove Bridge)
PointCloud2 uses sensor-data QoS (best effort). The provided launch uses `config/foxglove_qos.yaml` so the bridge subscribes best-effort to both point clouds and uses reliable + transient_local for `/tf_static`.
- If running a generic bridge, you can set overrides at runtime:
  - `ros2 param set /foxglove_bridge "qos_overrides./oak_d_pro/points.subscription.reliability" best_effort`
  - `ros2 param set /foxglove_bridge "qos_overrides./oak_d_sr/points.subscription.reliability" best_effort`
  - (Optional for images/camera_info with the same pattern.)
  - Airy clouds are also set to best_effort in `config/foxglove_qos.yaml` for `/airy_200/rslidar_points` and `/airy_201/rslidar_points`.

## Mounting (TF)
Mounts measured from `base_link` (sensor fixture center). URDF encodes these:
  - Pro → `camera_rgb_camera_optical_frame`:
    - Translation (m): x=0.148469, y=0.0, z=0.097926
    - Orientation: forward, 15° down; RPY rad `[-1.8325957, 0.0, -1.5707963]`
  - SR → `camera_right_camera_optical_frame`:
    - Translation (m): x=-0.211326, y=0.0, z=0.023959
    - Orientation: rear, 5° down; RPY rad `[-1.6580628, 0.0, 1.5707963]`

Airy LiDARs:
- Front (`airy_front`):
  - Translation (m): x=0.110367, y=0.0, z=0.037388
  - Orientation: z→forward, y→up, x→left; RPY rad `[+1.5707963, 0.0, +1.5707963]`
- Rear (`airy_rear`):
  - Translation (m): x=-0.203071, y=0.0, z=0.061300  (rear is negative x)
  - Orientation: z→up, y→rear, x→left; RPY rad `[0.0, 0.0, +1.5707963]`

Notes:
- The Airy drivers publish clouds under `/airy_200/*` and `/airy_201/*` topics, but their `frame_id`s are set to `airy_front` and `airy_rear` to align with the URDF.

## Parameters (key settings)
Provided in `config/oak_pro_only.yaml` (Pro):
- `camera.i_pipeline_type: RGBD`
- `stereo.i_align_depth: true`, `stereo.i_lr_check: true`, `stereo.i_subpixel: true`
- `stereo.i_output_disparity: false` (publish depth, not disparity)
- `rgb.i_fps: 30.0`
- `camera.i_publish_tf_from_calibration: false` (URDF owns TF)
- Set `camera.i_mx_id` to your OAK-D-Pro MXID as needed.

Provided in `config/oak_sr_only.yaml` (SR):
- `camera.i_pipeline_type: Depth`
- `stereo.i_align_depth: false`, `stereo.i_lr_check: true`, `stereo.i_subpixel: true`
- `stereo.i_fps: 20.0`, `stereo.i_resolution: 400P`
- `stereo.i_publish_synced_rect_pair: false`
- `stereo.i_output_disparity: false`
- `imu.i_enable_imu: false`
- `camera.i_publish_tf_from_calibration: false` (URDF owns TF)
- Set `camera.i_mx_id` to your OAK-D-SR MXID as needed.

## Troubleshooting / Status
- Verify depth encoding: `ros2 topic echo --once /oak_d_pro/camera/stereo/image_raw | grep encoding`
- No cloud in Foxglove: ensure bridge QoS best effort and fixed frame `base_link`.
- Check rates: `ros2 topic hz /oak_d_pro/points`.
  - For SR: `ros2 topic hz /oak_d_sr/points`.
 - Current: RViz2 OK; Foxglove cloud pending QoS/backpressure tuning.

## Foxglove Bridge
- Launch: `ros2 launch oak_multi_bringup foxglove_bridge.launch.py`
- QoS configured in `config/foxglove_qos.yaml` for point clouds (best_effort, depth 1) and TF (`tf_static` reliable + transient_local).
- In Foxglove: connect to `ws://<robot-ip>:8765`, set Fixed Frame `base_link`, add `/oak_d_sr/points` or `/oak_d_pro/points`.
  - Airy clouds: add `/airy_200/rslidar_points` and `/airy_201/rslidar_points` (QoS best_effort is preconfigured).

## End-to-End Launch (All Sensors + Foxglove)
1) Build + source: `cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash`
2) TF: `ros2 launch oak_multi_bringup robot_state.launch.py`
3) OAK-D Pro: `ros2 launch oak_multi_bringup oak_pro.launch.py`
4) OAK-D SR: `ros2 launch oak_multi_bringup oak_sr.launch.py`
5) AIRY LiDARs: `ros2 launch rslidar_sdk dual_airy_start.py`
6) Foxglove Bridge (optional): `ros2 launch oak_multi_bringup foxglove_bridge.launch.py`
7) In Foxglove: connect to `ws://<robot-ip>:8765`, set Fixed Frame `base_link`, add `/oak_d_pro/points`, `/oak_d_sr/points`, `/airy_200/rslidar_points`, `/airy_201/rslidar_points`.

## TF Reference (fixed transforms)
- `base_link -> camera_rgb_camera_optical_frame`
  - xyz: `0.148469 0.0 0.097926`, rpy: `-1.8325957 0.0 -1.5707963`
- `base_link -> camera_right_camera_optical_frame`
  - xyz: `-0.211326 0.0 0.023959`, rpy: `-1.6580628 0.0 1.5707963`
- `base_link -> airy_front`
  - xyz: `0.110367 0.0 0.037388`, rpy: `1.5707963 0.0 1.5707963`
- `base_link -> airy_rear`
  - xyz: `-0.203071 0.0 0.061300`, rpy: `0.0 0.0 1.5707963`

Verification:
- `ros2 topic echo --once /tf_static` (should include frames above)
- `ros2 run tf2_tools view_frames` (graph the TF tree)
