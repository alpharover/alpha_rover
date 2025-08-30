---
agent: "alpha_lidar_airy"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_lidar_airy"
  readme: "../alpha_ws/src/alpha_lidar_airy/README.md"
  docs: "../docs"
dependencies:
  internal: ["alpha_utils","alpha_bringup"]
  external: ["RoboSense AIRY HTTP API"]
provides:
  topics_pub:
    - {name: "/alpha/lidar/front/points", type: "sensor_msgs/PointCloud2", rate_hz: 10, description: "reordered 96x900"}
    - {name: "/alpha/lidar/rear/points", type: "sensor_msgs/PointCloud2", rate_hz: 10, description: "reordered 96x900"}
    - {name: "/alpha/lidar/state", type: "alpha_utils/LidarState[]", rate_hz: 2, description: "front/rear state"}
  topics_sub: []
  services:
    - {name: "/alpha/ui/cmd/lidar_mode", type: "alpha_utils/SetLidarMode", direction: "server"}
  actions: []
configs:
  - "../alpha_configs/lidar_airy.yaml"
  - "../alpha_configs/network.yaml"
runbooks:
  start: |
    # Start reorder + telemetry
    ros2 run alpha_lidar_airy reorder_node --ros-args -p config:=alpha_configs/lidar_airy.yaml
  stop: |
    # terminate the node process
    pkill -f alpha_lidar_airy || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/lidar/state
    ros2 topic hz /alpha/lidar/front/points
observability:
  slo:
    - {name: "reorder_latency_ms_p95", target: 10}
  metrics:
    - {name: "angle_table_hash", source: "log", note: "provenance"}
security:
  sros2_policies: ["deny-all-except: /alpha/lidar/*"]
  secrets: []
lifecycle:
  states: ["INIT","RUNNING","FAILED"]
  transitions: ["INIT->RUNNING: config valid; RUNNING->FAILED: reorder error"]
failure_modes:
  - {id: "LA-01", symptom: "No points published", detection: "topic stale", recovery: "restart node; verify MSOP port"}
  - {id: "LA-02", symptom: "Wrong geometry", detection: "test pattern mismatch", recovery: "verify vertical_angle_table_path; hash mismatch"}
tests:
  acceptance:
    - {id: "ROW-ORDER", description: "Rows sorted by ascending vertical angle", pass_criteria: "dim=96x900; known pattern matches"}
    - {id: "STATE-PUB", description: "Publishes LidarState", pass_criteria: "front/rear present with op_mode and ready"}
  ci_jobs:
    - {id: "lidar-unit", description: "Row reorder unit tests"}
notes: >
  Provides AIRY HTTP op-mode handling (OpM 0/1) and organized-cloud row reordering.
---

# AGENT — alpha_lidar_airy

## 1) Mission & Context
Owns LiDAR-specific quirks: toggling RoboSense AIRY op modes (Standby/Run) and reordering organized point clouds to match NVBlox expectations.

## 2) Responsibilities & Boundaries
- Must: expose `/alpha/ui/cmd/lidar_mode`, publish `/alpha/lidar/state`, and output 96×900 reordered clouds.
- Not: manage mapping or network; those live elsewhere.

## 3) Interfaces
### Topics (publish)
| Name | Type | Rate | Notes |
|---|---|---:|---|
| /alpha/lidar/front/points | sensor_msgs/PointCloud2 | 10–20 | reordered 96×900 |
| /alpha/lidar/rear/points  | sensor_msgs/PointCloud2 | 10–20 | reordered 96×900 |
| /alpha/lidar/state        | alpha_utils/LidarState[] | 1–2  | op_mode + ready |

### Topics (subscribe)
| Name | Type | Notes |
|---|---|---|
| (none) | | |

### Services / Actions
| Name | Type | Direction | Notes |
|---|---|---|---|
| /alpha/ui/cmd/lidar_mode | alpha_utils/SetLidarMode | server | OpM=0/1 http calls |

### Parameters & Config Keys
- `vertical_angle_table_path` (CSV), `expected_dims.height=96`, `expected_dims.width=900`, `range_m.min=0.10`, `range_m.max=60.0`

## 4) Runbooks
### Start
```bash
ros2 run alpha_lidar_airy reorder_node --ros-args -p config:=alpha_configs/lidar_airy.yaml
```
### Stop
```bash
pkill -f alpha_lidar_airy || true
```
### Healthcheck
```bash
ros2 topic echo -n1 /alpha/lidar/state
ros2 topic hz /alpha/lidar/front/points
```

## 5) Observability
- Metric: `angle_table_hash`
- Alerts: Missing/invalid table; dimension mismatch

## 6) Failure Modes & Recovery
- LA-01: No points → check MSOP port, restart node
- LA-02: Wrong geometry → verify angle table path and hash

## 7) Security
- SROS2 profile restricts to `/alpha/lidar/*`

## 8) Tests
- See acceptance entries above.

## 9) Change & Decision Log
- TBD
