Alpha Rover Backup Ops

Overview
- Code: pushed to GitHub (SSH). No auto-commit.
- Data: encrypted snapshots to Google Drive via rclone + restic.
- Cadence: weekly timer + on-demand `backup-now.sh`.

Prereqs
1) Install tools (run these on Ubuntu 22.04):
   sudo apt-get update && sudo apt-get install -y rclone restic git-lfs

2) Configure GitHub SSH (if not already):
   - Add this public key to your GitHub account: `~/.ssh/id_ed25519.pub`
   - Test: ssh -T git@github.com

3) Configure Google Drive remote (one-time):
   ~/alpha_ops/setup_rclone.sh

4) Initialize restic repository (one-time):
   ~/alpha_ops/restic_init.sh

Run a backup now
~/alpha_ops/backup-now.sh

Enable weekly backups
~/alpha_ops/enable-backups.sh

Restore (high level)
- Install rclone + restic
- Run setup_rclone.sh (or copy your rclone.conf)
- Export RESTIC_PASSWORD (from restic.env) and run:
  restic -r rclone:gdrive:restic-alpha_orin snapshots
  restic -r rclone:gdrive:restic-alpha_orin restore latest --target ~/restore_sandbox

