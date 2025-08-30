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

- alpha_lidar_airy:
  - Added Python package with two nodes:
    - `mode_service_node`: serves `/alpha/ui/cmd/lidar_mode` (dry-run or HTTP). Publishes `/alpha/lidar/state` at 2 Hz.
    - `reorder_node`: skeleton pass-through for now; subscribes to `/alpha/lidar/*/points_raw`, republishes to `/alpha/lidar/*/points`; logs angle table SHA if present.
  - Updated `alpha_configs/lidar_airy.yaml` to include HTTP endpoint stubs (`http.endpoints.run/standby`).
  - Added `alpha_configs/airy_vertical_angles.csv` to repo and pointed config at it; reorder resolves relative to config dir.
  - Launch wiring already present; parameters `http_enabled` and `http_timeout_sec` supported.

- alpha_mapping:
  - Added minimal C++ `nvblox` dummy node subscribing to `/alpha/lidar/{front,rear}/points` to scaffold provider wiring.
  - Build target: `alpha_mapping:nvblox`. Not auto-started; keep startup sequencing policy for later.

### Open Items / Next Session
- Confirm AIRY HTTP endpoints with device manual; then set `http_enabled:=true` in launch. Update `http.endpoints.*` if paths/methods differ.
- Ensure LiDAR drivers publish `/alpha/lidar/*/points_raw` (or update reorder inputs) and validate dims=96x900.
- Implemented full row reorder + range gate in `reorder_node` (row-block reorder by ascending vertical angle; out-of-range points set to NaN). Added topic parameters for raw inputs.
- Implement NVBlox provider plugin and mapping launch wiring.
- Add SMACC2 integration for `alpha_mode_manager` (replace skeleton) and recovery logic in `alpha_orchestrator`.
- Expand CI with tests and lint; add config schema validations.

---

Artifacts and decisions are linked from AGENTS docs where relevant.
