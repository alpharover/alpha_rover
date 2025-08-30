---
agent: "alpha_mapping"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_mapping"
  docs: "../../docs"
dependencies:
  internal: ["alpha_utils"]
  external: ["pluginlib"]
provides:
  topics_pub: []
  topics_sub: []
  services: []
  actions: []
configs:
  - "../../alpha_configs/mapping_provider.yaml"
runbooks:
  start: |
    # Provider plugins to be implemented (Nvblox/Voxblox)
  stop: |
    # N/A
  healthcheck: |
    # N/A
observability:
  slo: []
security:
  sros2_policies: []
  secrets: []
lifecycle:
  states: ["INIT","RUNNING","FAILED"]
  transitions: []
failure_modes: []
tests:
  acceptance: []
  ci_jobs: []
notes: >
  Defines the mapping provider interface header and will host plugins for NVBlox/Voxblox.
---
