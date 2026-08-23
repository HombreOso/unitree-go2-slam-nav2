#!/usr/bin/env python3
"""
Drive the scenario's inspection route through Nav2's FollowWaypoints action.

This is the "repeatable coverage and targeted revisits via waypoints" the paper
credits Module A with (Abstract, Section 3.2): the same route is flown on every
run, so differences between runs come from perception and control noise rather
than from a human steering differently each time. That repeatability is what
makes the three-runs-per-scenario averaging in Section 6 mean anything.

The node exits once the route finishes, which lets a shell script run a whole
scenario unattended.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints
from rclpy.action import ActionClient
from rclpy.node import Node


def yaw_to_quat(yaw):
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class WaypointMission(Node):
    def __init__(self):
        super().__init__('waypoint_mission')

        self.declare_parameter('scenario', 'A')
        self.declare_parameter('scenarios_yaml', '')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('loop', False)

        self.scenario = str(self.get_parameter('scenario').value).upper()
        self.frame_id = self.get_parameter('frame_id').value

        path = self.get_parameter('scenarios_yaml').value or (
            '/mnt/c/Users/admin/Documents/Robotics/Naderi2026/'
            'unitree-go2-slam-nav2/sim/go2_sim/config/scenarios.yaml')
        cfg = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
        self.waypoints = cfg['scenarios'][self.scenario]['waypoints']

        self.client = ActionClient(self, FollowWaypoints, 'follow_waypoints')
        self.result_code = None

        self.get_logger().info(
            f'Scenario {self.scenario}: {len(self.waypoints)} waypoints loaded.')

    def _build_goal(self):
        goal = FollowWaypoints.Goal()
        now = self.get_clock().now().to_msg()
        for (x, y, yaw) in self.waypoints:
            ps = PoseStamped()
            ps.header.frame_id = self.frame_id
            ps.header.stamp = now
            ps.pose.position.x = float(x)
            ps.pose.position.y = float(y)
            qz, qw = yaw_to_quat(float(yaw))
            ps.pose.orientation.z = qz
            ps.pose.orientation.w = qw
            goal.poses.append(ps)
        return goal

    def _feedback(self, msg):
        idx = msg.feedback.current_waypoint
        self.get_logger().info(f'Heading to waypoint {idx + 1}/{len(self.waypoints)}')

    def run(self):
        self.get_logger().info('Waiting for the Nav2 follow_waypoints action server...')
        if not self.client.wait_for_server(timeout_sec=120.0):
            self.get_logger().error(
                'follow_waypoints unavailable. Is Nav2 up and its lifecycle active?')
            return 1

        self.get_logger().info('Sending the inspection route.')
        send = self.client.send_goal_async(self._build_goal(), feedback_callback=self._feedback)
        rclpy.spin_until_future_complete(self, send)
        handle = send.result()
        if handle is None or not handle.accepted:
            self.get_logger().error('Nav2 rejected the waypoint goal.')
            return 1

        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        res = result_future.result()

        if res.status == GoalStatus.STATUS_SUCCEEDED:
            missed = list(res.result.missed_waypoints)
            if missed:
                # Nav2 skips a waypoint it cannot reach rather than aborting, so
                # this is the only place a partially-completed route shows up.
                self.get_logger().warn(f'Route finished, but missed waypoints: {missed}')
            else:
                self.get_logger().info('Inspection route completed; every waypoint reached.')
            return 0

        self.get_logger().error(f'Route did not succeed (status {res.status}).')
        return 1


def main(args=None):
    rclpy.init(args=args)
    node = WaypointMission()
    code = 1
    try:
        code = node.run()
    except KeyboardInterrupt:
        code = 130
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(code)


if __name__ == '__main__':
    main()
