Alpha Rover — Single Source of Truth

Overview
- This repository mirrors the Jetson Orin (alpha_orin) project setup.
- Contains the full ROS 2 workspace, configs, ops scripts, and docs required to rebuild a new device.

Structure
- `ros2_ws/`
  - `src/` — first‑party packages vendored here (e.g., `sensor_health_monitor`, `oak_*`).
  - `src/*` — vendor packages as submodules pointing to private mirrors (e.g., `rslidar_*`, `isaac_ros_common`).
  - `glim_config/` — GLIM configs.
- `alpha_ops/` — backup scripts/configs (symlinked to `~/alpha_ops`).
- `legacy/` — archived pre‑migration contents.
- Docs: `AGENTS.md`, `DUAL_AIRY_SETUP.md`, `OAK_MULTI_SENSOR_LAUNCH.md`.

Get Started
1) Clone with submodules:
   git clone --recurse-submodules git@github.com:alpharover/alpha_rover.git

2) Make this workspace canonical (symlink):
   ln -s ~/alpha_rover/ros2_ws ~/ros2_ws

3) Build:
   cd ~/ros2_ws && colcon build

4) Optional: import via ROS 2 vcs instead of submodules:
   cd ~/alpha_rover && vcs import ros2_ws/src < ros2.repos

Backups (GitHub + Google Drive)
- Scripts live in `alpha_ops/` (usable via `~/alpha_ops` symlink).

One‑time setup
- Google Drive OAuth: `~/alpha_ops/setup_rclone.sh`
- Initialize restic repo: `~/alpha_ops/restic_init.sh`

On‑demand backup
- `~/alpha_ops/backup-now.sh`
  - Pushes Git repos (to origin and private mirrors), writes system manifests, and snapshots data to Drive.

Weekly backups
- `~/alpha_ops/enable-backups.sh`
- Change time: edit `~/.config/systemd/user/alpha-backup.timer` and restart timer.

What gets backed up
- Include paths: `alpha_ops/data_paths.txt` (default includes `~/alpha_rover`).
- Exclusions: `~/.alpha-backupignore` skips build/venv/cache directories.

Restoring data
1) Install `rclone` and `restic`.
2) `~/alpha_ops/setup_rclone.sh` (or copy `~/.config/rclone/rclone.conf`).
3) `source alpha_ops/restic.env` (passphrase required) — see `alpha_ops/restic.env.example`.
4) `restic -r "$RESTIC_REPOSITORY" snapshots`
5) `restic -r "$RESTIC_REPOSITORY" restore latest --target ~/restore_sandbox`

Notes
- Secrets: `alpha_ops/restic.env` is not tracked; `restic.env.example` shows required vars.
- Vendor deps: third‑party repos are mirrored privately and included as submodules. When they change, update mirrors and then commit new submodule SHAs here.

Sudo Access (Askpass)
- Purpose: allow non-interactive `sudo` during maintenance and scripted tasks.
- Mechanism: an askpass helper prints the password from a private file; shell alias maps `sudo` to `sudo -A`.
- Files (local only, not tracked):
  - `~/.config/alpha_ops/secrets.env` (chmod 600) contains `SUDO_PASSWORD='...'`.
  - `~/.local/bin/alpha_askpass.sh` (chmod 700) reads the env file and echoes the password.
  - `~/.bashrc` exports `SUDO_ASKPASS="$HOME/.local/bin/alpha_askpass.sh"` and aliases `sudo` to `sudo -A`.
- Rotate password: edit `~/.config/alpha_ops/secrets.env` and start a new shell (or `source ~/.bashrc`).
- Remove askpass: delete the two files above and remove the export/alias lines from `~/.bashrc` (then `exec bash`).
- Security note: this stores a plaintext password with restrictive permissions; prefer scoped NOPASSWD sudoers in production.

## Agent Onboarding (Codex/LLMs)

- Start here: `AGENT_CONTEXT.md` — concise orientation for agents (paths, commands, packages, network, backups).
- Quick overview: run `~/alpha_ops/agent-hello.sh` for a one‑shot summary and JSON context.
- OAK quick commands: `oak start | oak map | oak foxglove | oak stop | oak lidar ...` (see `OAK_MULTI_SENSOR_LAUNCH.md`).
- ROS 2: ensure the environment is sourced: `source /opt/ros/humble/setup.bash`.
