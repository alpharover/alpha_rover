---
agent: "<component name, e.g., alpha_lidar_airy>"
component_type: "ros2_package"  # one of: ros2_package | config | deploy | docs | tooling
status: "draft"                 # draft | alpha | beta | stable | deprecated
version: "v0.1"
updated: "YYYY-MM-DD"
owner: "name_or_team"
links:
  roadmap: "../ALPHA_Software_Roadmap_v2.3.md"
  code: "<relative path to package or config>"
  readme: "<relative path to README.md>"
  docs: "<relative path to extra docs>"
dependencies:
  internal: []                  # e.g., [alpha_utils, alpha_bringup]
  external: []                  # e.g., [isaac_ros_nvblox, linuxptp]
provides:
  topics_pub:                   # topics this component PUBLISHES
    - {name: "", type: "", rate_hz: 0, description: ""}
  topics_sub:                   # topics this component SUBSCRIBES to
    - {name: "", type: "", description: ""}
  services:
    - {name: "", type: "", direction: "server|client"}
  actions: []
configs:
  - "<relative path to config yaml>"
runbooks:
  start: |
    # exact commands to start (deterministic, copy/paste-ready)
  stop: |
    # exact commands to stop
  healthcheck: |
    # quick commands to verify health
observability:
  slo:
    - {name: "cmd_latency_p95_ms", target: 60}
  metrics:
    - {name: "", source: "topic|log|trace", note: ""}
  logs:
    - {source: "", grep: ""}
security:
  sros2_policies: []
  secrets: []                   # paths or key names if any
lifecycle:
  states: ["INIT","RUNNING","DEGRADED","FAILED","SHUTDOWN"]
  transitions: []
failure_modes:
  - {id: "F1", symptom: "", detection: "", recovery: ""}
tests:
  acceptance:
    - {id: "", description: "", pass_criteria: ""}
  ci_jobs:
    - {id: "", description: ""}
notes: >
  Free-form context. Keep short.
---

# AGENT — <component name>

## 1) Mission & Context
One paragraph on what this component does and *why it exists*. Reference the roadmap link above when relevant.

## 2) Responsibilities & Boundaries
- What this component **must** do.
- What it **explicitly does not** do.

## 3) Interfaces
### Topics (publish)
| Name | Type | Rate | Notes |
|---|---|---:|---|

### Topics (subscribe)
| Name | Type | Notes |
|---|---|---|

### Services / Actions
| Name | Type | Direction | Notes |
|---|---|---|---|

### Parameters & Config Keys
List important parameters and the config YAMLs that set them.

## 4) Runbooks
### Start
Exact commands.

### Stop
Exact commands.

### Healthcheck
Minimal commands to confirm it's working (one minute or less).

## 5) Observability
- SLOs and how they’re measured.
- Key metrics and where to find them (topics, traces, logs).
- Example `ros2` commands for quick inspection.

## 6) Failure Modes & Recovery
Enumerate likely failures, how they’re detected, and the automatic/manual recovery steps.

## 7) Security
- SROS2 policies/keystores in effect.
- Any secrets and how they’re provisioned.

## 8) Tests
- Acceptance tests tying back to the roadmap.
- CI jobs names and how to run locally.

## 9) Change & Decision Log
- Link to ADRs / PRs that changed behavior.
