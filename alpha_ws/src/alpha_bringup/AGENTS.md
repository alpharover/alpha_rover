---
agent: "alpha_bringup"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
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
  topics_sub: []
  services: []
  actions: []
configs:
  - "../alpha_configs/startup_sequence.yaml"
runbooks:
  start: |
    # Start config manager (serves /alpha/config/get)
    ros2 run alpha_bringup config_manager --ros-args -p config_dir:=alpha_configs
    # In a separate terminal, run the startup sequencer (dry-run by default)
    ros2 run alpha_bringup startup_sequencer --ros-args -p sequence_config:=alpha_configs/startup_sequence.yaml -p dry_run:=true
  stop: |
    pkill -f alpha_bringup || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/mapping/startup_status
observability:
  slo:
    - {name: "startup_sequence_ms_p95", target: 12000}
  metrics:
    - {name: "sequence_step", source: "log", note: ""}
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
  Owns the startup sequencer and config manager; sets LiDARs to RUN, waits 10s, starts mapping.
---

# AGENT — alpha_bringup

## 1) Mission & Context
Sequences the system startup and manages validated configuration loading.

## 2) Responsibilities & Boundaries
- Must: publish startup status, enforce sequence, block on invalid configs.
- Not: own mapping internals or LiDAR geometry.
