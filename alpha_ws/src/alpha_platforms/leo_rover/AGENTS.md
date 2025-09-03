---
agent: "alpha_platforms_leo_rover"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-09-02"
owner: "Alpha SW"
links:
  roadmap: "../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_platforms/leo_rover"
  readme: "../alpha_ws/src/alpha_platforms/leo_rover/README.md"
  docs: "../docs"
dependencies:
  internal: []
  external: ["rclpy","robot_state_publisher","xacro"]
provides:
  topics_pub:
    - {name: "/alpha/health/adapter_alive", type: "std_msgs/Bool", rate_hz: 1, description: "Adapter heartbeat"}
    - {name: "/alpha/odom", type: "nav_msgs/Odometry", rate_hz: 0, description: "If mapped from platform"}
    - {name: "/alpha/camera/front/image", type: "sensor_msgs/Image", rate_hz: 0, description: "If mapped from platform"}
  topics_sub:
    - {name: "/alpha/cmd_vel", type: "geometry_msgs/Twist", description: "Bridged to /cmd_vel"}
  services: []
  actions: []
configs:
  - "../alpha_ws/src/alpha_platforms/leo_rover/config/leo_rover.yaml"
runbooks:
  start: |
    # Launch adapter + robot_state_publisher via the package launch
    ros2 launch alpha_platforms_leo_rover leorover_adapter.launch.py \
      mapping_config:=$HOME/alpha_rover/alpha_ws/src/alpha_platforms/leo_rover/config/leo_rover.yaml
  stop: |
    pkill -f leorover_adapter || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/health/adapter_alive
observability:
  slo:
    - {name: "adapter_heartbeat_hz", target: 1}
  metrics:
    - {name: "bridge_count", source: "log", note: "Count of active mappings at startup"}
  logs:
    - {source: "rosout", grep: "[bridge]"}
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["INIT","RUNNING","FAILED","SHUTDOWN"]
  transitions: ["INIT->RUNNING","RUNNING->FAILED"]
failure_modes:
  - {id: "LEO-01", symptom: "No /alpha/health/adapter_alive", detection: "heartbeat missing", recovery: "restart launch"}
tests:
  acceptance:
    - {id: "LEO-BOOT-01", description: "Adapter publishes heartbeat within 5s", pass_criteria: "Bool True observed"}
  ci_jobs:
    - {id: "lint", description: "flake8/style checks"}
notes: >
  Bridges Leo Rover platform topics and frames onto the canonical /alpha/* namespace with QoS normalization.
---

# AGENT — alpha_platforms_leo_rover

## 1) Mission & Context
Normalize Leo Rover platform interfaces to ALPHA canonical topics and TF. Provide a minimal TF tree via robot_state_publisher.

## 2) Responsibilities & Boundaries
- Must: bridge configured topics with appropriate QoS; publish heartbeat.
- Not: own platform drivers or camera/odometry generation; only adapts existing topics.

## 3) Interfaces
### Topics (publish)
| Name | Type | Rate | Notes |
|---|---|---:|---|
| /alpha/health/adapter_alive | std_msgs/Bool | 1 | Heartbeat |
| /alpha/odom | nav_msgs/Odometry | 0 | If mapping configured |
| /alpha/camera/front/image | sensor_msgs/Image | 0 | If mapping configured |

### Topics (subscribe)
| Name | Type | Notes |
|---|---|---|
| /alpha/cmd_vel | geometry_msgs/Twist | Bridged to /cmd_vel |

### Parameters & Config Keys
- mapping_config: path to YAML listing `mappings` entries (type,in,out,in_qos,out_qos,...).

## 4) Runbooks
See front matter runbooks for canonical commands.

## 5) Observability
- Heartbeat topic at 1 Hz; bridge lines logged on startup.

## 6) Failure Modes & Recovery
- LEO-01: Missing heartbeat. Recovery: relaunch adapter; verify ROS discovery and config path.

## 7) Security
- No secrets; SROS2 not configured yet.

## 8) Tests
- Basic config test exists; extend with runtime smoke checks when CI harness available.

## 9) Change & Decision Log
- 2025-09-02: Initial AGENTS created and integration into bringup behind flag.

