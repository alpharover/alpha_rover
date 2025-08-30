# UI Parameter Candidates

## Network
- Jetson network interface `eth0` and IP `192.168.1.10/24`
- Front LiDAR IP `192.168.1.200` and ports `msop:6699`, `difop:7788`, `imu:6688`
- Rear LiDAR IP `192.168.1.201` and ports `msop:6700`, `difop:7789`, `imu:6689`

## LiDAR
- Vertical angle table path and reorder/log flags
- Expected frame dimensions `height:96`, `width:900`
- Field of view angles (min `-0.001`, max `1.5707963` radians)
- Range limits `0.10–60.0 m`

## Mapping
- Provider `nvblox` with TSDF voxel `0.15` and ESDF enable flag
- Input LiDAR topics and expected dimensions
- Mapping FOV and range limits

## Thermal
- Warning and shedding thresholds (`warn_c:80`, `shed_c:85`)
- Thermal actions and clear condition

## Degradation Policies
- Levels L0–L3 with video frame rate, bitrate, LiDAR rate, and mapping flag
- Trigger thresholds for latency SLOs, round-trip time, and packet loss

## Bandwidth Budgets
- Target min/max Mbps for TELEOP, MAPPING, and RTH_TOPO modes

## Failure Domains
- Critical and optional components with recovery actions for perception, motion, comms, and storage subsystems

## Calibration
- Bounds on pose errors for sensors relative to the base
- Seed extrinsic transforms for LiDAR and cameras

## Recorder Profiles
- Continuous topics, retention time, and rate limits
- Triggered topics with pre/post recording windows

## Startup Sequence
- LiDAR spin-up time and step sequence
- Status topic and enumerated states

## Docking
- AprilTag ID, size, approach distance, final offset, and tolerances

## Observability
- Service-level objectives for command latency and mapping latency

## Lifecycle States
- Allowed system states: INIT, RUNNING, DEGRADED, FAILED, SHUTDOWN
