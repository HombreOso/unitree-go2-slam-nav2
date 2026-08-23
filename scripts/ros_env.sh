# Shared environment for every WSL-side ROS 2 / Gazebo script.
# Source this, do not execute it.

REPO_WIN=/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2
WS="${HOME}/go2_ws"

source /opt/ros/humble/setup.bash
source "${WS}/install/setup.bash"

# Gazebo's own setup.sh must be sourced BEFORE we append: it seeds
# GAZEBO_RESOURCE_PATH with the OGRE shader/media directories. Appending to an
# unset variable leaves those out and every material fails with
# "Unable to find shader lib".
if [ -f /usr/share/gazebo/setup.sh ]; then
    source /usr/share/gazebo/setup.sh
fi

export GAZEBO_MODEL_PATH="${GAZEBO_MODEL_PATH}:${REPO_WIN}/sim/go2_sim/models"
export GAZEBO_RESOURCE_PATH="${GAZEBO_RESOURCE_PATH}:${REPO_WIN}/sim/go2_sim/models"

# No GPU in WSL here, so OGRE has to go through llvmpipe.
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

# Never let Gazebo stall on a download from models.gazebosim.org - every model
# used by these worlds is local.
export GAZEBO_MODEL_DATABASE_URI=""

# DDS. Two things are deliberate here, both found the hard way:
#
#   * ROS_LOCALHOST_ONLY must stay UNSET. With rmw_cyclonedds on this WSL
#     distro every node dies at startup on "rmw_create_node: failed to create
#     domain" - which took down the whole Nav2 stack while Gazebo and SLAM kept
#     running, so the symptom looked like a Nav2 bug rather than a transport
#     one. Verified: 0/8 nodes survive with it set, 8/8 without.
#   * No CYCLONEDDS_URI. Cyclone's defaults work; the <Interfaces> syntax used
#     by newer Cyclone releases is rejected by the version Humble ships, and a
#     rejected config fails exactly the same way as the variable above.
#
# A non-default domain id keeps these runs from discovering anything else.
unset ROS_LOCALHOST_ONLY
unset CYCLONEDDS_URI
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=42
