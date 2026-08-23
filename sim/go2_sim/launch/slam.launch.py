#!/usr/bin/env python3
"""
SLAM for the inspection runs.

Two backends:

  backend:=rtabmap       (default) Reproduces Section 4.2 of the paper:
                         icp_odometry estimates motion by ICP-aligning
                         successive LiDAR clouds, rtabmap builds the map and
                         detects loop closures, and RGB-D + IMU are fused in to
                         improve both. This is the configuration the paper ran.

  backend:=slam_toolbox  A 2D-scan fallback. Much cheaper, and worth having
                         because this machine renders Gazebo in software with
                         no GPU - if RTAB-Map cannot keep up, this still yields
                         the occupancy grid Nav2 needs to plan on.

Either way the output contract is the same: a /map occupancy grid plus a
map->odom transform.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    backend = LaunchConfiguration('backend')
    localization = LaunchConfiguration('localization')

    is_rtabmap = IfCondition(PythonExpression(["'", backend, "' == 'rtabmap'"]))
    is_toolbox = UnlessCondition(PythonExpression(["'", backend, "' == 'rtabmap'"]))

    # Shared RTAB-Map settings. Keys are RTAB-Map's own parameter names.
    rtabmap_params = {
        'use_sim_time': use_sim_time,
        'frame_id': 'base_footprint',
        'odom_frame_id': 'odom',
        'map_frame_id': 'map',
        'subscribe_depth': True,
        'subscribe_rgb': True,
        'subscribe_scan_cloud': True,
        'approx_sync': True,
        'sync_queue_size': 30,
        'qos_image': 2,          # best-effort, matching the Gazebo camera
        'qos_scan': 2,
        'wait_for_transform': 0.4,
        # Grid built from the LiDAR cloud rather than the depth image: longer
        # range and a cleaner floor separation for Nav2's costmap.
        'Grid/FromDepth': 'false',
        'Grid/RayTracing': 'true',
        'Grid/3D': 'false',
        'Grid/CellSize': '0.05',
        'Grid/MaxObstacleHeight': '1.2',
        'Grid/MaxGroundHeight': '0.12',
        'Grid/RangeMax': '18.0',
        # Loop closure. The lab has repetitive concrete walls, so a strict
        # inlier requirement avoids false closures folding the map onto itself.
        'Rtabmap/DetectionRate': '1.0',
        'RGBD/OptimizeFromGraphEnd': 'false',
        'RGBD/ProximityBySpace': 'true',
        'RGBD/AngularUpdate': '0.05',
        'RGBD/LinearUpdate': '0.05',
        'Vis/MinInliers': '18',
        'Reg/Strategy': '1',      # 1 = ICP, matching the paper's LiDAR pipeline
        'Reg/Force3DoF': 'true',  # planar lab; locks roll/pitch/z
        'Icp/VoxelSize': '0.08',
        'Icp/MaxCorrespondenceDistance': '0.5',
        'Icp/PointToPlane': 'true',
        'Icp/Iterations': '18',
        'Optimizer/Strategy': '1',
    }

    remaps = [
        ('scan_cloud', '/rslidar_points'),
        ('rgb/image', '/camera/color/image_raw'),
        ('rgb/camera_info', '/camera/color/camera_info'),
        ('depth/image', '/camera/color/depth/image_raw'),
        ('imu', '/imu/data'),
    ]

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('backend', default_value='rtabmap',
                              description="'rtabmap' (as in the paper) or 'slam_toolbox'."),
        DeclareLaunchArgument('localization', default_value='false',
                              description='true replays a prebuilt map without updating it.'),
        DeclareLaunchArgument('rtabmap_db',
                              default_value='/root/.ros/go2_inspection.db'),

        # ---------------- RTAB-Map ----------------
        # ICP odometry: motion from point-cloud alignment, exactly the
        # icp_odometry node named in Section 4.2.
        Node(condition=is_rtabmap,
             package='rtabmap_odom', executable='icp_odometry', output='screen',
             parameters=[{
                 'use_sim_time': use_sim_time,
                 'frame_id': 'base_footprint',
                 'odom_frame_id': 'odom',
                 'publish_tf': True,
                 'wait_for_transform': 0.4,
                 'qos_scan': 2,
                 'expected_update_rate': 0.0,
                 'Icp/VoxelSize': '0.10',
                 'Icp/MaxCorrespondenceDistance': '0.6',
                 'Icp/PointToPlane': 'true',
                 'Icp/Iterations': '12',
                 'Icp/Epsilon': '0.002',
                 'Odom/Strategy': '0',
                 'Odom/ResetCountdown': '10',
                 'Odom/GuessMotion': 'true',
                 'Reg/Force3DoF': 'true',
             }],
             remappings=[('scan_cloud', '/rslidar_points'), ('imu', '/imu/data')]),

        Node(condition=is_rtabmap,
             package='rtabmap_slam', executable='rtabmap', output='screen',
             parameters=[rtabmap_params],
             remappings=remaps,
             # -d clears the database so each run starts from a blank map;
             # without it RTAB-Map would silently resume the previous run.
             arguments=['-d', '--delete_db_on_start']),

        # ---------------- slam_toolbox fallback ----------------
        Node(condition=is_toolbox,
             package='slam_toolbox', executable='async_slam_toolbox_node',
             name='slam_toolbox', output='screen',
             parameters=[{
                 'use_sim_time': use_sim_time,
                 'odom_frame': 'odom',
                 'map_frame': 'map',
                 'base_frame': 'base_footprint',
                 'scan_topic': '/scan',
                 'mode': 'mapping',
                 'resolution': 0.05,
                 'max_laser_range': 20.0,
                 'minimum_travel_distance': 0.15,
                 'minimum_travel_heading': 0.15,
                 'transform_publish_period': 0.05,
                 'do_loop_closing': True,
                 'loop_search_maximum_distance': 4.0,
             }]),
    ])
