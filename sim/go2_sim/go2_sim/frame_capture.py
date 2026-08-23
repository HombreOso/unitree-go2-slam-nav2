#!/usr/bin/env python3
"""
Capture RGB frames at a fixed rate during an inspection run.

This is the hand-off from Module A (robotics) to Module B (AI). The paper
samples the video stream at 1 fps and embeds the capture timestamp in each
filename so that the report layer can reconstruct temporal context
(Sections 4.3 and 6); we do the same.

Beyond the frames themselves, this node writes a manifest recording, for every
frame, the robot pose in the map frame and which Table 1 hazards were actually
inside the camera frustum at that instant. That per-frame visibility is the
GROUND TRUTH the AI pipeline is scored against - the paper had human labelling
of a lab recording, and this is the simulation's equivalent. Deriving it from
geometry rather than by hand is what makes the whole benchmark reproducible.

A frame is labelled unsafe iff at least one hazard is visible in it.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import rclpy
import yaml
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

import tf2_ros

import cv2


class FrameCapture(Node):
    def __init__(self):
        super().__init__('frame_capture')

        self.declare_parameter('scenario', 'A')
        self.declare_parameter('run', 1)
        self.declare_parameter('rate_hz', 1.0)
        self.declare_parameter('output_root', '')
        self.declare_parameter('scenarios_yaml', '')
        self.declare_parameter('image_topic', '/camera/color/image_raw')
        # Camera frustum, matching the URDF's 87 deg horizontal FOV.
        self.declare_parameter('hfov_deg', 87.0)
        self.declare_parameter('max_range_m', 8.0)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', 'base_footprint')

        gp = lambda n: self.get_parameter(n).value
        self.scenario = str(gp('scenario')).upper()
        self.run_id = int(gp('run'))
        self.rate_hz = float(gp('rate_hz'))
        self.hfov = math.radians(float(gp('hfov_deg')))
        self.max_range = float(gp('max_range_m'))
        self.map_frame = gp('map_frame')
        self.base_frame = gp('base_frame')

        root = gp('output_root') or os.path.expanduser(
            '/mnt/c/Users/admin/Documents/Robotics/Naderi2026/unitree-go2-slam-nav2/data/runs')
        self.out_dir = Path(root) / f'scenario_{self.scenario}' / f'run_{self.run_id}'
        self.frames_dir = self.out_dir / 'frames'
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        self.hazards = self._load_hazards(gp('scenarios_yaml'))
        self.get_logger().info(
            f'Scenario {self.scenario} run {self.run_id}: '
            f'{len(self.hazards)} hazards, capturing at {self.rate_hz} Hz -> {self.frames_dir}')

        self.bridge = CvBridge()
        self.latest = None
        self.records = []
        self.index = 0
        self.t0 = None

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Camera images are best-effort in Gazebo; matching QoS avoids a silent
        # subscription mismatch that would leave us capturing nothing.
        qos = QoSProfile(depth=2, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Image, gp('image_topic'), self._on_image, qos)
        self.create_timer(1.0 / self.rate_hz, self._on_tick)

    # ------------------------------------------------------------------
    def _load_hazards(self, path):
        if not path:
            path = ('/mnt/c/Users/admin/Documents/Robotics/Naderi2026/'
                    'unitree-go2-slam-nav2/sim/go2_sim/config/scenarios.yaml')
        cfg = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
        scen = cfg['scenarios'][self.scenario]
        out = []
        for h in scen['hazards']:
            out.append({
                'id': h['id'],
                'category': h['category'],
                'violation': h['violation'],
                'osha_ref': h['osha_ref'],
                'osha_subpart': h['osha_subpart'],
                'x': float(h['pose'][0]),
                'y': float(h['pose'][1]),
            })
        return out

    def _on_image(self, msg):
        self.latest = msg

    # ------------------------------------------------------------------
    def _robot_pose(self):
        """Return (x, y, yaw) in the map frame, or None if TF is not ready."""
        try:
            tf = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time())
        except Exception:
            return None
        t = tf.transform.translation
        q = tf.transform.rotation
        # Yaw from quaternion.
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return t.x, t.y, math.atan2(siny, cosy)

    def _visible_hazards(self, x, y, yaw):
        """Hazards inside the camera frustum.

        Range and bearing only - there is no occlusion test. In an open lab
        with the hazards spread along the route this matches what the camera
        actually sees; it would need a ray test in a cluttered multi-room map.
        """
        seen = []
        half_fov = self.hfov / 2.0
        for h in self.hazards:
            dx, dy = h['x'] - x, h['y'] - y
            dist = math.hypot(dx, dy)
            if dist > self.max_range:
                continue
            bearing = math.atan2(dy, dx) - yaw
            bearing = math.atan2(math.sin(bearing), math.cos(bearing))
            if abs(bearing) <= half_fov:
                seen.append({
                    'id': h['id'],
                    'category': h['category'],
                    'violation': h['violation'],
                    'osha_ref': h['osha_ref'],
                    'distance_m': round(dist, 3),
                    'bearing_deg': round(math.degrees(bearing), 2),
                })
        return seen

    # ------------------------------------------------------------------
    def _on_tick(self):
        if self.latest is None:
            self.get_logger().warn('No camera frames yet.', throttle_duration_sec=5.0)
            return
        pose = self._robot_pose()
        if pose is None:
            self.get_logger().warn('Waiting for map->base TF.', throttle_duration_sec=5.0)
            return

        now = self.get_clock().now()
        if self.t0 is None:
            self.t0 = now
        elapsed = (now - self.t0).nanoseconds / 1e9

        try:
            frame = self.bridge.imgmsg_to_cv2(self.latest, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'cv_bridge failed: {exc}')
            return

        x, y, yaw = pose
        visible = self._visible_hazards(x, y, yaw)

        # Filename carries the timestamp, as in the paper's pipeline.
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        fname = f'{self.scenario}_r{self.run_id}_f{self.index:04d}_t{elapsed:07.2f}s_{stamp}.jpg'
        cv2.imwrite(str(self.frames_dir / fname), frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        self.records.append({
            'frame_index': self.index,
            'filename': fname,
            'elapsed_s': round(elapsed, 2),
            'utc': datetime.now(timezone.utc).isoformat(),
            'pose': {'x': round(x, 3), 'y': round(y, 3), 'yaw_rad': round(yaw, 4)},
            'visible_hazards': visible,
            # Ground truth: unsafe iff a real hazard was in view.
            'ground_truth': 'unsafe' if visible else 'safe',
        })
        self.index += 1
        if self.index % 10 == 0:
            n_unsafe = sum(1 for r in self.records if r['ground_truth'] == 'unsafe')
            self.get_logger().info(
                f'{self.index} frames captured ({n_unsafe} unsafe / {self.index - n_unsafe} safe)')

    # ------------------------------------------------------------------
    def write_manifest(self):
        if not self.records:
            self.get_logger().warn('No frames captured; manifest not written.')
            return
        n_unsafe = sum(1 for r in self.records if r['ground_truth'] == 'unsafe')
        manifest = {
            'scenario': self.scenario,
            'run': self.run_id,
            'source': 'gazebo_simulation',
            'sample_rate_hz': self.rate_hz,
            'camera': {'hfov_deg': math.degrees(self.hfov), 'max_range_m': self.max_range},
            'hazards_in_scenario': self.hazards,
            'totals': {
                'frames': len(self.records),
                'unsafe': n_unsafe,
                'safe': len(self.records) - n_unsafe,
            },
            'frames': self.records,
        }
        path = self.out_dir / 'manifest.json'
        path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        self.get_logger().info(
            f'Wrote {path} - {len(self.records)} frames '
            f'({n_unsafe} unsafe, {len(self.records) - n_unsafe} safe)')


def main(args=None):
    rclpy.init(args=args)
    node = FrameCapture()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.write_manifest()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
