# Glim Configuration Changes

This file tracks modifications made to the configuration files in this directory.

## `config_sub_mapping_gpu.json`

- **2025-07-17:** Increased map update frequency.
  - `"keyframe_update_interval_trans"`: `1.0` -> `0.5`
  - `"keyframe_update_interval_rot"`: `3.14` -> `1.57`

- **2025-07-17:** Tuned for small indoor environment map quality.
  - `"max_num_keyframes"`: `15` -> `5`
  - `"keyframe_voxel_resolution"`: `0.25` -> `0.15`
  - `"submap_downsample_resolution"`: `0.1` -> `0.05`

## `config_sensors.json`

- **2025-07-17:** Updated with sensor-specific IMU calibration data.
  - `"T_lidar_imu"`: `[-0.706479, 0.707706, 0.00372143, -0.00497837]` -> `[0.711904, -0.702254, 0.00340482, 0.00459558]` (rotation part only)
