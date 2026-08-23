OUT=/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2/data/runs/scenario_A/run_1
echo "--- dir ---"; ls -la "$OUT" 2>&1 | head
echo "--- frames: $(ls -1 "$OUT/frames" 2>/dev/null | wc -l) ---"
echo "--- progress ---"
grep -E "Nav2 is up|Waiting for Nav2|Starting the waypoint|frames captured|Route finished|ERROR" "$OUT/run.log" 2>/dev/null | tail -8
echo "--- died ---"; grep -c "process has died" "$OUT/run.log" 2>/dev/null
echo "--- procs ---"
for p in gzserver icp_odometry rtabmap controller_server bt_navigator waypoint_follower frame_capture; do
  printf '%-20s %s\n' "$p" "$(pgrep -fc $p 2>/dev/null || echo 0)"
done
