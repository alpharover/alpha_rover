# Project Progress Log

This running log captures progress and decisions to help resume quickly.

## 2025-08-30
- Repo baseline prepared:
  - Created `trunk` empty baseline and `legacy-2025-08` worktree + tag `legacy-pre-arch-2025-08`.
  - Home cleanup: established `alpha_ws` as the canonical workspace.
- Scaffolding:
  - Added agents doc kit; seeded AGENTS; wired index + validation.
  - Added `alpha_utils` (msgs/srvs) and `alpha_bringup` (config manager + startup sequencer).
  - Added `alpha_lidar_airy` (C++): `reorder_node`, `mode_service_node` (dry-run by default).
  - Added `alpha_mapping` skeleton with provider interface header.
  - Added `alpha_observability` SLO publisher (placeholder).
  - Added `alpha_mode_manager` and `alpha_orchestrator` skeleton nodes.
  - Added `alpha_configs` YAMLs per roadmap; `deploy/` skeleton.
  - CI: GitHub Actions for docs validation + ROS 2 Humble build.
- Launch:
  - `alpha_bringup/launch/startup.launch.py` starts config manager, sequencer, lidar nodes, mode manager, orchestrator.
  - Added time sync preflight gate and SLO publisher to launch.
  - Added comms degrade manager to launch.

- alpha_lidar_airy:
  - Added Python package with two nodes:
    - `mode_service_node`: serves `/alpha/ui/cmd/lidar_mode` (dry-run or HTTP). Publishes `/alpha/lidar/state` at 2 Hz.
    - `reorder_node`: skeleton pass-through for now; subscribes to `/alpha/lidar/*/points_raw`, republishes to `/alpha/lidar/*/points`; logs angle table SHA if present.
  - Updated `alpha_configs/lidar_airy.yaml` to include HTTP endpoint stubs (`http.endpoints.run/standby`).
  - Added `alpha_configs/airy_vertical_angles.csv` to repo and pointed config at it; reorder resolves relative to config dir.
  - Launch wiring already present; parameters `http_enabled` and `http_timeout_sec` supported.

- alpha_mapping:
  - Added minimal C++ `nvblox` dummy node subscribing to `/alpha/lidar/{front,rear}/points` to scaffold provider wiring.
  - Added `mapping_node` that reads `mapping_provider.yaml`, subscribes to configured LiDAR topics, and routes clouds to a dummy provider (implements `IMappingProvider`).
  - Startup sequence now launches `alpha_mapping mapping_node` after LiDAR spin-up.
  - Added pluginlib-based provider loading; implemented placeholder `NvbloxProvider` plugin and description. `mapping_node` tries `alpha_mapping/NvbloxProvider` then falls back to Dummy.
  - Build targets: `alpha_mapping:nvblox`, `alpha_mapping:mapping_node`, `alpha_mapping:nvblox_provider`.

- alpha_mode_manager:
  - Upgraded Python node to read `alpha_configs/modes.yaml` (base mode, overlays, exclusive list).
  - Added guard checks for entering `MAPPING` overlay via `/alpha/time_sync/preflight_gate` and `/alpha_calibration_tools/tf_ok` (std_srvs/Trigger), controlled by `enforce_guards`.
  - Clears overlays on exclusive base modes (`FAILSAFE`, `DOCKING`, `RTH_TOPO`). Publishes state every second and immediately on change.
  - Launch now passes `modes_config` and `enforce_guards`.

- Config validation:
  - ConfigManager validates YAMLs against JSON Schemas when present (added schemas for `lidar_airy`, `network`, `modes`).
  - Added schema for `mapping_provider.yaml`.
  - Added schema for `failure_domains.yaml` and `time_sync.yaml`.
  - Added schema for `degrade_policies.yaml`.

### Open Items / Next Session
- Confirm AIRY HTTP endpoints with device manual; then set `http_enabled:=true` in launch. Update `http.endpoints.*` if paths/methods differ.
- Ensure LiDAR drivers publish `/alpha/lidar/*/points_raw` (or update reorder inputs) and validate dims=96x900.
- Implemented full row reorder + range gate in `reorder_node` (row-block reorder by ascending vertical angle; out-of-range points set to NaN). Added topic parameters for raw inputs.
- Implement NVBlox provider plugin and mapping launch wiring.
- Add SMACC2 integration for `alpha_mode_manager` (replace skeleton) and recovery logic in `alpha_orchestrator`.
- Expand CI with tests and lint; add config schema validations.

## 2025-08-30 (cont.)
- Orchestrator:
  - Reads `alpha_configs/failure_domains.yaml`; subscribes to `/alpha/health` and emits `DOMAIN_HEALTH` events on changes.
  - Handles `/alpha/orchestrator/cmd` actions `e_stop`, `resume`, `recover_perception`.
  - Executes config-driven recovery lists (e.g., `perception.recovery.vslam_lost`); issues ModeSet to `FAILSAFE` when specified (dry-run by default), other actions reported via events.
  - Launch now passes `config_failure_domains` and `dry_run`.
  - Subscribes to `/alpha/comms/degrade_level`; maps L0→OK, L1/L2→DEGRADED, L3→FAILED for `comms` and publishes `/alpha/health` snapshots.
- Config validation: added schema for `failure_domains.yaml`.
- Observability:
  - Implemented `alpha_observability/slo_publisher`: subscribes to `/alpha/metrics/*_latency_ms`, computes P95, publishes `DiagnosticArray` to `/alpha/observability/slo`, and emits `SLO_BREACH` events against thresholds in `degrade_policies.yaml`.
  - Added `alpha_observability/latency_feeders` for placeholder latency metrics; configurable sources.
- Time Sync:
  - Added `alpha_time_sync` preflight gate node exposing `/alpha/time_sync/preflight_gate` and `/alpha/time_sync/status` (skeleton, `always_ok` param).
- Comms/Degrade:
  - Added `alpha_comms/degrade_manager`: listens to SLO metrics, escalates/de-escalates through L0→L3, publishes `/alpha/comms/degrade_level`, emits events, and disables MAPPING overlay when level requires it (dry-run by default).
  - Publishes `/alpha/comms/budget_intent` (DegradeBudget) with `video_fps`, `video_bitrate`, `lidar_hz`, `mapping`. Video budget applier publishes `/alpha/video/target_*`. LiDAR reorder subscribes and throttles output to target Hz.

---

Artifacts and decisions are linked from AGENTS docs where relevant.

- Recorder:
  - Added `alpha_recorder/ring_recorder`: manages rotating rosbag2 ring (`--max-bag-duration`), trims to retention window, serves `/alpha/recorder/trigger` to gather pre-window segments and capture post-window into a new bag dir under `data/triggers/`.
  - Status on `/alpha/recorder/status`.

## 2025-09-01
- CI now builds/tests all packages and adds a `tf_ok` enforcement unit test (roadmap 10.6 — Calibration tools + TF preflight/CI).
- Added `alpha_configs/extrinsics_current.yaml` for calibration (roadmap 7.13 — extrinsics_seed.yaml).
- Integrated `video_controller` and wired into launch (roadmap 10.3 — Comms Manager + budgets + impairment harness in CI).
