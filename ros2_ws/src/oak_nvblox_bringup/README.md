oak_nvblox_bringup
===================

Minimal bringup to run NVIDIA Isaac ROS nvblox against the OAK‑D Pro depth stream.

Launch
------

```
source ~/ros2_ws/install/setup.bash
ros2 launch oak_nvblox_bringup nvblox_dual_cams_with_lidar.launch.py  # Dual cameras + front LiDAR (recommended)
ros2 launch oak_nvblox_bringup nvblox_from_oak_with_lidar.launch.py   # Pro depth + front LiDAR
```

Defaults:
- Subscribes to `/oak_d_pro/camera/stereo/{image_raw,camera_info}` for depth.
- If dual cameras: also subscribes to `/oak_d_sr/camera/stereo/{image_raw,camera_info}`.
- Uses `global_frame=base_link` and QoS `SENSOR_DATA`.
- `use_color=false` by default (avoids BGR8 vs RGB8 mismatch on OAK RGB).
 - ESDF mode is 3D; a 2D slice is also published for convenience.
- LiDAR launch sets min range to 0.25 m by default.

QoS note
--------
- RoboSense point clouds are now published with SensorDataQoS (BEST_EFFORT) directly from the driver for compatibility with nvblox's SENSOR_DATA input.
- No external QoS bridge is required.

Visualization (Foxglove)
------------------------
- Connect: `ws://<robot-ip>:8765`
- Fixed frame: `base_link`
- Topics: `/nvblox_node/static_esdf_pointcloud`, `/nvblox_node/static_map_slice`,
  `/nvblox_node/static_occupancy_grid`, `/nvblox_node/combined_occupancy_grid`, `/nvblox_node/mesh`.

Notes
-----
- Switch mapping frame to `odom`/`map` when odometry/localization is available.
- To enable color integration, either publish RGB8 from the camera or insert a RGB conversion node.
