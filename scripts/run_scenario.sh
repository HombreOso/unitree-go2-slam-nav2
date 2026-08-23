#!/usr/bin/env bash
# =============================================================================
# Run one complete inspection run: Gazebo + SLAM + Nav2 + waypoint route +
# 1 fps frame capture, then save the map and shut everything down.
#
#   bash scripts/run_scenario.sh <A|B|C> <run_number> [slam_backend]
#
# Produces, under data/runs/scenario_<S>/run_<N>/:
#   frames/*.jpg     the captured RGB frames (timestamped filenames)
#   manifest.json    per-frame pose + visible hazards + ground-truth label
#   map.pgm/.yaml    the occupancy grid SLAM built
#   run.log          full console log
# =============================================================================
set -o pipefail

SCEN="${1:-A}"
RUN="${2:-1}"
BACKEND="${3:-rtabmap}"

REPO=/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2
source "${REPO}/scripts/ros_env.sh"

OUT="${REPO}/data/runs/scenario_${SCEN}/run_${RUN}"
mkdir -p "${OUT}"
LOG="${OUT}/run.log"
: > "${LOG}"

log() { echo "[$(date '+%T')] $*" | tee -a "${LOG}"; }

cleanup() {
    log "Shutting down."
    [ -n "${MISSION_PID:-}" ] && kill "${MISSION_PID}" 2>/dev/null
    [ -n "${LAUNCH_PID:-}" ] && kill "${LAUNCH_PID}" 2>/dev/null
    sleep 3
    pkill -f gzserver;  pkill -f gzclient
    pkill -f rtabmap;   pkill -f icp_odometry;  pkill -f slam_toolbox
    pkill -f controller_server; pkill -f planner_server; pkill -f bt_navigator
    pkill -f behavior_server;   pkill -f waypoint_follower
    pkill -f velocity_smoother; pkill -f lifecycle_manager
    pkill -f robot_state_pub;   pkill -f frame_capture
    pkill -f pointcloud_to_laserscan; pkill -f cmd_vel_bridge
    sleep 2
}
trap cleanup EXIT INT TERM

log "=== Scenario ${SCEN}, run ${RUN}, SLAM backend '${BACKEND}' ==="

# --- 1. Bring up the stack -------------------------------------------------
ros2 launch go2_sim inspection.launch.py \
    scenario:="${SCEN}" run:="${RUN}" slam_backend:="${BACKEND}" gui:=false \
    >> "${LOG}" 2>&1 &
LAUNCH_PID=$!
log "Stack launching (pid ${LAUNCH_PID})."

# --- 2. Wait for Nav2 to be ready -----------------------------------------
# The stack starts in stages (Gazebo, then SLAM, then Nav2), so poll for the
# action server rather than guessing a fixed sleep.
log "Waiting for Nav2's follow_waypoints action server (up to 6 min)..."
READY=0
for i in $(seq 1 72); do
    sleep 5
    if ros2 action list 2>/dev/null | grep -q "follow_waypoints"; then
        READY=1
        log "Nav2 is up after ~$((i * 5))s."
        break
    fi
done
if [ "${READY}" -ne 1 ]; then
    log "ERROR: Nav2 never came up. See ${LOG}."
    exit 1
fi

# Let SLAM accumulate a map before asking Nav2 to plan across it.
log "Letting SLAM settle for 25s."
sleep 25

# --- 3. Drive the inspection route -----------------------------------------
log "Starting the waypoint mission."
ros2 run go2_sim waypoint_mission --ros-args \
    -p scenario:="${SCEN}" -p use_sim_time:=true >> "${LOG}" 2>&1 &
MISSION_PID=$!

# Cap the run so a stuck robot cannot hang the whole batch.
MAX_WAIT=1500
WAITED=0
while kill -0 "${MISSION_PID}" 2>/dev/null; do
    sleep 10
    WAITED=$((WAITED + 10))
    if [ "${WAITED}" -ge "${MAX_WAIT}" ]; then
        log "WARNING: mission exceeded ${MAX_WAIT}s; stopping it and keeping what was captured."
        kill "${MISSION_PID}" 2>/dev/null
        break
    fi
    if [ $((WAITED % 120)) -eq 0 ]; then
        N=$(ls -1 "${OUT}/frames" 2>/dev/null | wc -l)
        log "  ...${WAITED}s elapsed, ${N} frames captured."
    fi
done
log "Route finished after ${WAITED}s."

# Keep capturing briefly so the last waypoint is represented.
sleep 8

# --- 4. Save the map -------------------------------------------------------
log "Saving the occupancy grid."
timeout 90 ros2 run nav2_map_server map_saver_cli -f "${OUT}/map" \
    --ros-args -p use_sim_time:=true >> "${LOG}" 2>&1 \
    && log "Map saved to ${OUT}/map.pgm" \
    || log "WARNING: map_saver failed (see ${LOG})."

# --- 5. Stop frame capture cleanly so it writes its manifest ---------------
log "Stopping frame capture so it flushes manifest.json."
pkill -INT -f frame_capture
sleep 6

N=$(ls -1 "${OUT}/frames" 2>/dev/null | wc -l)
log "=== Run complete: ${N} frames in ${OUT} ==="
if [ -f "${OUT}/manifest.json" ]; then
    log "manifest.json written."
else
    log "WARNING: manifest.json missing."
fi
