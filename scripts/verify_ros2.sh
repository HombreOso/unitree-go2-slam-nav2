#!/usr/bin/env bash
source /opt/ros/humble/setup.bash
echo "ROS_DISTRO=$ROS_DISTRO"
for p in rtabmap_slam rtabmap_odom rtabmap_viz nav2_bringup nav2_navfn_planner nav2_waypoint_follower \
         gazebo_ros gazebo_plugins pointcloud_to_laserscan slam_toolbox robot_state_publisher xacro; do
  printf '%-28s ' "$p"
  if ros2 pkg prefix "$p" >/dev/null 2>&1; then echo OK; else echo MISSING; fi
done
echo "--- gazebo ---"
gzserver --version 2>&1 | head -2
echo "--- python ---"
python3 -c "import cv2, yaml; print('cv2', cv2.__version__, '| yaml ok')"
