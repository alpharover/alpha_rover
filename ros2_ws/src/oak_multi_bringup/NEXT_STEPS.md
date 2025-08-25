Next Steps: OAK Bringup + LiDAR + Foxglove

Status (Humble, oak_multi_bringup)
- TF source: URDF via robot_state_publisher (single source of truth)
  - Pro frame `camera_rgb_camera_optical_frame`: xyz [0.148469, 0, 0.097926], rpy [-1.8325957, 0, -1.5707963]
  - SR frame `camera_right_camera_optical_frame`: xyz [-0.211326, 0, 0.023959], rpy [-1.6580628, 0, 1.5707963]
- Driver TFs: disabled (`camera.i_publish_tf_from_calibration: false` for both)
- SR: 20.0 Hz, 400P, `stereo.i_publish_synced_rect_pair: false`, IMU disabled
- Launches:
  - TF: `ros2 launch oak_multi_bringup robot_state.launch.py`
  - Pro: `ros2 launch oak_multi_bringup oak_pro.launch.py`
  - SR: `ros2 launch oak_multi_bringup oak_sr.launch.py`
  - Multi: `ros2 launch oak_multi_bringup oak_multi.launch.py` (ST container; see TODO for split)
  - Foxglove: `ros2 launch oak_multi_bringup foxglove_bridge.launch.py`
- Foxglove: point cloud not yet visible; QoS overrides added; backpressure suspected

Open Issues / TODOs
1) Multi-cam stability
   - Split `oak_multi.launch.py` into two containers (`oak_pro_container`, `oak_sr_container`).
   - Keep `use_intra_process_comms: false` for all composables.
   - If still unstable, run pointcloud nodes as standalone processes instead of composables.

2) Foxglove PointCloud2 visibility
   - Verify bridge QoS params active (best_effort, depth 1) and TF settings (`tf_static` reliable + transient_local).
   - Add optional throttled/downsampled cloud (topic_tools relay or voxel grid) for Foxglove, e.g. `/oak_d_sr/points_viz`.
   - Consider lowering SR FPS to 15.0 if still dropping.

3) URDF install hygiene
   - Ensure CMake includes: `install(DIRECTORY launch config urdf DESTINATION share/${PROJECT_NAME})`.
   - Rebuild + source so `robot_state.launch.py` can always use the installed path.

4) Robosense Airy LiDARs (dual)
   - Provide mount extrinsics (xyz [m], rpy [rad or deg] specify units) for left/right sensors.
   - Update `urdf/oak_sensors.urdf.xacro` properties: `airy_left_xyz/rpy`, `airy_right_xyz/rpy`.
   - Add frame names expected by LiDAR drivers (e.g., `laser_left`, `laser_right`) if needed.

5) Isaac ROS Visual SLAM integration
   - Confirm rectified image topics naming or add remaps to match Isaac’s defaults.
   - Ensure camera_info.frame_id resolves in TF; fixed frame should be `base_link`.

Quick Run Commands
- TF: `ros2 launch oak_multi_bringup robot_state.launch.py`
- Pro: `ros2 launch oak_multi_bringup oak_pro.launch.py`
- SR: `ros2 launch oak_multi_bringup oak_sr.launch.py`
- Multi: `ros2 launch oak_multi_bringup oak_multi.launch.py`
- Foxglove: `ros2 launch oak_multi_bringup foxglove_bridge.launch.py` (connect to `ws://<robot-ip>:8765`)

