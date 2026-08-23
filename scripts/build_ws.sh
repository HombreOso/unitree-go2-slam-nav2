#!/usr/bin/env bash
# Build the go2 simulation workspace inside WSL.
set -eo pipefail
WS="${HOME}/go2_ws"
source /opt/ros/humble/setup.bash
cd "${WS}"
# go2_cmd_processor needs the physical Unitree SDK (unitree_api msgs), which is
# not installed in simulation; go2_sim's cmd_vel_bridge stands in for it.
colcon build --symlink-install --packages-skip go2_cmd_processor
echo "=== build finished ==="
source "${WS}/install/setup.bash"
ros2 pkg list | grep -E '^(go2_sim|go2_slam_nav|frontier|image_processing)$' || true
echo "--- executables ---"
ros2 pkg executables go2_sim || true
