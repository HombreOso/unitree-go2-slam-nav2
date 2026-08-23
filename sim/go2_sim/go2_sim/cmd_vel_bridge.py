#!/usr/bin/env python3
"""
Simulation stand-in for the real ``go2_cmd_processor`` node.

On hardware that node subscribes to Nav2's /cmd_vel and republishes it as a
Unitree SportMode "Move" request (api_id 1008) at 200 Hz, zeroing the command
if nothing new arrives within 0.25 s (Section 4.2 of the paper). In Gazebo the
planar-move plugin consumes Twist directly, so we keep the same watchdog and
the same Go2 velocity envelope and simply forward the Twist.

Keeping this layer in the loop matters: it means the Nav2 velocity limits tuned
in simulation are the limits the physical robot would actually see, instead of
Nav2 talking to an idealised plant it will never meet on hardware.
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class CmdVelBridge(Node):
    def __init__(self):
        super().__init__('cmd_vel_bridge')

        self.declare_parameter('rate', 50.0)
        self.declare_parameter('cmd_vel_timeout', 0.25)
        self.declare_parameter('input_topic', '/cmd_vel')
        self.declare_parameter('output_topic', '/cmd_vel_sim')
        # Go2 SportMode envelope, deliberately conservative for indoor
        # inspection: the robot is carrying a LiDAR and is meant to produce
        # usable camera frames, not to move fast.
        self.declare_parameter('max_vx', 0.8)
        self.declare_parameter('max_vy', 0.4)
        self.declare_parameter('max_wz', 1.0)

        gp = lambda n: self.get_parameter(n).value
        self.timeout = float(gp('cmd_vel_timeout'))
        self.max_vx = float(gp('max_vx'))
        self.max_vy = float(gp('max_vy'))
        self.max_wz = float(gp('max_wz'))

        self.last_cmd = Twist()
        self.last_stamp = None
        self.stopped = True

        self.pub = self.create_publisher(Twist, gp('output_topic'), 10)
        self.create_subscription(Twist, gp('input_topic'), self._on_cmd, 10)
        self.create_timer(1.0 / float(gp('rate')), self._tick)

        self.get_logger().info(
            f"cmd_vel bridge up: {gp('input_topic')} -> {gp('output_topic')}, "
            f'watchdog {self.timeout}s, limits '
            f'vx<={self.max_vx} vy<={self.max_vy} wz<={self.max_wz}')

    @staticmethod
    def _clamp(v, lim):
        return max(-lim, min(lim, v))

    def _on_cmd(self, msg: Twist):
        out = Twist()
        out.linear.x = self._clamp(msg.linear.x, self.max_vx)
        out.linear.y = self._clamp(msg.linear.y, self.max_vy)
        out.angular.z = self._clamp(msg.angular.z, self.max_wz)
        self.last_cmd = out
        self.last_stamp = self.get_clock().now()
        self.stopped = False

    def _tick(self):
        if self.last_stamp is None:
            return
        age = (self.get_clock().now() - self.last_stamp).nanoseconds / 1e9
        if age > self.timeout:
            # Watchdog: stale commands must not keep the robot walking.
            if not self.stopped:
                self.get_logger().warn(
                    f'cmd_vel stale ({age:.2f}s) - stopping.', throttle_duration_sec=5.0)
                self.pub.publish(Twist())
                self.stopped = True
            return
        self.pub.publish(self.last_cmd)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
