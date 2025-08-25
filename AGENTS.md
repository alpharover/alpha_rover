# Repository Guidelines

## Project Structure & Module Organization
- Root: `ros2_ws/` with `src/` (packages), `build/`, `install/`, `log/`.
- Packages live under `src/<package_name>`; keep one concern per package.
- Config in `<package>/config/*.yaml`; launch files in `<package>/launch/*.launch.py`.
- Tests live in `<package>/test/` alongside the code they validate.

## Build, Test, and Development Commands
- Build: `colcon build --symlink-install`
  - Incremental builds with symlinks for faster edit–run cycles.
- Source env: `source install/setup.bash`
  - Makes built packages available to `ros2` CLI and runtime.
- Run node: `ros2 run <package> <executable>`
- Launch: `ros2 launch <package> <file.launch.py>`
- Test: `colcon test && colcon test-result --verbose`
- Lint/format (Python): `black . && isort . && flake8`
- Lint/format (C++): `ament_uncrustify --reformat`, `clang-format -i` on sources.

## Coding Style & Naming Conventions
- Python: 4‑space indent, Black defaults; imports sorted by isort.
- C++: follow ament/ROS 2 style (brace-on-same-line, 2‑space or project default indent).
- Packages/topics/services: `lower_snake_case`; message/service types: `CamelCase`.
- Executables and node names: `lower_snake_case`; classes: `CamelCase`.
- Keep launch/config names descriptive: `robot_bringup.launch.py`, `camera.yaml`.

## Testing Guidelines
- Python tests with `pytest` via `ament_pytest`; C++ with `ament_cmake_gtest`.
- Name tests `test_*.py` and `<target>_test.cpp`; place fixtures in `test/`.
- Run all tests with `colcon test`; aim for meaningful coverage and fast runtime.
- Prefer deterministic tests; avoid real hardware in CI—mock interfaces instead.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits style (e.g., `feat(pkg): add image rectifier`).
- Keep messages imperative, include scope, and reference issues (`Fixes #123`).
- PRs: clear summary, linked issues, test plan/output, and relevant screenshots/logs.
- Ensure `colcon build` and `colcon test` pass locally before requesting review.

## Security & Configuration Tips
- Do not commit secrets or large logs; add to `.gitignore`.
- Use parameters YAML under `config/`; prefer `ROS_DOMAIN_ID` to avoid cross‑talk.
- For reproducibility, document hardware/ROS distro in the package README.

## System Documentation
- **OAK Multi-Sensor Launch System**: See `OAK_MULTI_SENSOR_LAUNCH.md` for complete sensor orchestration system
  - Quick commands: `oak`, `oak map`, `oak foxglove`, `oak stop`, `oak lidar [status|standby|run]`
  - AIRY LiDARs default to Standby at boot (user service `airy-standby.service`).
  - Technical details: TF tree, QoS settings, process management, troubleshooting
  - Hardware: OAK-D cameras + AIRY LiDARs with precise mounting coordinates

- **Isaac ROS nvblox (3D Mapping)**
  - Install (APT): repository added and `ros-humble-isaac-ros-nvblox` installed.
  - One-liner: `oak map` — launches both OAK cameras (Pro + SR), nvblox (front AIRY LiDAR), and Foxglove.
    - Options: `oak map --lidar rear` (rear LiDAR); `--lidar both` is experimental and will auto‑fallback.
  - Manual: `ros2 launch oak_nvblox_bringup nvblox_dual_cams_with_lidar.launch.py`
    - Defaults: `global_frame=base_link`, QoS `SENSOR_DATA`, ESDF 3D, color disabled (BGR8 vs RGB8).
  - Visualize in Foxglove (fixed frame `base_link`):
    - `/nvblox_node/static_esdf_pointcloud`, `/nvblox_node/static_map_slice`, `/nvblox_node/static_occupancy_grid`, `/nvblox_node/combined_occupancy_grid`, `/nvblox_node/mesh`.
  - Stop: `oak stop` to stop sensors/bridge/nvblox.

## Headless WiFi Access (Remote Sites)
- **Automatic Fallback**: System auto-switches to AP mode when no known WiFi networks found (60s timeout)
- **Network Name**: `alpha_orin_wireless`
- **Password**: `9909`
- **Jetson IP**: `192.168.4.1`
- **SSH Command**: `ssh alpha_orin@192.168.4.1`

**Usage:**
1. Take Jetson to remote site (no WiFi router)
2. Boot system - waits 60s for known networks
3. If none found, becomes WiFi hotspot automatically
4. Connect MacBook to "alpha_orin_wireless" (password: 9909)
5. SSH normally to 192.168.4.1

**Service Management:**
- Status: `sudo systemctl status wifi-fallback.service`
- Logs: `sudo tail -f /var/log/wifi-fallback.log`
- Manual start: `sudo systemctl start wifi-fallback.service`
- Disable: `sudo systemctl disable wifi-fallback.service`

## Next Steps (Planned)
- Enable color mapping (RGB8 conversion + flag).
- Investigate robust dual‑LiDAR support with nvblox or pre‑fusion.
- Add map save/load helpers (PLY/ESDF/Occupancy).
- Switch mapping frame to `odom`/`map` when available; add CLI flag.

## Agent Onboarding (Codex/LLMs)
- Read `AGENT_CONTEXT.md` first for an immediate orientation (paths, commands, packages, network, backups).
- Run `~/alpha_ops/agent-hello.sh` to print a concise overview and machine‑readable JSON summary.
- Ensure ROS 2 env is loaded: `source /opt/ros/humble/setup.bash` before any `ros2`/`colcon` usage.
- Entrypoint for the OAK system is the `oak` CLI (`~/.local/bin/oak`) → `ros2_ws/src/oak_multi_bringup/scripts/oak`.
