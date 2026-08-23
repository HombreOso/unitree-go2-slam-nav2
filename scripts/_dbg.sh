source /opt/ros/humble/setup.bash
cd "$HOME/go2_ws"
rm -rf build/go2_sim install/go2_sim
colcon build --symlink-install --packages-select go2_sim 2>&1 | tail -5
source "$HOME/go2_ws/install/setup.bash"
echo "--- executables ---"; ros2 pkg executables go2_sim
echo "--- xacro parse test ---"
xacro "$HOME/go2_ws/install/go2_sim/share/go2_sim/urdf/go2_sim.urdf.xacro" publish_odom_tf:=false > /tmp/go2.urdf && echo "XACRO OK: $(wc -l < /tmp/go2.urdf) lines" || echo "XACRO FAILED"
