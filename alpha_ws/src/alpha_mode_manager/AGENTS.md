---
agent: "alpha_mode_manager"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_mode_manager"
  docs: "../../docs"
dependencies:
  internal: ["alpha_utils"]
  external: []
provides:
  topics_pub:
    - {name: "/alpha/mode/state", type: "alpha_utils/ModeState", rate_hz: 1, description: "current base mode + overlays"}
  topics_sub: []
  services:
    - {name: "/alpha/mode/set", type: "alpha_utils/ModeSet", direction: "server"}
  actions: []
configs: []
runbooks:
  start: |
    ros2 run alpha_mode_manager mode_manager
  stop: |
    pkill -f alpha_mode_manager || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/mode/state
observability:
  slo: []
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["TELEOP","FAILSAFE","DOCKING","RTH_TOPO"]
  transitions: []
failure_modes: []
tests:
  acceptance: []
  ci_jobs: []
notes: >
  Skeleton mode manager providing ModeSet service and state publisher; SMACC2 integration to follow.
---

