---
agent: "alpha_lidar_airy_cpp"
component_type: "ros2_package"
status: "beta"
version: "v0.1"
updated: "2025-08-31"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_lidar_airy_cpp"
  readme: "../alpha_ws/src/alpha_lidar_airy_cpp/README.md"
  docs: "../../docs"
dependencies:
  internal: ["alpha_lidar_airy"]
  external: ["rclcpp","sensor_msgs","diagnostic_msgs","yaml-cpp"]
provides:
  topics_pub:
    - {name: "/alpha/lidar/front/points", type: "sensor_msgs/PointCloud2", rate_hz: 10, description: "reordered 96x900 (SensorDataQoS)"}
    - {name: "/alpha/lidar/rear/points", type: "sensor_msgs/PointCloud2", rate_hz: 10, description: "reordered 96x900 (SensorDataQoS)"}
  topics_sub:
    - {name: "/alpha/lidar/front/points_raw", type: "sensor_msgs/PointCloud2"}
    - {name: "/alpha/lidar/rear/points_raw", type: "sensor_msgs/PointCloud2"}
  services: []
  actions: []
configs:
  - "../../alpha_configs/lidar_airy.yaml"
runbooks:
  start: |
    # Launch C++ reorder backend
    ros2 launch alpha_lidar_airy airy_bringup.launch.py backend:=cpp start_mode_service:=false
  stop: |
    # terminate processes
    pkill -f reorder_node_cpp || true
  healthcheck: |
    ros2 topic hz /alpha/lidar/front/points -w 30
observability:
  slo:
    - {name: "points_rate_hz_p95", target: 9.0}
    - {name: "relative_skew_ms_p95", target: 12}
  metrics:
    - {name: "reorder_backend", source: "/diagnostics", note: "cpp"}
    - {name: "reorder_latency_ms.{front,rear}.p50|p95", source: "/diagnostics"}
    - {name: "points_rate_hz.{front,rear}", source: "/diagnostics"}
security:
  sros2_policies: ["deny-all-except: /alpha/lidar/*"]
  secrets: []
lifecycle:
  states: ["INIT","RUNNING","FAILED"]
  transitions: ["INIT->RUNNING: config valid; RUNNING->FAILED: reorder error"]
failure_modes:
  - {id: "LA-CPP-01", symptom: "No points published", detection: "topic stale", recovery: "verify config + angle table"}
tests:
  acceptance:
    - {id: "REL-SKEW", description: "Relative skew vs raw post warm-up", pass_criteria: "P95 ≤ 12 ms"}
    - {id: "DIMS", description: "Dims exactly 96×900", pass_criteria: "pad/truncate if needed; warn"}
  ci_jobs:
    - {id: "build-cpp", description: "Build alpha_lidar_airy_cpp"}
notes: >
  High-performance rclcpp implementation of the AIRY row reorder.

## Mission & Context
Provide a low-latency reorder stage to meet ≥9 Hz at ≤1.0 CPU core.

## Responsibilities & Boundaries
- Must: subscribe to raw organized clouds, reorder rows by vertical angle, normalize to 96×900, publish with SensorData QoS.
- Not: op-mode HTTP control (lives in alpha_lidar_airy Python package).

## Interfaces
- Topics (subscribe): `/alpha/lidar/front/points_raw`, `/alpha/lidar/rear/points_raw` (sensor_msgs/PointCloud2)
- Topics (publish): `/alpha/lidar/front/points`, `/alpha/lidar/rear/points` (sensor_msgs/PointCloud2)
- Parameters: `config` (path), `input_front_topic`, `input_rear_topic`, `timestamp_policy` (sensor|node)

## Runbooks
See start/stop/healthcheck above.

## Observability
Publishes diagnostics at `/diagnostics` under `alpha_lidar_airy/reorder`.

## Failure Modes & Recovery
- LA-CPP-01: No output → check driver, config path, angle table path.

## Security
None

## Tests
Use `alpha_testing/lidar_accept` with relative skew mode.

## Change & Decision Log
- 2025-08-31: Initial C++ backend added; launch `backend:=cpp` supported.
---

