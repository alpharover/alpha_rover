#!/usr/bin/env bash
set -euo pipefail
TAG="${1:-YYYY.MM-dev}"
IMG="nvcr.io/nvidia/isaac-ros/ros2_humble:${TAG}"
echo "Pulling ${IMG} ..."
docker pull "${IMG}"
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMG}")
sed -i "s|^ISAAC_ROS_HUMBLE_DEV_DIGEST=.*|ISAAC_ROS_HUMBLE_DEV_DIGEST=${DIGEST}|" "$(dirname "$0")/../deploy/IMAGES.lock"
echo "Pinned: ${DIGEST}"

