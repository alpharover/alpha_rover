# alpha_oak — OAK Camera Bringup

Launches OAK cameras (front/rear) and remaps to canonical topics.
- Publishes: `/alpha/cam/{front,rear}/image_color`, `/alpha/cam/{front,rear}/camera_info`
- QoS: SensorData (BestEffort/Volatile)
- Dependency: `depthai_ros_driver` (prefer APT install on target)

Run:

```
ros2 launch alpha_oak oak_bringup.launch.py
```
