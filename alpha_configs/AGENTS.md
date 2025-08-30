---
agent: "alpha_configs"
component_type: "config"
status: "alpha"
version: "v2.3"
updated: "2025-08-30"
owner: "Alpha SW"
links:
  roadmap: "../ALPHA_Software_Roadmap_v2.3.md"
  code: "../alpha_configs"
  readme: "../alpha_configs/README.md"
  docs: "../docs"
dependencies:
  internal: []
  external: []
provides:
  topics_pub: []
  topics_sub: []
  services: []
  actions: []
configs:
  - "../alpha_configs/network.yaml"
  - "../alpha_configs/lidar_airy.yaml"
  - "../alpha_configs/extrinsics_seed.yaml"
  - "../alpha_configs/mapping_provider.yaml"
  - "../alpha_configs/startup_sequence.yaml"
runbooks:
  start: |
    # Configs are loaded by alpha_bringup's Config Manager
  stop: |
    # N/A
  healthcheck: |
    ros2 service call /alpha/config/get alpha_utils/srv/GetConfig '{key: "network"}'
observability:
  slo: []
  metrics: []
security:
  sros2_policies: []
  secrets: ["/var/lib/alpha/secrets/*"]
lifecycle:
  states: ["VALID","INVALID"]
  transitions: ["INVALID->VALID: schema pass"]
failure_modes:
  - {id: "CFG-01", symptom: "Schema validation fails", detection: "CI job fails", recovery: "fix YAML to schema"}
tests:
  acceptance:
    - {id: "SCHEMA", description: "Schemas validate all YAMLs", pass_criteria: "CI green"}
  ci_jobs:
    - {id: "validate-configs", description: "Run schema validation on PR"}
notes: >
  Single source of truth for runtime parameters and hardware addresses.
---

# AGENT — alpha_configs

## 1) Mission & Context
Holds all top-level YAML files and JSON Schemas. CI enforces validity.
