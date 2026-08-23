source /mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2/scripts/ros_env.sh
OUT=/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2/results/preview
mkdir -p "$OUT"

SC=${1:-A}
# Spawn facing the first hazard cluster so the preview shows actual content.
ros2 launch go2_sim gazebo.launch.py scenario:=$SC gui:=false publish_odom_tf:=true \
    x:=1.2 y:=1.6 yaw:=0.35 > /tmp/gz.log 2>&1 &
LP=$!
sleep 80

python3 - "$OUT" "$SC" <<'PY'
import sys, rclpy, cv2
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

out_dir, sc = sys.argv[1], sys.argv[2]
rclpy.init()
n = Node('grab')
br = CvBridge()
got = {}
def cb(m):
    got['img'] = m
qos = QoSProfile(depth=2, reliability=ReliabilityPolicy.BEST_EFFORT)
n.create_subscription(Image, '/camera/color/image_raw', cb, qos)
import time
t0 = time.time()
while time.time() - t0 < 40 and 'img' not in got:
    rclpy.spin_once(n, timeout_sec=0.5)
if 'img' in got:
    f = br.imgmsg_to_cv2(got['img'], desired_encoding='bgr8')
    p = f"{out_dir}/scenario_{sc}_preview.jpg"
    cv2.imwrite(p, f, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    print("SAVED", p, f.shape)
else:
    print("NO IMAGE RECEIVED")
n.destroy_node(); rclpy.shutdown()
PY

kill $LP 2>/dev/null; pkill -f gzserver; pkill -f robot_state_pub; sleep 2
echo done
