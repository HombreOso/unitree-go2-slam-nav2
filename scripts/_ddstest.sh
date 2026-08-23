REPO=/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2
source /opt/ros/humble/setup.bash
source "$HOME/go2_ws/install/setup.bash"

try() {
  local name="$1"; shift
  ( # subshell so env changes don't leak
    unset ROS_LOCALHOST_ONLY CYCLONEDDS_URI RMW_IMPLEMENTATION ROS_DOMAIN_ID
    eval "$1"
    rm -f /tmp/t*.log
    for i in $(seq 1 8); do
      ros2 run demo_nodes_cpp talker --ros-args -r __node:=t$i > /tmp/t$i.log 2>&1 &
    done
    sleep 10
    alive=$(pgrep -fc 'demo_nodes_cpp talker' 2>/dev/null || echo 0)
    errs=$(grep -l "failed to create domain" /tmp/t*.log 2>/dev/null | wc -l)
    printf '%-42s alive=%s/8  domain_errors=%s\n' "$name" "$alive" "$errs"
    pkill -f demo_nodes_cpp 2>/dev/null
    sleep 2
  )
}

echo "--- interfaces ---"; ip -br addr | head
echo
try "cyclonedds DEFAULT (no URI, no localhost_only)" 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp'
try "cyclonedds + our XML"                            "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export CYCLONEDDS_URI=file://$REPO/scripts/cyclonedds.xml"
try "fastrtps DEFAULT"                                'export RMW_IMPLEMENTATION=rmw_fastrtps_cpp'
try "fastrtps + ROS_LOCALHOST_ONLY=1"                 'export RMW_IMPLEMENTATION=rmw_fastrtps_cpp; export ROS_LOCALHOST_ONLY=1'
echo done
