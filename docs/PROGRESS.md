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

### Open Items / Next Session
- Confirm AIRY HTTP endpoints; enable `mode_service_node` with `http_enabled:=true`.
- Ensure LiDAR drivers publish `/alpha/lidar/*/points_raw` or adjust topics accordingly.
- Implement NVBlox provider plugin and mapping launch wiring.
- Add SMACC2 integration for `alpha_mode_manager` (replace skeleton) and recovery logic in `alpha_orchestrator`.
- Expand CI with tests and lint; add config schema validations.

---

Artifacts and decisions are linked from AGENTS docs where relevant.
