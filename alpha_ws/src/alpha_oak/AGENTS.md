---
agent: "alpha_oak"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_oak"
  readme: "../alpha_ws/src/alpha_oak/README.md"
  docs: "../docs"
dependencies:
  internal: ["alpha_utils","alpha_bringup"]
  external: ["depthai_ros_driver"]
provides:
  topics_pub:
    - {name: "/alpha/cam/front/image_color", type: "sensor_msgs/Image", rate_hz: 30}
    - {name: "/alpha/cam/front/camera_info", type: "sensor_msgs/CameraInfo", rate_hz: 1}
    - {name: "/alpha/cam/rear/image_color", type: "sensor_msgs/Image", rate_hz: 30}
    - {name: "/alpha/cam/rear/camera_info", type: "sensor_msgs/CameraInfo", rate_hz: 1}
  topics_sub: []
  services: []
  actions: []
configs:
  - "../alpha_configs/oak_cams.yaml"
runbooks:
  start: |
    ros2 launch alpha_oak oak_bringup.launch.py
  stop: |
    pkill -f depthai_ros_driver || true
  healthcheck: |
    ros2 topic echo -n 1 /alpha/cam/front/camera_info
    ros2 topic hz /alpha/cam/front/image_color -w 30
observability:
  slo:
    - {name: "video_latency_ms_p95", target: 120}
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["INIT","RUNNING","FAILED"]
  transitions: []
failure_modes: []
tests:
  acceptance:
    - {id: "OAK-RATE", description: "RGB at configured FPS", pass_criteria: "az hz≥target"}
  ci_jobs: []
notes: >
  Uses apt-installed depthai_ros_driver. Switch to source/pinned SHA only if features/fixes require.

---
# AGENT — alpha_oak

## Interfaces
- Publishes canonical camera topics for front/rear OAK devices.

## Runbooks
See start/stop/healthcheck above.
