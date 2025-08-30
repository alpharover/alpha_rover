---

# **RoboSense Airy → NVBlox Integration: Implementation & Troubleshooting Playbook**

## **0\) Scope & success criteria**

Goal: NVBlox integrates 3D point clouds from Airy and produces live TSDF/ESDF/mesh outputs with stable timing (no transform extrapolation, no silent drops).

Pass conditions:

* NVBlox receives /pointcloud (PointCloud2), integrates at \~10 Hz, and publishes non-empty /nvblox\_node/mesh (or TSDF/ESDF topics).

* No TF lookup/extrapolation errors.

* No persistent “queue full” or “late transform” logs.

---

## **1\) Map Airy specs to NVBlox intrinsics (must match, or NVBlox ignores the cloud)**

From the Airy manual:

* Channels (rings): 96 → lidar\_height: 96\. 

* Vertical FOV: 0° … 90° (hemisphere upward). Use asymmetric FOV in NVBlox:

   min\_angle\_below\_zero\_elevation\_rad: 0.0, max\_angle\_above\_zero\_elevation\_rad: 1.570796. 

* Azimuth (horizontal) resolution: 0.4° → columns per rev \= 360/0.4 \= 900 → lidar\_width: 900\. 

* Spin / frame rate: 600 rpm \= 10 Hz. 

* Range & blind zone: 0.10 m blind zone, up to 60 m measurement range → set NVBlox gates accordingly. 

* 5 ms “gap” per second (≈ one frame): one out of every 10 frames has a \~32° missing wedge; place the start angle behind the robot via Phase Lock / Frame Start Angle to avoid carving the forward view. 

* Time sync options: GPS, PTP, gPTP supported (status exposed).   

* Default network: Device IP 192.168.1.200, MSOP 6699, DIFOP 7788\. 

* Coordinate frame origin: center of the LiDAR base (model airy\_link there). 

---

## **2\) NVBlox parameters — Airy-specific YAML (drop-in)**

\# nvblox\_airy.yaml  
nvblox\_node:  
  ros\_\_parameters:  
    \# Inputs used  
    use\_depth: false  
    use\_lidar: true

    \# Frames / transforms  
    global\_frame: map          \# use 'odom' if that's your world  
    use\_tf\_transforms: true  
    use\_topic\_transforms: false  
    pose\_frame: base\_link      \# only used if you disable TF

    \# Airy LiDAR model (exact)  
    lidar\_height: 96  
    lidar\_width: 900  
    use\_non\_equal\_vertical\_fov\_lidar\_params: true  
    min\_angle\_below\_zero\_elevation\_rad: 0.0  
    max\_angle\_above\_zero\_elevation\_rad: 1.57079632679  \# 90 deg

    \# Range gates from spec  
    lidar\_min\_valid\_range\_m: 0.10  
    lidar\_max\_valid\_range\_m: 60.0

    \# Integration distances (default 10 m is too short for rooms/outdoors)  
    static\_mapper:  
      lidar\_projective\_integrator\_max\_integration\_distance\_m: 25.0  
    dynamic\_mapper:  
      lidar\_projective\_integrator\_max\_integration\_distance\_m: 25.0

    \# Rates / buffering  
    integrate\_lidar\_rate\_hz: 10.0  
    maximum\_input\_queue\_length: 50  
    \# If your LiDAR driver publishes best-effort SensorData QoS, consider:  
    \# input\_qos: "SENSOR\_DATA"

    \# Debug visibility (avoid hiding data while bringing up)  
    layer\_visualization\_exclusion\_radius\_m: 0.0  
    layer\_visualization\_exclusion\_height\_m: 0.0  
    map\_clearing\_radius\_m: 0.0

    \# Useful debugging prints  
    print\_rates\_to\_console: true  
    print\_delays\_to\_console: true  
---

## **3\) Launch wiring (ROS 2\)**

Make NVBlox subscribe to your Airy cloud via remap to pointcloud:

\# nvblox\_with\_airy.launch.py  
from launch import LaunchDescription  
from launch\_ros.actions import Node

def generate\_launch\_description():  
    return LaunchDescription(\[  
        Node(  
            package="isaac\_ros\_nvblox",  
            executable="nvblox\_node",  
            name="nvblox\_node",  
            output="screen",  
            parameters=\["/path/to/nvblox\_airy.yaml"\],  
            remappings=\[  
                ("pointcloud", "/airy/rslidar\_points"),    \# \<-- your Airy topic  
            \],  
        ),  
    \])  
---

## **4\) Time synchronization & stamping policy (pick ONE, be consistent)**

Option A — Sensor-time (best with PTP/gPTP/GPS wired):

* Keep the LiDAR/driver publishing sensor timestamps in the PointCloud2 header (from MSOP).

* Ensure your robot state (TF/odometry) uses the same time base; lock Jetson \+ network to PTP/gPTP or GPS.

* Verify Time Sync Mode/Status via DIFOP and Web UI.   

Option B — ROS-time (practical fallback):

* Configure your ROS LiDAR driver to stamp PointCloud2.header.stamp with ROS time (not the device clock).

* Keep all TF producers on ROS time.

* This avoids transform extrapolation when no PTP/gPTP/GPS is available.

Do not mix sensor-time clouds with ROS-time TF. That’s the fastest way to make NVBlox “look alive” while it drops every scan.

---

## **5\) TF / extrinsics**

* URDF: define airy\_link with origin at center of the LiDAR base (per manual). 

* Provide a stable chain: map → odom → base\_link → airy\_link.

* Verify at runtime:

ros2 run tf2\_ros tf2\_echo base\_link airy\_link  
---

## **6\) Airy device setup essentials**

* Network: set host to the same /24 as the device (192.168.1.x); Airy defaults: IP 192.168.1.200, MSOP 6699, DIFOP 7788\. 

* Use RSView/Wireshark to confirm packets; DIFOP carries config & status (motor speed, time sync mode/status, vertical & horizontal angle calibration).     

* Phase Lock & Start Angle: set the locked phase and place the gap behind the robot so each forward scan is complete. (Web UI → Phase Lock Setting.)   

* Return mode: start with Strongest (factory default). Change in Web UI if needed; Dual doubles data volume. 

---

## **7\) Fast diagnostics (copy/paste block)**

\# 1\) Verify the raw cloud  
ros2 topic info \-v /airy/rslidar\_points  
ros2 topic hz /airy/rslidar\_points  
ros2 topic echo \-n1 /airy/rslidar\_points | sed \-n '1,25p'   \# header.stamp, header.frame\_id

\# 2\) Check TF linkage at message time  
ros2 run tf2\_ros tf2\_echo base\_link airy\_link

\# 3\) Confirm NVBlox is receiving & integrating  
ros2 param set /nvblox\_node print\_rates\_to\_console true  
ros2 param set /nvblox\_node print\_delays\_to\_console true

\# 4\) Watch outputs (any non-empty topic is a win)  
ros2 topic echo \-n1 /nvblox\_node/mesh/vertices   \# or visualize in Foxglove/RViz  
ros2 topic list | grep nvblox

Expected:

* hz \~ 10 Hz; header.frame\_id stable (e.g., airy\_link); header.stamp monotonic.

* TF echo prints transforms without “extrapolation” complaints.

* NVBlox prints healthy input rates and delay stats; mesh/TSDF topics non-empty.

---

## **8\) Common failure modes → blunt fixes**

* Nothing integrates → Intrinsics wrong or missing: set lidar\_height: 96, lidar\_width: 900, asymmetric vertical FOV 0…90°. (Don’t use a generic 16-ring/30° profile.)   

* Transform extrapolation → Mixed clocks. Use PTP/gPTP/GPS end-to-end (Option A) or stamp with ROS time everywhere (Option B). 

* Looks “near-sighted” → Raise NVBlox LiDAR integrator max distance to ≥ 20–25 m (both static\_mapper and dynamic\_mapper).

* Bursty drops → Increase maximum\_input\_queue\_length (50–100) and match QoS to your driver (often sensor/best-effort).

* Forward arc missing every 10th frame → set Phase Lock/Start Angle so the 32° gap sits behind the chassis. 

---

## **9\) Minimal end-to-end smoke test**

1. Bring up Airy (verify MSOP/DIFOP traffic; web at http://192.168.1.200). 

2. Start the Airy ROS driver (/airy/rslidar\_points present, 10 Hz).

3. Launch NVBlox with the Airy YAML and remap to pointcloud.

4. Move the robot / sweep the sensor; confirm live updates in /nvblox\_node/mesh or TSDF/ESDF outputs.

5. If empty: check intrinsics, clock consistency, TF, then integration distance—in that order.

---

### **Appendix — Rationale for strict asymmetry**

Airy’s vertical coverage is 0°…90° (horizon→zenith). Using a symmetric ±45° vertical model misprojects rows during NVBlox’s pointcloud→depth projection and can yield “nothing happens” even with healthy topics and TF. Use the asymmetric min/max above.

---

If you want this tailored to your repo’s launcher (e.g., oak map \--lidar rear) I can slot these params/remaps directly into your launch \+ YAML and output a ready-to-drop PR.

