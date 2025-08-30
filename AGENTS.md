---
agent: "alpha_project_root"
component_type: "docs"
status: "alpha"
version: "v2.3"
updated: "2025-08-30"
owner: "Tim"
links:
  roadmap: "./ALPHA_Software_Roadmap_v2.3.md"
  code: "./alpha_ws/src"
  readme: "./README.md"
  docs: "./docs"
  progress: "./docs/PROGRESS.md"
dependencies:
  internal: ["alpha_utils","alpha_bringup","alpha_lidar_airy","alpha_mapping","alpha_observability","alpha_ui_api"]
  external: ["isaac_ros_nvblox","isaac_ros_apriltag","ros2_tracing","linuxptp"]
provides:
  topics_pub: []
  topics_sub: []
  services: []
  actions: []
configs:
  - "./alpha_configs"
runbooks:
  start: |
    # See per-component runbooks. This root doc indexes the project.
  stop: |
    # See per-component runbooks.
  healthcheck: |
    ros2 topic list
observability:
  slo:
    - {name: "cmd_latency_p95_ms", target: 60}
    - {name: "map_latency_p95_ms", target: 90}
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["INIT","RUNNING","DEGRADED","FAILED","SHUTDOWN"]
  transitions: []
failure_modes: []
tests:
  acceptance:
    - {id: "NET-ADDR", description: "LiDAR IPs reachable; MSOP ports open", pass_criteria: "ping + netcat OK"}
  ci_jobs:
    - {id: "agents-validate", description: "Validate AGENTS front-matter schema"}
notes: >
  Start here. Use docs/AGENTS_INDEX.md to navigate per-component docs.

## Change & Decision Log
- 2025-08-30: Created trunk baseline and legacy branch/worktree. Scaffolding added for utils, bringup, LiDAR (C++), mapping skeleton, observability, mode manager, orchestrator; CI enabled; bringup launch added.
---

# ALPHA Project — AGENTS Overview

This file anchors the "chain of agents" documentation set. See `docs/AGENTS_INDEX.md` for the generated index of all components.
