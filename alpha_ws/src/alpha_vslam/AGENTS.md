---
agent: "alpha_vslam"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_vslam"
  docs: "../docs"
dependencies:
  internal: []
  external: ["isaac_ros_visual_slam"]
provides:
  topics_pub:
    - {name: "/alpha/vslam/odom", type: "nav_msgs/Odometry", rate_hz: 30}
  topics_sub:
    - {name: "/alpha/cam/front/image_color", type: "sensor_msgs/Image"}
    - {name: "/alpha/cam/front/camera_info", type: "sensor_msgs/CameraInfo"}
  services: []
  actions: []
configs: []
runbooks:
  start: |
    docker compose -f deploy/compose.vslam.yaml --env-file deploy/IMAGES.lock up -d
  stop: |
    docker compose -f deploy/compose.vslam.yaml --env-file deploy/IMAGES.lock down || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/vslam/odom || true
observability:
  slo: []
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["CONTAINERIZED"]
  transitions: []
failure_modes: []
tests:
  acceptance: []
  ci_jobs: []
notes: >
  Runs Isaac ROS Visual SLAM inside a container with pinned image digest.

---
# AGENT — alpha_vslam

Wrapper that launches Visual SLAM in a container and remaps inputs to canonical camera topics. Adjust launch parameters and remappings for stereo as needed.
