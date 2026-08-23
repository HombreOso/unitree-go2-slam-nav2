source /mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2/scripts/ros_env.sh

ros2 launch go2_sim gazebo.launch.py scenario:=A gui:=false > /tmp/gz.log 2>&1 &
LP=$!
echo "launch pid $LP; waiting 90s..."
sleep 90

echo "=== TOPICS ==="
ros2 topic list 2>/dev/null | sort
echo
echo "=== DATA CHECK ==="
for t in /rslidar_points /camera/color/image_raw /camera/color/depth/image_raw /odom /scan /imu/data; do
  printf '%-36s ' "$t"
  timeout 25 ros2 topic echo "$t" --once --field header.frame_id 2>/dev/null | head -1 || echo "(NO DATA)"
done
echo
echo "=== TF odom->base_footprint ==="
timeout 12 ros2 run tf2_ros tf2_echo odom base_footprint 2>&1 | grep -A3 "Translation" | head -6
echo
echo "=== ERRORS ==="
grep -iE "\[Err\]|ERROR" /tmp/gz.log | grep -v "shader lib" | head -10
echo "=== SPAWN ==="
grep -i "spawn" /tmp/gz.log | tail -4

kill $LP 2>/dev/null
pkill -f gzserver; pkill -f gzclient; pkill -f robot_state_pub
sleep 3
echo "=== done ==="
