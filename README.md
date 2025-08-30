# ALPHA Rover Stack

> Operator‑first tele‑operation with robust comms, safety, and mapping — autonomy added incrementally (Teach‑&‑Repeat RTH, then Docking).

[![ROS 2](https://img.shields.io/badge/ROS%202-Humble-22314E)](https://docs.ros.org/en/humble/)


[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

---

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Hardware Baseline](#hardware-baseline)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Run \& Observe](#run--observe)
- [Testing](#testing)
- [Security \& OTA](#security--ota)
- [Docs for Agents](#docs-for-agents)
- [Contributing](#contributing)
- [License](#license)
- [Citation \& Acknowledgments](#citation--acknowledgments)

---

## Overview

**ALPHA** is a field‑reliable rover software stack focused on **low‑latency tele‑operation** under constrained bandwidth, with **safety first** and **deterministic mapping**. Autonomy is layered in carefully: **Teach‑\&‑Repeat** return‑to‑home, then **AprilTag‑based docking**.

This repository includes the **roadmap**, **config schemas**, and (as code lands) the **ROS 2 packages** that implement the plan.

- **Roadmap:** [`ALPHA_Software_Roadmap_v2.3.md`](./ALPHA_Software_Roadmap_v2.3.md)
- **Agents docs chain:** see [Docs for Agents](#docs-for-agents)

> **Status:** Active development. The v2.3 roadmap is authoritative for interfaces, topics, and acceptance tests.

---

## Key Features

- **Operator‑first networking:** SLO‑driven degrade ladder protects command latency under 3–8 Mbps.
- **Safety supervisor (RPi):** Independent heartbeat/failsafe; halts within \<300 ms on link pull.
- **Mapping that tells the truth:** NVBlox with **AIRY organized‑cloud row reordering (96×900)** and hardened FOV/range gating.
- **Deterministic startup:** Declarative sequencer — **LiDARs RUN → wait 10 s → start NVBlox**, with visible status.
- **Forensic recording:** Ring buffer + triggered bags with rich metadata for post‑mortems.
- **Config with schemas:** JSON‑schema validation blocks bad YAML before deployment.
- **A/B deployments, signatures, and SROS2:** Safe rollbacks and least‑privilege comms.

---

## Architecture

```
+-------------------+         +----------------+
|   Operator UI     |<------->|  alpha_ui_api  |
+-------------------+         +----------------+
           ^                          ^
           | Status/Events            | Commands (dock, home, lidar_mode)
           v                          v
+-------------------+         +----------------+
|  alpha_observability       |  alpha_mode_manager / orchestrator
|  SLOs, tracing, events     |  modes, degrade, recovery
+-------------------+         +----------------+
           ^                          ^
           | Metrics/Health           | Orchestration
           v                          v
+-------------------+   clouds   +--------------------+
|  alpha_lidar_airy |----------->|    alpha_mapping   |--> NVBlox/Voxblox
|  AIRY OpM 0/1,    |            |  provider plugins  |
|  96x900 reorder   |            +--------------------+
+-------------------+                    ^
           ^                              |
           | Startup sequence (RUN->wait->start)
           v                              |
+-------------------+                     |
|  alpha_bringup    |---------------------+
|  config manager   |
+-------------------+
```

---

## Hardware Baseline

- **Compute:** NVIDIA Jetson Orin (AGX) on Ubuntu 22.04; Raspberry Pi 4/5 as safety supervisor.
- **LiDAR:** 2× RoboSense **AIRY** (front `192.168.1.200`, rear `192.168.1.201`) with MSOP/DIFOP/IMU ports pinned.
- **Cameras:** OAK‑D Pro‑W (front), OAK‑D SR (rear).
- **IMU & power:** 6/9‑axis IMU, INA226 current/voltage monitor.
- **Base:** Differential drive; `/cmd_vel`; hardware e‑stop.

> See the roadmap for full extrinsics and network details.

---

## Repository Layout

```
alpha_ws/src/
  alpha_bringup/          # startup sequencer + config manager + launch
  alpha_lidar_airy/       # AIRY op-mode control, vertical-angle reorder, diagnostics
  alpha_mapping/          # provider interface + NVBlox/Voxblox plugins
  alpha_mode_manager/     # SMACC2 hierarchical modes/overlays
  alpha_observability/    # ros2_tracing, SLO metrics, dashboards
  alpha_orchestrator/     # failure domains & recovery ladder
  alpha_recorder/         # ring buffer + triggered capture + metadata
  alpha_ui_api/           # UI-facing topics/services
  alpha_utils/            # shared msgs/srvs
alpha_configs/            # YAML configs + JSON Schemas
deploy/                   # compose stacks, healthchecks, cosign, A/B
docs/                     # AGENTS chain, style, indices
```

---

## Quick Start

### 1) Prerequisites
- **OS:** Ubuntu 22.04 (Jammy)
- **ROS 2:** Humble Hawksbill (`ros-humble-desktop`, `colcon`)
- **Python:** 3.10
- Optional: **Docker Engine + Compose plugin** (for deploy)

### 2) Clone & build (from source)

```bash
# Clone (adjust for your org/repo)
git clone https://github.com/ORG/REPO.git alpha_rover
cd alpha_rover

# ROS 2 workspace
mkdir -p alpha_ws/src
# alpha_ws is the canonical workspace
# (packages will live under alpha_ws/src as they land)

# Build
cd alpha_ws
colcon build --symlink-install
source install/setup.bash
```

> Jetson builds should use JetPack 6.x and the NVIDIA Container Runtime if running NVBlox in containers.

---

## Configuration

All runtime knobs live in `alpha_configs/` and are **schema‑validated**.

### Network (`network.yaml`)
```yaml
jetson: { nic: eth0, ipv4: 192.168.1.10/24 }
lidar:
  front: { ip: 192.168.1.200, ports: { msop: 6699, difop: 7788, imu: 6688 } }
  rear:  { ip: 192.168.1.201, ports: { msop: 6700, difop: 7789, imu: 6689 } }
```

### LiDAR reorder (`lidar_airy.yaml`)
```yaml
vertical_angle_table_path: /etc/alpha/lidar/airy_vertical_angles.csv
expected_dims: { height: 96, width: 900 }
fov:
  min_angle_below_zero_elevation_rad: -0.001
  max_angle_above_zero_elevation_rad: 1.5707963
range_m: { min: 0.10, max: 60.0 }
```

### Mapping provider (`mapping_provider.yaml`)
```yaml
provider: nvblox
lidar_dims: { height: 96, width: 900 }
fov:
  min_angle_below_zero_elevation_rad: -0.001
  max_angle_above_zero_elevation_rad: 1.5707963
range_m: { min: 0.10, max: 60.0 }
input_topics: [/alpha/lidar/front/points, /alpha/lidar/rear/points]
```

### Startup sequence (`startup_sequence.yaml`)
```yaml
steps:
  - set_lidar_mode: { target: both, op_mode: 1 }   # RUN
  - wait: { seconds: 10 }
  - start_node: { package: alpha_mapping, node: nvblox }
publish_status_topic: /alpha/mapping/startup_status
status_enums: [WAITING_FOR_LIDAR, SPINNING_UP, STARTED]
```

> See the roadmap for extrinsics, SLOs, thermal policy, and bandwidth budgets.

---

## Run & Observe

Once components land, bringup follows:

```bash
# Start startup sequencer (example)
ros2 launch alpha_bringup startup.launch.py

# Verify LiDAR states
ros2 topic echo -n1 /alpha/lidar/state

# Check mapping startup status
ros2 topic echo -n1 /alpha/mapping/startup_status

# Toggle LiDAR modes (server implemented by alpha_lidar_airy)
ros2 service call /alpha/ui/cmd/lidar_mode alpha_utils/srv/SetLidarMode \
  "{target: 'both', op_mode: 1}"
```

**Observability targets (P95):**
- `cmd_latency_ms ≤ 60`
- `map_latency_ms ≤ 90`
- `video_latency_ms ≤ 120`

---

## Testing

Acceptance tests mirror real‑world operations. Examples:

- **Network Addressing:** LiDAR IP/ports reachable.
- **LiDAR Standby at Boot:** Both units report STANDBY in ≤5 s.
- **LiDAR Mode Toggle:** Run↔Standby reflects in ≤1 s.
- **AIRY Row Reorder:** Output is 96×900 sorted by ascending vertical angle.
- **NVBlox Parameter Sanity:** Accepts dims/FOV; drops out‑of‑range points.
- **Startup Sequencer:** NVBlox starts ≥10 s after RUN; status transitions visible.

CI will validate `alpha_configs` against JSON Schemas and run component tests as they land.

---

## Security & OTA

- **A/B deployments** with healthchecks and signed artifacts (cosign).
- **SROS2** policies on critical topics/services.
- **WireGuard** for remote operations.
- **Read‑only rootfs** profiles where feasible.

> Details and acceptance criteria are specified in the roadmap (Phase 14).

---

## Docs for Agents

This repo maintains a **chain of `AGENTS.md` files** so a new agent (human or LLM) can ramp quickly.

- Template: `docs/AGENTS_TEMPLATE.md`
- Style: `docs/AGENTS_STYLE.md`
- Index (generated): `docs/AGENTS_INDEX.md`
- Scripts:
  ```bash
  python3 scripts/agents_validate.py .         # validate front-matter
  python3 scripts/agents_index.py . docs/AGENTS_INDEX.md
  ```

Each component’s `AGENTS.md` includes interfaces, runbooks, observability, tests, and links to code/config.

---

## Contributing

We welcome issues and PRs. Please:
1. Update or add the component’s `AGENTS.md`.
2. Keep `alpha_configs` valid (CI enforces schema checks).
3. Include acceptance tests where possible.
4. Follow ROS 2 package guidelines and keep interfaces consistent with the roadmap.

---

## License

This project is licensed under the **Apache License 2.0**.

See [`LICENSE`](./LICENSE) for the full text. Contributions are accepted under the same license.

---

## Citation & Acknowledgments

- Built on **ROS 2 Humble**, **NVIDIA Isaac ROS**, **NVBlox**, and **OpenCV** ecosystems.
- RoboSense AIRY and Luxonis OAK‑D devices used in hardware validation.
- See `ALPHA_Software_Roadmap_v2.3.md` for references and design decisions.

---

> Safety first: always test on stands before ground runs, keep an e‑stop within reach, and respect power/thermal limits.

---

## Repository-Specific Details

- Default branch: `trunk` (active development). Legacy snapshot: `legacy-2025-08` (available as a worktree at `~/alpha_rover_legacy`).
- Progress log: see `docs/PROGRESS.md` for a running summary of work and next steps.
- Agents index: open `docs/AGENTS_INDEX.md` for a clickable map of all `AGENTS.md` files.

### Quick Start (Repo)
- Dependencies:
  - `sudo apt-get install libyaml-cpp-dev libcurl4-openssl-dev`
- Build:
  - `cd ~/alpha_rover && colcon build --base-paths alpha_ws --merge-install`
  - `source install/setup.bash`
- Launch (dry-run defaults):
  - `ros2 launch alpha_bringup startup.launch.py`
- LiDAR tools:
  - `ros2 run alpha_lidar_airy mode_service_node --ros-args -p network_config:=alpha_configs/network.yaml -p http_enabled:=false`
  - `ros2 run alpha_lidar_airy reorder_node --ros-args -p config:=alpha_configs/lidar_airy.yaml`

### Directory Overview
- `alpha_ws/src/` — core ROS 2 packages (bringup, lidar_airy, mapping, mode_manager, observability, orchestrator, utils).
- `alpha_configs/` — validated YAML configs and example schemas.
- `deploy/` — A/B compose and deployment artifacts (skeleton).
- `docs/` — documentation kit, schema, index, and project progress log.

### Contributing & Conduct
- See `CONTRIBUTING.md` for workflow, branching, and code style.
- See `CODE_OF_CONDUCT.md` for expected behavior and reporting.

