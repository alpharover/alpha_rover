---
agent: "alpha_bringup"
component_type: "ros2_package"
status: "draft"
version: "v0.2"
updated: "2025-08-31"
owner: "Alpha SW"
links:
  roadmap: "../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_bringup"
  readme: "../alpha_ws/src/alpha_bringup/README.md"
  docs: "../docs"
dependencies:
  internal: ["alpha_utils","alpha_mapping","alpha_lidar_airy"]
  external: []
provides:
  topics_pub:
    - {name: "/alpha/mapping/startup_status", type: "std_msgs/String", rate_hz: 1, description: "WAITING_FOR_LIDAR|SPINNING_UP|STARTED"}
    - {name: "/alpha/gates/lidar_ready", type: "std_msgs/Bool", rate_hz: 2, description: "durable gate: true after 10s + ≥9Hz per LiDAR (3s window)"}
  topics_sub: []
  services: []
  actions: []
configs:
  - "../alpha_configs/startup_sequence.yaml"
runbooks:
  start: |
    # Launch bringup (includes config manager, startup sequencer, LiDAR ready gate)
    ros2 launch alpha_bringup startup.launch.py
  stop: |
    pkill -f alpha_bringup || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/mapping/startup_status
observability:
  slo:
    - {name: "startup_sequence_ms_p95", target: 12000}
  metrics:
    - {name: "sequence_step", source: "log", note: ""}
    - {name: "lidar_ready_gate_state", source: "/alpha/gates/lidar_ready", note: "Bool (durable)"}
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["INIT","WAITING_FOR_LIDAR","SPINNING_UP","STARTED","FAILED"]
  transitions: ["INIT->WAITING_FOR_LIDAR","WAITING_FOR_LIDAR->SPINNING_UP","SPINNING_UP->STARTED"]
failure_modes:
  - {id: "BR-01", symptom: "Never reaches STARTED", detection: "status stuck", recovery: "verify LiDAR op-mode, increase wait"}
tests:
  acceptance:
    - {id: "SEQ-10S", description: "NVBlox starts >=10s after LiDAR RUN", pass_criteria: "status transitions correct"}
  ci_jobs:
    - {id: "bringup-sim", description: "Sim runs through sequence"}
notes: >
  Owns the startup sequencer, config manager, and LiDAR ready gate. Gate publishes true only
  after a 10s warm-up and both `/alpha/lidar/{front,rear}/points` rates ≥ 9 Hz over a 3s window.

## Change & Decision Log
- 2025-08-30: Added config_manager and startup_sequencer nodes; added startup.launch.py.
---

# AGENT — alpha_bringup

## 1) Mission & Context
Sequences the system startup and manages validated configuration loading.

## 2) Responsibilities & Boundaries
- Must: publish startup status, enforce sequence, block on invalid configs.
- Not: own mapping internals or LiDAR geometry.
