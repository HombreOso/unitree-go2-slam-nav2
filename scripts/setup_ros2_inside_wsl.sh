#!/usr/bin/env bash
# =============================================================================
# Stage 1b - Install ROS 2 Humble + Gazebo + RTAB-Map + Nav2 inside WSL Ubuntu.
#
# Run INSIDE the WSL Ubuntu-22.04 shell:
#     bash /mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2/scripts/setup_ros2_inside_wsl.sh
#
# Reproduces Module A of Naderi et al. (2026). The paper used ROS 2 Foxy on
# Ubuntu 20.04; Foxy reached end-of-life in May 2023, so we target Humble
# (Ubuntu 22.04 LTS). The RTAB-Map + Nav2 node graph is unchanged.
# =============================================================================
set -euo pipefail

WS="${HOME}/go2_ws"
REPO_WIN="/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2"
LOG="${REPO_WIN}/results/stage1_ros2_setup.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

log "=== Stage 1b: ROS 2 Humble setup starting ==="
log "Ubuntu: $(lsb_release -ds 2>/dev/null || echo unknown)"

# --- 1. Base tooling -------------------------------------------------------
log "Installing base tooling."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    curl gnupg lsb-release software-properties-common \
    build-essential git python3-pip

# --- 2. ROS 2 apt repository ----------------------------------------------
if [ ! -f /etc/apt/sources.list.d/ros2.list ]; then
    log "Adding the ROS 2 apt repository."
    sudo add-apt-repository -y universe
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
        | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    sudo apt-get update -qq
else
    log "ROS 2 apt repository already present."
fi

# --- 3. ROS 2 Humble + simulation + SLAM + navigation ----------------------
log "Installing ros-humble-desktop (this is the long one, ~10-20 min)."
sudo apt-get install -y ros-humble-desktop

log "Installing Gazebo Classic 11 + ROS integration."
sudo apt-get install -y \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-gazebo-plugins \
    ros-humble-gazebo-ros2-control

log "Installing SLAM (RTAB-Map, as used in the paper) and navigation (Nav2)."
sudo apt-get install -y \
    ros-humble-rtabmap-ros \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-slam-toolbox

log "Installing supporting ROS packages."
sudo apt-get install -y \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    ros-humble-pointcloud-to-laserscan \
    ros-humble-tf2-tools \
    ros-humble-tf-transformations \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-image-transport-plugins \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-opencv

# --- 4. rosdep -------------------------------------------------------------
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    log "Initialising rosdep."
    sudo rosdep init || true
fi
rosdep update || true

# --- 5. Workspace ----------------------------------------------------------
log "Creating workspace at ${WS}."
mkdir -p "${WS}/src"

# The simulation package lives in the Windows repo; symlink it in so edits on
# either side stay in sync rather than being copied and drifting apart.
if [ ! -e "${WS}/src/go2_sim" ]; then
    ln -s "${REPO_WIN}/sim/go2_sim" "${WS}/src/go2_sim"
    log "Linked go2_sim into the workspace."
fi
for pkg in go2_slam_nav go2_cmd_processor frontier image_processing; do
    if [ -d "${REPO_WIN}/${pkg}" ] && [ ! -e "${WS}/src/${pkg}" ]; then
        ln -s "${REPO_WIN}/${pkg}" "${WS}/src/${pkg}"
        log "Linked ${pkg} into the workspace."
    fi
done

# --- 6. Build --------------------------------------------------------------
# Pass --no-build to install the toolchain only and build later; useful when the
# apt install and the package authoring are happening in parallel.
if [ "${1:-}" = "--no-build" ]; then
    log "Skipping colcon build (--no-build). Run scripts/build_ws.sh when ready."
else
    log "Building the workspace."
    set +u
    source /opt/ros/humble/setup.bash
    set -u
    cd "${WS}"
    # go2_cmd_processor talks to the physical Unitree SDK, which is not present
    # in simulation; skip it so the build does not fail on a missing dependency.
    colcon build --symlink-install --packages-skip go2_cmd_processor 2>&1 | tee -a "$LOG"
fi

# --- 7. Shell convenience --------------------------------------------------
if ! grep -q "go2_ws/install/setup.bash" "${HOME}/.bashrc" 2>/dev/null; then
    {
        echo ""
        echo "# --- ROS 2 (added by unitree-go2-slam-nav2 setup) ---"
        echo "source /opt/ros/humble/setup.bash"
        echo "source ${WS}/install/setup.bash"
        echo "export GAZEBO_MODEL_PATH=\$GAZEBO_MODEL_PATH:${REPO_WIN}/sim/go2_sim/models"
        # Gazebo Classic has no GPU in WSL; force software rendering so it does
        # not fall over on a missing GL driver.
        echo "export LIBGL_ALWAYS_SOFTWARE=1"
        echo "export GALLIUM_DRIVER=llvmpipe"
    } >> "${HOME}/.bashrc"
    log "Added ROS 2 sourcing to ~/.bashrc."
fi

log "=== Stage 1b complete ==="
log "Open a NEW WSL shell, then run:"
log "  ros2 launch go2_sim scenario.launch.py scenario:=A"
