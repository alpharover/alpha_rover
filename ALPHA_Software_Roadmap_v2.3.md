# ALPHA Software Roadmap — **v2.3**
**Updated:** 2025-08-30


---

# PART I — Project Context & Reference (from v1, consolidated)

## 0. Scope & Objectives
- **Primary goal:** Field‑reliable, operator‑first tele‑op rover with robust comms, safety, and mapping; autonomy added incrementally (Teach‑&‑Repeat RTH, then Docking).
- **Non‑goals (v2.1):** Full semantic autonomy, multi‑robot coordination, cloud‑dependent control.
- **Success criteria:** Low‑latency tele‑op under constrained bandwidth, graceful degrade, safe failure, reproducible mapping, deterministic tests, and searchable datasets.

## 0.1 Reference Platform (Baseline)
- **Compute:** NVIDIA Jetson Orin (AGX 64gb) running Ubuntu 22.04 + ROS 2 (Humble) in containers; **Raspberry Pi (4/5)** as **Safety Supervisor** & hardware I/O.
- **Networking:** Wired Jetson↔RPi (preferred) + Wi‑Fi/LTE uplink; WireGuard for remote ops.
- **Sensors:**
  - **LiDAR:** 2× RoboSense **AIRY** (front/rear).
  - **Camera:** OAK‑D Pro-W (RGB‑D, mounted on front of rover) for operator video + AprilTag docking; OAK-D-SR mounted on rear of rover (Depth Only)
  - **IMU:** 6‑ or 9‑axis (for deskew + tilt safety).
  - **Power:** INA226 current/voltage.
- **Base:** Differential drive; motor controller with `/cmd_vel` interface; hardware e‑stop.
- **Time:** PTP (linuxptp) between Jetson/RPi; capture‑time stamps at drivers.

### 0.1.1 Network addressing (initial)

```yaml
network:
  jetson:
    nic: eth0
    ipv4: 192.168.1.10/24
  lidar:
    front:
      ip: 192.168.1.200
      ports: { msop: 6699, difop: 7788, imu: 6688 }
    rear:
      ip: 192.168.1.201
      ports: { msop: 6700, difop: 7789, imu: 6689 }
```

### 0.1.2 Initial extrinsics (URDF seed)

```yaml
frames:
  base_to_lidar_front:
    translation_m: [0.110367, 0.0, 0.037388]
    rpy_rad: [1.5707963, 0.0, 1.5707963]
  base_to_lidar_rear:
    translation_m: [-0.203071, 0.0, 0.061300]
    rpy_rad: [0.0, 0.0, 1.5707963]
  base_to_oakd_pro_optical:
    translation_m: [0.148469, 0.0, 0.097926]
    rpy_rad: [-1.8325957, 0.0, -1.5707963]
  base_to_oakd_sr_optical:
    translation_m: [-0.211326, 0.0, 0.023959]
    rpy_rad: [-1.6580628, 0.0, 1.5707963]
```

## 0.2 External Packages & Dependencies
- **NVIDIA Isaac ROS:** NITROS transport, **isaac_ros_nvblox** (TSDF/ESDF), **isaac_ros_apriltag**, image pipeline, NVENC/H.264/H.265 encoder, **isaac_ros_visualSLAM**
- **Mapping fallback:** **Voxblox** (CPU).
- **Tracing/metrics:** ros2_tracing (LTTng), Prometheus or Foxglove.
- **Security/OTA:** Docker/Compose, cosign, syft/grype, SROS2, WireGuard.
- **Testing:** Gazebo/Isaac Sim (as available), tc/netem impairment harness, rosbag HIL.

> **Pin exact versions/digests** in `deploy/lockfiles/` to avoid surprise upgrades.

## 0.3 Sensor I/O — Raw Topics (canonical)
| Sensor | Topic | Msg type | Rate | Notes |
|---|---|---:|---|---|
| Front LiDAR | `/alpha/lidar/front/points` | `sensor_msgs/PointCloud2` | 10–20 Hz | Organized cloud if available; deskew optional |
| Rear LiDAR | `/alpha/lidar/rear/points`  | `sensor_msgs/PointCloud2` | 10–20 Hz | Same as above |
| RGB camera | `/alpha/cam/front/image_color` | `sensor_msgs/Image` | 15–30 Hz | Encoded to H.264/265 for UI stream |
| IMU | `/alpha/imu/data` | `sensor_msgs/Imu` | 100–200 Hz | Tilt safety + deskew |
| Wheel odom | `/alpha/odom` | `nav_msgs/Odometry` | 30–50 Hz | Diff‑drive odometry |
| Power | `/alpha/power/ina226` | custom `alpha_utils/Power` | 5–10 Hz | Current, voltage |
| Temps | `/alpha/thermal/jetson`, `/alpha/thermal/rpi` | `sensor_msgs/Temperature` | 1–2 Hz | Thermal policy input |

## 0.4 LiDAR→NVBlox Integration (principle & policy)
- **Never concatenate** LiDARs before NVBlox. Publish each cloud separately (distinct `frame_id`s) to the **same NVBlox input topic**. NVBlox fuses via TF + timestamps.
- **Requirements:** PTP skew < 5 ms; correct TF extrinsics; optional constant‑velocity deskew pre‑NVBlox.
- **Pre‑filters:** Per‑LiDAR throttle + voxel downsample; drop on health faults; auto‑pause mapping when TF/time gates fail.
- **AIRY organized cloud reorder:** Raw `sensor_msgs/PointCloud2` arrives as **96×900** "organized" frames from each AIRY. Before NVBlox, rows must be reordered by **vertical ring angle** using a parsed **vertical‑angle table**; sort rows ascending by angle and copy data to match the new order. Log a stable hash of the angle table for traceability.
- **NVBlox expectations (LiDAR):** `lidar_height=96`, `lidar_width=900`, **non‑equal vertical FOV** with `min_angle_below_zero_elevation_rad=-0.001`, `max_angle_above_zero_elevation_rad=1.5707963`. Enforce **range gate** `[0.10, 60.0] m` prior to integration; out‑of‑range points are dropped.
- **Config hooks:** The reorder stage reads its angle table path from `alpha_configs/lidar_airy.yaml` and validates dimensions; failures raise a health fault and block mapping.

## 0.5 Base Image & Provisioning (bootstrap)
- **Jetson:** JetPack (Orin), Docker Engine + Compose plugin, ROS 2 (Humble), NVIDIA Container Runtime. Create a readonly `/etc` profile and watchdog.
- **RPi:** 64‑bit OS, ROS 2 base, I²C/SPI enabled. Rootfs readonly overlay; hardware watchdog.
- **Secrets:** provisioned via `sops` (age) or Vault; cosign/WireGuard keys stored under `/var/lib/alpha/secrets/` with 600 perms. First‑boot script pulls `deploy/current.yaml` and starts A/B stack.

---

# PART II — Execution Plan (v2 foundation, expanded)

## 1. Repository Layout (unchanged from v2)
**Monorepo:** `alpha_ws/src/`
```
alpha_bringup/                  # startup sequencer + config manager + launch
alpha_mode_manager/             # SMACC2 hierarchical modes/overlays
alpha_orchestrator/             # failure domains & recovery ladder
alpha_lidar_airy/               # AIRY op-mode control (HTTP), vertical-angle reorder, diagnostics
alpha_safety_agent/             # RPi supervisor (heartbeat, safety, fans)
alpha_time_sync/                # PTP monitor + preflight gate
alpha_observability/            # ros2_tracing, SLO metrics, dashboards
alpha_recorder/                 # ring buffer + triggered capture + metadata
alpha_comms/                    # ws bridge, NVENC control, degrade policies
alpha_mapping/                  # provider interface + NVBlox/Voxblox plugins
alpha_navigation/               # teach&repeat: recorder/graph/follower
alpha_docking/                  # AprilTag-based docking
alpha_traction/                 # traction estimator, safety mux, recovery
alpha_calibration_tools/        # extrinsics + TF regression
alpha_ci/                       # sim worlds, netem profiles, CI jobs
alpha_security_ota/             # A/B compose, healthchecks, cosign, SROS2
alpha_ui_api/                   # topics/services for operator UI
alpha_utils/                    # msgs/srvs: Heartbeat, Health, Mode, Events, Power
```

**Top‑level config:** `alpha_configs/`
```
modes.yaml
failure_domains.yaml
degrade_policies.yaml
bandwidth_budgets.yaml
thermal_policy.yaml
recorder_profiles.yaml
calibration_bounds.yaml
mapping_provider.yaml
dock_config.yaml
traction_policy.yaml
schemas/  # JSON Schemas for validation
```

**Containers & deploy:** `deploy/`
```
compose.ab.yaml
compose.ba.yaml
lockfiles/
healthchecks/
cosign/
```

---

## 2. Core APIs & Messages (agent‑consumable)

### 2.1 Message Definitions
```msg
# alpha_utils/msg/Heartbeat.msg
builtin_interfaces/Time stamp
string source                 # node name
uint32 seq
```

```msg
# alpha_utils/msg/DomainHealth.msg
uint8 OK=0
uint8 DEGRADED=1
uint8 FAILED=2
uint8 UNKNOWN=3
string domain                 # e.g., "perception", "motion", "comms", "storage"
uint8 status
string reason                 # human-readable cause or code
```

```msg
# alpha_utils/msg/Health.msg
builtin_interfaces/Time stamp
alpha_utils/DomainHealth[] domains
```

```msg
# alpha_utils/msg/ModeState.msg
string base_mode              # e.g., "TELEOP", "FAILSAFE", "DOCKING", "RTH_TOPO"
string[] overlays             # e.g., ["NIGHT","MAPPING","LOW_POWER"]
bool failsafe                 # convenience flag
```

```msg
# alpha_utils/msg/Power.msg
builtin_interfaces/Time stamp
float32 voltage_v
float32 current_a
float32 power_w
```

```msg
# alpha_utils/msg/Event.msg
builtin_interfaces/Time stamp
string type                   # e.g., "SLO_BREACH","HEARTBEAT_LOSS","THERMAL_SHED"
string details                # free-form or JSON
```

```msg
# alpha_utils/msg/LidarState.msg
string id            # "front" | "rear"
string ip
uint8 op_mode        # 0=STANDBY, 1=RUN
bool ready           # true when spun up and publishing
```

### 2.2 Service Definitions
```srv
# alpha_utils/srv/ModeSet.srv
# Request
string target_base_mode
string[] enable_overlays
string[] disable_overlays
bool clear_overlays
string reason
---
# Response
bool accepted
string message
alpha_utils/ModeState current
```

```srv
# alpha_utils/srv/GetConfig.srv
# Request
string key                    # e.g., "bandwidth_budgets", "thermal_policy"
---
# Response
bool found
string yaml                   # raw YAML for that key (validated)
string message
```

```srv
# alpha_utils/srv/TriggerRecord.srv
# Request
string reason
---
# Response
bool started
string bag_id
string message
```

```srv
# alpha_utils/srv/OrchestratorCommand.srv
# Request
string action                 # "e_stop","resume","recover_perception"
---
# Response
bool accepted
string message
```

```srv
# alpha_utils/srv/SetLidarMode.srv
# Request
string target        # "front" | "rear" | "both"
uint8 op_mode        # 0=STANDBY, 1=RUN
---
# Response
bool accepted
string message
alpha_utils/LidarState[] states
```

### 2.3 Mode Manager Framework Decision
- **Chosen:** **SMACC2** for hierarchical modes/overlays (compile‑time safety, orthogonals, clear guards).
- **Interfaces:**
  - Subscribes: `/alpha/mode/set` (**ModeSet.srv**).
  - Publishes: `/alpha/mode/state` (**ModeState.msg**).
  - Guard queries: services to `alpha_time_sync/preflight_gate`, `alpha_calibration_tools/tf_ok`.

### 2.4 Mapping Provider Interface (C++ plugin)
```cpp
// alpha_mapping/include/alpha_mapping/provider_interface.hpp
namespace alpha_mapping {
class IMappingProvider {
public:
  virtual ~IMappingProvider() = default;
  virtual bool configure(rclcpp::Node* node) = 0;
  virtual void integrateCloud(const sensor_msgs::msg::PointCloud2::SharedPtr& cloud,
                              const std::string& frame_id,
                              const rclcpp::Time& stamp) = 0;
  virtual bool getTSDF(nvblox_msgs::msg::TsdfLayer& out) = 0;   // or alpha_mapping_msgs
  virtual bool getESDF(nvblox_msgs::msg::EsdfLayer& out) = 0;
  virtual void reset() = 0;
};
} // namespace alpha_mapping
```

- Plugins: `NvbloxProvider` and `VoxbloxProvider` registered via `pluginlib`.

---

## 3. Configuration Strategy & Validation

### 3.1 Loading
- `alpha_bringup` launches nodes with their **ROS 2 parameters** and also runs a **Config Manager** (`alpha_bringup/config_manager.py`) that:
  - Reads top‑level YAMLs in `alpha_configs/`.
  - Validates against JSON Schemas in `alpha_configs/schemas/`.
  - Publishes a **ParameterEvent** and serves **GetConfig.srv** per key.
  - Supports **SIGHUP** to re‑load (dev only).
  - Knows about keys: **network**, **lidar_airy**, **extrinsics_seed**, **startup_sequence**; validates each against its schema.

### 3.2 Validation
- `alpha_configs/schemas/*.schema.json` define required keys/types/ranges.
- CI job `alpha_ci/validate_configs` runs schema checks and round‑trips YAML→dict→YAML.
- Pre‑flight blocks on **invalid or missing configs**.

---

## 4. Operator/UI API (topics & services)

### 4.1 Status Feeds (UI subscribes)
- `/alpha/health` — `alpha_utils/Health`
- `/alpha/mode/state` — `alpha_utils/ModeState`
- `/alpha/time_sync/status` — `std_msgs/String` or custom (offset, drift, state)
- `/alpha/observability/slo` — `diagnostic_msgs/DiagnosticArray` (P95s)
- `/alpha/events` — `alpha_utils/Event`
- `/alpha/recorder/status` — `std_msgs/String` (ring active / triggered / bag_id)
- `/alpha/thermal/status` — `diagnostic_msgs/DiagnosticArray`
- `/alpha/docking/state`, `/alpha/rth/state` — `std_msgs/String` (state machine states/ETA)
- `/alpha/lidar/state` — `alpha_utils/LidarState[]` (front/rear state: STANDBY/RUN, ready)
- `/alpha/mapping/startup_status` — `std_msgs/String` (enum: `WAITING_FOR_LIDAR`, `SPINNING_UP`, `STARTED`)

### 4.2 Commands (UI invokes)
- `/alpha/mode/set` — `alpha_utils/ModeSet` (service)
- `/alpha/ui/cmd/dock` — `std_srvs/Trigger`
- `/alpha/ui/cmd/home` — `std_srvs/Trigger`
- `/alpha/ui/cmd/clear_faults` — `std_srvs/Trigger`
- `/alpha/recorder/trigger` — `alpha_utils/TriggerRecord`
- `/alpha/ui/cmd/lidar_mode` — `alpha_utils/SetLidarMode` (service)

---

## 5. Phases (kept from v2, with context)

> Phases remain identical to v2 (0.5 through 15) but now operate with the APIs/config above. For completeness, they are reproduced here with minimal edits.

### Phase 0.5 — Simulation + CI/HIL + Impairment Harness
**Goals:** deterministic tests for modes, degrade, recovery.  
**Deliverables:** sim worlds, netem profiles (Gilbert–Elliott), CI jobs with P95 asserts.  
**Acceptance:** Degrade ladder trips/reverses correctly under `120 ms RTT + 5–10%` burst loss; SLOs hold.

### Phase 1 — Safety Supervisor (RPi)
**Goals:** fail safe without Jetson.  
**Deliverables:** heartbeat watchdog, safety monitors, fan control, failsafe state machine.  
**Acceptance:** Link‑pull halts < 300 ms; LED/beeper; fans alive; tilt/undervolt latch.  
**Deliverables (additions):** LiDAR op‑mode control (HTTP OpM=0/1) via `alpha_lidar_airy`; boot service forces **STANDBY** on both units; status query/telemetry.  
**Acceptance (additions):** On cold boot, both LiDARs report **STANDBY**; manual **Run/Standby** commands for `front`/`rear`/`both` succeed; state reflects in `/alpha/lidar/state` within ≤1 s.

### Phase 2 — Observability: SLOs + Tracing
**Budgets (P95):** cmd ≤60 ms, map ≤90 ms, video ≤120 ms.  
**Deliverables:** ros2_tracing, SLO monitor; UI shows tripped SLO.  
**Acceptance:** SLO breach auto‑degrades; visible in ≤1 s.

### Phase 3 — Time Sync as a Gate
**Deliverables:** linuxptp agent, pre‑flight gate, capture‑time stamping.  
**Acceptance:** Clock step blocks pre‑flight; passes post‑convergence; deskew verified.

### Phase 4 — Comms Manager (SLO‑ & bandwidth‑aware)
**Deliverables:** ws bridge + NVENC control; degrade policies; budgets per mode.  
**Acceptance:** Under 5 Mbps cap, cmd latency ≤60 ms; video scales; mapping pauses at L2.

### Phase 5 — Failure‑Domain Orchestrator
**Deliverables:** `failure_domains.yaml`; health watchdog; recovery actions.  
**Acceptance:** Kill `vslam` → odom‑only + speed cap; UI flags `PERCEPTION_DEGRADED` in ≤1 s.

### Phase 6 — Forensic Recording (Ring + Triggered)
**Deliverables:** ring buffer + trigger nodes; unified metadata.json.  
**Acceptance:** −30/+60 s bag on trigger; checksums; metadata includes git/container/calib/PTP/temps.

### Phase 7 — Calibration First‑Class + TF Regression
**Deliverables:** AprilTag extrinsics tool; bounds; pre‑flight TF check; CI TF regression.  
**Acceptance:** Pre‑flight blocks if bounds exceeded.

### Phase 8 — Mapping Provider Abstraction
**Deliverables:** provider interface + NVBlox/Voxblox plugins; selector YAML.  
**Acceptance:** Swap to Voxblox; tests pass (lower FPS OK).  
**Deliverables (additions):** AIRY vertical‑angle reorder filter; NVBlox set to `lidar_height=96`, `lidar_width=900`, FOV `[-0.001, 1.5707963]` rad; range gate `[0.10,60.0]` m; startup sequencer: set LiDARs **RUN**, wait **10 s**, then start NVBlox.  
**Acceptance (additions):** Reorder validated against angle table; NVBlox receives 96×900; out‑of‑range points dropped; mapping starts only after spin‑up delay; mapping stability unchanged vs v2.2.

### Phase 8a — Sensor Drivers Online
**Objective:** Bring AIRY LiDAR and OAK camera drivers online with canonical topics, health checks, and startup gates.

**Acceptance:**
- AIRY LiDAR (front/rear) publish `/alpha/lidar/{front,rear}/points` at expected dims 96×900, skew ≤ 20 ms, stable rate.
- OAK cameras (front/rear) publish `/alpha/cam/{front,rear}/image_color` and `/camera_info` at 720p30 (or configured), camera_info sane. UI/stream pipeline targets P95 latency ≤ 120 ms.
- Mapping provider is gated until LiDAR OK; VSLAM gated until camera OK + time sync.

**External Packages & Dependencies (pins):**
| Package | Use | Install Target | Version Pin | Canonical Topics | Acceptance |
|---|---|---|---|---|---|
| rslidar_sdk (+ rslidar_msg) | AIRY LiDAR driver | Host (source) | Commit SHA | `/alpha/lidar/{front,rear}/points_raw` → reorder → `/points` | dims=96×900; skew ≤20 ms |
| depthai-ros | OAK camera driver | Host (apt) | apt version | `/alpha/cam/{front,rear}/image_color`, `/camera_info` | camera_info sane; FPS stable; UI P95≤120 ms |
| isaac_ros_nvblox | Mapping (ESDF/mesh) | Container | Image digest | provider contract topics | FPS target met; provider swap OK |
| isaac_ros_visual_slam | Visual SLAM | Container | Image digest | `/alpha/vslam/odom` + TF | repeatability tolerance OK |


### Phase 9 — Navigation: Teach‑&‑Repeat / Topological RTH
**Deliverables:** path recorder, graph builder, topo follower; `/start_record` `/stop_record` `/go_home`.  
**Acceptance:** 8/10 returns within 0.5 m / ±10° on 50 m dynamic route.

### Phase 10 — Autonomous Docking & Smart Charging
**Deliverables:** AprilTag detector; servo controller; dock config; charger handshake.  
**Acceptance:** 9/10 docks from 2–3 m ≤60 s; ≤3 cm lateral; ≤5° yaw; robust abort/retry.

### Phase 11 — Traction‑Aware Limiter + Stuck Recovery
**Deliverables:** slip estimator; safety mux; wiggle/back‑off.  
**Acceptance:** ≥50% fewer brownouts; stalls recover < 3 s.

### Phase 12 — Thermal/Power Policy
**Deliverables:** thermal policy; auto shedding; watchdog.  
**Acceptance:** Auto‑shed before throttle; control path responsive.

### Phase 13 — Bandwidth Budgets & QoS
**Deliverables:** budgets per mode; DDS QoS tiers; NVENC ladder & LiDAR throttle.  
**Acceptance:** Under 3–5 Mbps caps, cmd latency holds; graceful scaling of non‑critical topics.

### Phase 14 — Security & OTA
**Deliverables:** A/B Compose; cosign; SBOM; SROS2 on critical topics; WireGuard; RO rootfs.  
**Acceptance:** Bad deploy rolls back < 30 s; unauthorized cmd_vel_safe blocked; diagnostics pass.

### Phase 15 — Data Lifecycle & Catalog
**Deliverables:** auto offload to NAS; integrity; indexer → SQLite/web; re‑processing hooks.  
**Acceptance:** New run cataloged < 2 min post‑dock; searchable by git/SHA/temps/errors.

---

## 6. Modes — Hierarchical State Machine (SMACC2)
```yaml
# alpha_configs/modes.yaml (concept)
base: TELEOP
overlays:
  - NIGHT
  - LOW_POWER
  - MAPPING
exclusive:
  - FAILSAFE
  - DOCKING
  - RTH_TOPO
transitions:
  TELEOP -> DOCKING: when cmd 'dock' && battery < X
  TELEOP -> RTH_TOPO: when cmd 'home' || comms_lost
guards:
  enter MAPPING: ptp_ok && tf_ok
```

---

## 7. Key Config Templates (drop into `alpha_configs/`)
(unchanged from v2; shown here verbatim with schemas added)

### 7.1 `failure_domains.yaml`
```yaml
perception:
  critical: [vslam]
  optional: [nvblox]
  recovery:
    vslam_lost: [switch: wheel_odom_only, limit_speed: 0.3, mode: failsafe]
motion:
  critical: [base_driver, twist_mux]
  optional: [motion_guards]
  recovery:
    base_fault: [e_stop]
comms:
  critical: [ws_bridge]
  optional: [hud_stream]
storage:
  critical: [recorder_triggered]
  optional: [ring_buffer]
```

### 7.2 `degrade_policies.yaml`
```yaml
levels:
  L0: {video_fps: 30, video_bitrate: 6_000k, lidar_hz: 20, mapping: true}
  L1: {video_fps: 20, video_bitrate: 3_000k, lidar_hz: 15, mapping: true}
  L2: {video_fps: 10, video_bitrate: 1_200k, lidar_hz: 10, mapping: false}
  L3: {video_fps: 0,  video_bitrate: 0,      lidar_hz: 5,  mapping: false}
triggers:
  slo_p95_cmd_ms: 60
  slo_p95_map_ms: 90
  slo_p95_video_ms: 120
  rtt_ms: [80,120,180]
  loss_pct: [1,5,10]
```

### 7.3 `bandwidth_budgets.yaml`
```yaml
TELEOP:   {min_mbps: 3, max_mbps: 8}
MAPPING:  {min_mbps: 5, max_mbps: 12}
RTH_TOPO: {min_mbps: 2, max_mbps: 6}
```

### 7.4 `thermal_policy.yaml`
```yaml
warn_c: 80
shed_c: 85
actions:
  - at: warn_c   # UI warning, map rate -25%
  - at: shed_c   # nvpmodel↓, NVENC bitrate↓, pause mapping
  - clear: <78C  # resume compute
```

### 7.5 `recorder_profiles.yaml`
```yaml
continuous:
  topics: [/tf, /diagnostics, /alpha/health]
  retention_sec: 300
  rate_limit_hz: 10
triggered:
  topics: [/* sensors */, /alpha/*/internal_state]
  pre_sec: 30
  post_sec: 60
```

### 7.6 `calibration_bounds.yaml`
```yaml
base_to_lidar_front: {pos_mm: 5, yaw_deg: 0.3, pitch_deg: 0.3, roll_deg: 0.3}
base_to_lidar_rear:  {pos_mm: 5, yaw_deg: 0.3, pitch_deg: 0.3, roll_deg: 0.3}
base_to_camera:      {pos_mm: 5, yaw_deg: 0.5, pitch_deg: 0.5, roll_deg: 0.5}
```

### 7.7 `mapping_provider.yaml`
```yaml
provider: nvblox   # or 'voxblox'
tsdf_voxel: 0.15
esdf_enabled: true
input_topics: [/alpha/lidar/front/points, /alpha/lidar/rear/points]
lidar_dims: { height: 96, width: 900 }
fov:
  min_angle_below_zero_elevation_rad: -0.001
  max_angle_above_zero_elevation_rad: 1.5707963
range_m: { min: 0.10, max: 60.0 }
```

### 7.8 `dock_config.yaml`
```yaml
tag_id: 7
tag_size_m: 0.16
approach_m: 2.0
final_offset_m: 0.15
yaw_tol_deg: 5
lat_tol_m: 0.03
```

### 7.9 `traction_policy.yaml`
```yaml
slip_thresh: 0.25
current_spike_a: 3.0
yaw_rate_thresh: 0.6
accel_limit_scale: [1.0, 0.6, 0.4]  # normal->warn->crit
```

### 7.10 `schemas/` (examples)
`alpha_configs/schemas/degrade_policies.schema.json`
```json
{
  "type": "object",
  "properties": {
    "levels": { "type": "object" },
    "triggers": {
      "type": "object",
      "properties": {
        "slo_p95_cmd_ms": { "type": "number", "minimum": 1 },
        "slo_p95_map_ms": { "type": "number", "minimum": 1 },
        "slo_p95_video_ms": { "type": "number", "minimum": 1 },
        "rtt_ms": { "type": "array", "items": { "type": "number" } },
        "loss_pct": { "type": "array", "items": { "type": "number" } }
      },
      "required": ["slo_p95_cmd_ms","slo_p95_map_ms","slo_p95_video_ms"]
    }
  },
  "required": ["levels","triggers"]
}
```

### 7.11 `network.yaml`
```yaml
jetson:
  nic: eth0
  ipv4: 192.168.1.10/24
lidar:
  front:
    ip: 192.168.1.200
    ports: { msop: 6699, difop: 7788, imu: 6688 }
  rear:
    ip: 192.168.1.201
    ports: { msop: 6700, difop: 7789, imu: 6689 }
```

### 7.12 `lidar_airy.yaml`
```yaml
vertical_angle_table_path: /etc/alpha/lidar/airy_vertical_angles.csv   # TODO: confirm path
reorder_enabled: true
log_table_hash: true
expected_dims: { height: 96, width: 900 }
fov:
  min_angle_below_zero_elevation_rad: -0.001
  max_angle_above_zero_elevation_rad: 1.5707963
range_m: { min: 0.10, max: 60.0 }
```

### 7.13 `extrinsics_seed.yaml`
```yaml
frames:
  base_to_lidar_front:
    translation_m: [0.110367, 0.0, 0.037388]
    rpy_rad: [1.5707963, 0.0, 1.5707963]
  base_to_lidar_rear:
    translation_m: [-0.203071, 0.0, 0.061300]
    rpy_rad: [0.0, 0.0, 1.5707963]
  base_to_oakd_pro_optical:
    translation_m: [0.148469, 0.0, 0.097926]
    rpy_rad: [-1.8325957, 0.0, -1.5707963]
  base_to_oakd_sr_optical:
    translation_m: [-0.211326, 0.0, 0.023959]
    rpy_rad: [-1.6580628, 0.0, 1.5707963]
```

### 7.14 `startup_sequence.yaml`
```yaml
lidar_spinup_sec: 10
steps:
  - set_lidar_mode: { target: both, op_mode: 1 }   # 1=RUN
  - wait: { seconds: 10 }
  - start_node: { package: alpha_mapping, node: nvblox }  # start mapping after spin-up
publish_status_topic: /alpha/mapping/startup_status
status_enums: [WAITING_FOR_LIDAR, SPINNING_UP, STARTED]
```

---

## 8. Test Matrix (excerpt)
| Test | Setup | Pass Criteria |
|---|---|---|
| Preflight Time Sync | PTP offset injection | Block if \|offset\|≥5 ms; pass when <5 ms |
| SLO‑Driven Degrade | Netem RTT 120 ms + 5% burst loss | Degrades to L2 in ≤2 s; cmd latency ≤60 ms |
| VSLAM Loss | Kill process mid‑run | Switch to odom‑only; speed cap 0.3 m/s; UI flag |
| Thermal Shed | Heat to 85 °C | nvpmodel↓, NVENC↓, mapping paused; resume <78 °C |
| Docking | 10 trials, 2–3 m start | ≥9 success; ≤3 cm lateral; ≤5° yaw; ≤60 s |
| Traction Stall | Low‑μ ramp | ≥50% fewer brownouts; recovery <3 s |
| Network Addressing Sanity | Ping 192.168.1.200/201; netcat MSOP ports | Both LiDAR IPs reachable; MSOP ports open; no IP conflicts |
| LiDAR Standby at Boot | Cold boot | Both units report STANDBY on `/alpha/lidar/state` within ≤5 s |
| LiDAR Mode Toggle | UI service `/alpha/ui/cmd/lidar_mode` | Run↔Standby commands succeed for front/rear/both; state reflects ≤1 s |
| AIRY Row Reorder | Feed known pattern with angle table | Output rows sorted by ascending vertical angle; dims exactly 96×900 |
| NVBlox Parameter Sanity | Launch mapping with config | NVBlox accepts dims; vertical FOV set; out‑of‑range points dropped |
| Startup Sequencer | Observe sequencer logs | NVBlox starts ≥10 s after switching LiDARs to RUN; status transitions: WAITING→SPINNING_UP→STARTED |

---

## 9. Operator/UI Signals (must surface)
- **Time Sync:** `PTP_OK / WARN / FAIL` with offset/drift.
- **SLO Rungs:** which SLO tripped; current degrade level.
- **Failure Domains:** `OK/DEGRADED/FAILED` per domain with cause.
- **Recorder:** `RING ACTIVE / TRIGGERED (reason)`; link to bag ID.
- **Thermal:** `NORMAL / SHED / THROTTLE_RISK`.
- **Docking/RTH:** state + ETA.
- **LiDARs:** FRONT/REAR — `STANDBY`/`RUN` + `ready` flag; angle table hash (for reorder provenance).
- **Mapping Startup:** `WAITING_FOR_LIDAR` / `SPINNING_UP (T‑10…0)` / `STARTED`.

---

## 10. Implementation Order (unchanged)
1) Safety Supervisor (RPi) + Time Sync Gate  
2) Observability (SLOs + tracing)  
3) Comms Manager + budgets + impairment harness in CI  
4) Failure‑Domain Orchestrator  
5) Forensic Recorder + Metadata  
6) Calibration tools + TF preflight/CI  
7) Mapping Provider abstraction  
8) Topological RTH  
9) Docking & charging  
10) Traction + thermal/power  
11) Security & OTA  
12) Data offload & catalog

---

# Appendices

## A. Hardware Bill of Materials (baseline)
- Jetson Orin (AGX), NVMe 2 TB, active cooling.
- Raspberry Pi 4/5 with hardware watchdog.
- 2× RoboSense AIRY LiDAR with Ethernet.
- OAK‑D Pro-W Camera & OAK-D-SR Camera.
- IMU (Bosch/Analog Devices class).
- INA226 current/voltage monitor.
- Differential drive base and motor controller with `/cmd_vel` interface.
- AprilTag board (16 cm) for docking target.
- Docking contacts/charger with enable line (GPIO/CAN).

## B. LiDAR Mounting & Calibration Notes
- Rigid mounts with repeatable datum surfaces; cable strain‑relief.
- AprilTag calibration board for extrinsics; log calibration SHA; enforce bounds with pre‑flight TF check.
- Record LiDAR intrinsics/extrinsics under `alpha_calibration_tools/` with date + operator.

## C. Provisioning & Secrets
- First‑boot pulls `deploy/current.yaml` from a locked repo; verifies cosign signatures.
- Secrets delivered by `sops`‑encrypted files; decrypted on device with pre‑provisioned **age** key.
- WireGuard profiles enrolled per robot; keys rotated quarterly.

---

**End of v2.3**
