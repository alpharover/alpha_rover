# alpha_lidar_airy_cpp — C++ Reorder Backend

- Purpose: high‑performance row reorder for RoboSense AIRY organized clouds.
- Subscribes: `/alpha/lidar/{front,rear}/points_raw` (sensor_msgs/PointCloud2)
- Publishes: `/alpha/lidar/{front,rear}/points` (SensorData QoS), exact 96×900
- Timestamp policy: preserves sensor header stamp by default (`timestamp_policy:=sensor`)
- Diagnostics: `reorder_backend=cpp`, latency, rates, pad/normalize counters, `angle_table_hash`

Launch via:

```
ros2 launch alpha_lidar_airy airy_bringup.launch.py backend:=cpp start_mode_service:=false
```
