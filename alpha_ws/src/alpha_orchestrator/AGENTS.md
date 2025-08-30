---
agent: "alpha_orchestrator"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_orchestrator"
  docs: "../../docs"
dependencies:
  internal: ["alpha_utils"]
  external: []
provides:
  topics_pub:
    - {name: "/alpha/events", type: "alpha_utils/Event", rate_hz: 1, description: "system events"}
  topics_sub: []
  services:
    - {name: "/alpha/orchestrator/cmd", type: "alpha_utils/OrchestratorCommand", direction: "server"}
  actions: []
configs: []
runbooks:
  start: |
    ros2 run alpha_orchestrator orchestrator
  stop: |
    pkill -f alpha_orchestrator || true
  healthcheck: |
    ros2 topic echo -n1 /alpha/events
observability:
  slo: []
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["RUNNING"]
  transitions: []
failure_modes: []
tests:
  acceptance: []
  ci_jobs: []
notes: >
  Skeleton orchestrator: accepts high-level commands and emits Event messages; integrates recovery later.
---

