#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="alpharover/alpha_rover"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install: https://cli.github.com/" >&2
  exit 1
fi

echo "Setting GitHub topics on ${REPO_SLUG}..."

# Recommended topics for discoverability
topics=(
  ros2
  ros2-humble
  robotics
  rover
  teleoperation
  mapping
  lidar
  apriltag
  nvblox
  jetson
  nv-jetson
  ubuntu-22-04
  observability
  tracing
  sros2
)

for t in "${topics[@]}"; do
  gh repo edit "$REPO_SLUG" --add-topic "$t"
done

echo "Done. Verify at: https://github.com/${REPO_SLUG}/settings"

