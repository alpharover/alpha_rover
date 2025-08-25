# Dual AIRY LiDAR Setup Documentation

## Quick Start (When You're Tired and Forget Everything!)

### To Launch Both AIRY Sensors:
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch rslidar_sdk dual_airy_start.py
```

### To Verify It's Working:
Open a new terminal and run:
```bash
source ~/ros2_ws/install/setup.bash
ros2 topic list | grep rslidar
ros2 topic hz /airy_200/rslidar_points
ros2 topic hz /airy_201/rslidar_points
```

Expected topics:
- `/airy_200/rslidar_points` (LiDAR point cloud from sensor 1)
- `/airy_200/rslidar_imu` (IMU data from sensor 1)
- `/airy_201/rslidar_points` (LiDAR point cloud from sensor 2)
- `/airy_201/rslidar_imu` (IMU data from sensor 2)

---

## Hardware Configuration

### AIRY Sensor 1 (192.168.1.200):
- **Device IP**: 192.168.1.200
- **MSOP Port**: 6699
- **DIFOP Port**: 7788
- **IMU Port**: 6688
- **Destination IP**: 192.168.1.10 (Jetson)

### AIRY Sensor 2 (192.168.1.201):
- **Device IP**: 192.168.1.201
- **MSOP Port**: 6700 (different!)
- **DIFOP Port**: 7789 (different!)
- **IMU Port**: 6689 (different!)
- **Destination IP**: 192.168.1.10 (Jetson)

### Jetson Network:
- **IP Address**: 192.168.1.10
- **Listens on ports**: 6699, 6700, 6688, 6689, 7788, 7789

---

## File Locations

### Launch File:
`/home/alpha_orin/ros2_ws/src/rslidar_sdk/launch/dual_airy_start.py`

### Configuration Files:
- **Sensor 1**: `/home/alpha_orin/ros2_ws/src/rslidar_sdk/config/config_airy_200.yaml`
- **Sensor 2**: `/home/alpha_orin/ros2_ws/src/rslidar_sdk/config/config_airy_201.yaml`

---

## Key Configuration Differences

| Parameter | Sensor 1 (200) | Sensor 2 (201) |
|-----------|----------------|----------------|
| msop_port | 6699 | 6700 |
| difop_port | 7788 | 7789 |
| imu_port | 6688 | 6689 |
| ros_frame_id | airy_front | airy_rear |
| Topics | /airy_200/* | /airy_201/* |

---

## Expected Performance
- **Sensor 1**: ~7 Hz point cloud rate
- **Sensor 2**: ~5 Hz point cloud rate
- **Both sensors**: Provide IMU data and point clouds simultaneously

---

## Troubleshooting

### If Launch Fails:
1. Make sure workspace is built: `colcon build --packages-select rslidar_sdk`
2. Source the workspace: `source install/setup.bash`
3. Check sensor network settings match the config above
4. Verify both sensors are powered and connected to network

### If No Data:
1. Check topic list: `ros2 topic list | grep rslidar`
2. Check topic rates: `ros2 topic hz /airy_200/rslidar_points`
3. Verify sensor destination IPs are set to 192.168.1.10
4. Check firewall isn't blocking the ports

### If Port Conflicts:
- Only one instance of this launch file can run at a time
- Kill existing processes before relaunching
- Use `ros2 node list` to check for existing nodes

---

## Files Created for This Setup

1. **dual_airy_start.py** - Main launch file for both sensors
2. **config_airy_200.yaml** - Configuration for first sensor (ports 6699/7788/6688)
3. **config_airy_201.yaml** - Configuration for second sensor (ports 6700/7789/6689)

---

## Single Sensor Launch (Backup)
If you only want to run one sensor, use the original:
```bash
ros2 launch rslidar_sdk humble_start.py
```

---

### TF/URDF Integration
For consistent transforms with OAK cameras, start the robot_state_publisher first:
```bash
ros2 launch oak_multi_bringup robot_state.launch.py
```
The URDF defines `base_link -> airy_front` and `base_link -> airy_rear` static transforms.
Both AIRY configs set `ros_frame_id` to these links, so clouds/IMU align in TF.

Reference TF coordinates (xyz in meters, rpy in radians):

```yaml
# AIRY Front: forward-facing LiDAR
airy_front:
  translation: [0.110367, 0.0, 0.037388]
  rotation: [1.5707963, 0.0, 1.5707963]

# AIRY Rear: rear-facing LiDAR
airy_rear:
  translation: [-0.203071, 0.0, 0.061300]
  rotation: [0.0, 0.0, 1.5707963]
```

*Last updated: August 21, 2025*
*Dual AIRY setup successfully tested and working*

---

## Standby / Run Power Control

- Default boot behavior: both AIRY LiDARs are forced to Standby to minimize heat.
  - Managed by user service `airy-standby.service` (runs `airy_boot_standby.sh`).
  - Status: `systemctl --user status airy-standby.service`
  - Logs: `journalctl --user -u airy-standby.service -e -f`
  - Disable: `systemctl --user disable --now airy-standby.service`

- Manual control (CLI):
  - Show: `oak lidar status`
  - Standby: `oak lidar standby`
  - Run: `oak lidar run`
  - Target specific unit: add `--lidar front|rear` (default both)
  - Override IPs: `--front-ip 192.168.1.200 --rear-ip 192.168.1.201`

- Launch integration:
  - `oak start`/`oak map` brings LiDARs to Run before starting `rslidar_sdk`.
  - `oak stop` returns them to Standby.
