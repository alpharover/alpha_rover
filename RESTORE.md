Alpha Rover — Disaster Recovery

Goal
- Reproduce the Alpha Rover system on a fresh Jetson or host using this repo and the encrypted Google Drive backup.

Prerequisites
- OS: Ubuntu 22.04 LTS (JetPack/Jetson L4T recommended for hardware).
- Packages:
  sudo apt-get update && sudo apt-get install -y \
    git git-lfs rclone restic build-essential cmake \
    python3-colcon-common-extensions

Source Code
1) Configure GitHub SSH (if needed) and add your public key.
2) Clone with submodules:
   git clone --recurse-submodules git@github.com:alpharover/alpha_rover.git
3) Make the workspace canonical path (optional but recommended):
   ln -s ~/alpha_rover/ros2_ws ~/ros2_ws

Backups — Google Drive (restic)
1) Configure Drive remote:
   ~/alpha_rover/alpha_ops/setup_rclone.sh
   (headless flow prints a URL to authorize; paste code back in the terminal)
2) Create `alpha_ops/restic.env` from the example and set the passphrase:
   cp ~/alpha_rover/alpha_ops/restic.env.example ~/alpha_rover/alpha_ops/restic.env
   # edit RESTIC_PASSWORD (owner keeps it safe)
3) Load env and verify snapshots:
   source ~/alpha_rover/alpha_ops/restic.env
   restic -r "$RESTIC_REPOSITORY" snapshots
4) Restore to a sandbox path (example):
   restic -r "$RESTIC_REPOSITORY" restore latest --target ~/restore_sandbox

Rebuild
1) Build workspace:
   cd ~/ros2_ws && colcon build
2) Configure runtime (e.g., udev, systemd units for your application) as needed.

Enable Scheduled Backups
- Enable weekly timer:
  ~/alpha_rover/alpha_ops/enable-backups.sh
  # change schedule via ~/.config/systemd/user/alpha-backup.timer (OnCalendar)

Troubleshooting
- SSH/GitHub: `ssh -T git@github.com`
- Drive auth: rerun `setup_rclone.sh` if token expired.
- Restic repo path: defined in `alpha_ops/restic.env` (default: rclone:gdrive:restic-alpha_orin).
- Logs: `journalctl --user -u alpha-backup.service --no-pager` and `alpha_ops/logs/`.

