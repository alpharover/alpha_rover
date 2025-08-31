---
agent: "alpha_testing"
component_type: "ros2_package"
status: "draft"
version: "v0.1"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_ws/src/alpha_testing"
  docs: "../docs"
dependencies:
  internal: []
  external: []
provides:
  topics_pub: []
  topics_sub: []
  services: []
  actions: []
configs: []
runbooks:
  start: |
    ros2 run alpha_testing lidar_accept
  stop: |
    true
  healthcheck: |
    ros2 run alpha_testing lidar_accept || echo "LiDAR acceptance failed"
observability:
  slo: []
security:
  sros2_policies: []
  secrets: []
---
lifecycle:
  states: ["MANUAL"]
  transitions: []
failure_modes: []
tests:
  acceptance:
    - {id: "LIDAR-ACCEPT", description: "Dims=96×900; skew ≤20ms", pass_criteria: "script returns 0"}
  ci_jobs: []
notes: >
  Runtime acceptance checks, run on-device against live topics.

# AGENT — alpha_testing

## LiDAR Acceptance
Passes when both front and rear LiDAR publish 96×900 PointCloud2 with header skew ≤ 20 ms.
