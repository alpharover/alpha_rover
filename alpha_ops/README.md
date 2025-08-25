Alpha Rover Backup Ops

Overview
- Code: commit/push to GitHub. Vendor deps mirrored to private repos, pinned via submodules.
- Data: encrypted, deduplicated snapshots to Google Drive via `rclone` + `restic`.
- Cadence: weekly timer plus on-demand `backup-now.sh`.

Location
- This folder lives in the repo at `alpha_rover/alpha_ops` and is symlinked to `~/alpha_ops`.
- You can run scripts from either path.

Prereqs
- Ubuntu 22.04 LTS on Jetson (JetPack/L4T compatible)
- Tools: `sudo apt-get update && sudo apt-get install -y rclone restic git-lfs`
- GitHub SSH: add `~/.ssh/id_ed25519.pub` to your GitHub → Settings → SSH keys, then `ssh -T git@github.com`.

Google Drive Setup (one-time)
1) OAuth: `~/alpha_ops/setup_rclone.sh`
   - Approve in browser/headless flow. This wires the Drive folder you shared.
2) Init encrypted repo: `~/alpha_ops/restic_init.sh`
   - Writes `alpha_ops/restic.env` (not tracked in Git). Passphrase is required for restore.

Run a backup now
- `~/alpha_ops/backup-now.sh`
  - Pushes repos (origin/backup), writes system manifests, runs restic snapshot.

Include/Exclude
- Include list: `alpha_ops/data_paths.txt` (one path per line). Default includes `~/alpha_rover`.
- Exclusions: `~/.alpha-backupignore` ignores build caches (e.g., `build/`, `install/`, `.venv/`).

Enable weekly backups
- `~/alpha_ops/enable-backups.sh`
- Change time: edit `~/.config/systemd/user/alpha-backup.timer` (`OnCalendar=`), then:
  - `systemctl --user daemon-reload && systemctl --user restart alpha-backup.timer`

Check status/logs
- `systemctl --user list-timers | grep alpha-backup`
- `journalctl --user -u alpha-backup.service --no-pager`
- Logs also in `alpha_ops/logs/`.

Restore (high level)
1) Install `rclone` + `restic`.
2) Run `alpha_ops/setup_rclone.sh` (or copy your `rclone.conf`).
3) `source alpha_ops/restic.env` to load `RESTIC_REPOSITORY` and passphrase env.
4) Verify: `restic -r "$RESTIC_REPOSITORY" snapshots`
5) Restore: `restic -r "$RESTIC_REPOSITORY" restore latest --target ~/restore_sandbox`

Sudo/Askpass
- Scripts may invoke `sudo` non-interactively via askpass.
- Local files (not tracked):
  - `~/.config/alpha_ops/secrets.env` with `SUDO_PASSWORD='...'` (600 perms)
  - `~/.local/bin/alpha_askpass.sh` (700 perms)
  - `~/.bashrc` sets `SUDO_ASKPASS` and aliases `sudo` to `sudo -A`.
- Rotate/remove as described in the root README’s “Sudo Access (Askpass)” section.
