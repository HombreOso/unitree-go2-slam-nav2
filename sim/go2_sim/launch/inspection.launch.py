#!/usr/bin/env python3
"""
Full Module A run: Gazebo + SLAM + Nav2 + frame capture, for one scenario.

    ros2 launch go2_sim inspection.launch.py scenario:=A run:=1

Startup is staged rather than simultaneous. Nav2's costmaps refuse to configure
until /map and the TF tree exist, and frame capture needs map->base_footprint
before it can label a frame, so each layer waits for the one beneath it. On a
software-rendered machine those waits need to be generous.

The waypoint mission is NOT started here - run it separately (or via
scripts/run_scenario.sh) once you can see that SLAM has converged.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('go2_sim')
    launch_dir = os.path.join(pkg, 'launch')

    scenario = LaunchConfiguration('scenario')
    run = LaunchConfiguration('run')
    backend = LaunchConfiguration('slam_backend')
    gui = LaunchConfiguration('gui')
    output_root = LaunchConfiguration('output_root')

    # slam_toolbox does not estimate odometry, so Gazebo has to supply
    # odom->base_footprint in that mode. With RTAB-Map, icp_odometry owns it.
    publish_odom_tf = PythonExpression(
        ["'false' if '", backend, "' == 'rtabmap' else 'true'"])

    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='A'),
        DeclareLaunchArgument('run', default_value='1'),
        DeclareLaunchArgument('slam_backend', default_value='rtabmap',
                              description="'rtabmap' (paper) or 'slam_toolbox' (light)."),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('capture_rate', default_value='1.0',
                              description='Frame sampling rate; the paper uses 1 fps.'),
        DeclareLaunchArgument('output_root', default_value=''),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'gazebo.launch.py')),
            launch_arguments={'scenario': scenario,
                              'gui': gui,
                              'publish_odom_tf': publish_odom_tf}.items()),

        # Let Gazebo spawn the robot and start publishing sensors first.
        TimerAction(period=12.0, actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(launch_dir, 'slam.launch.py')),
                launch_arguments={'backend': backend}.items()),
        ]),

        # Nav2 needs /map from SLAM before its costmaps will configure.
        TimerAction(period=30.0, actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(launch_dir, 'nav.launch.py'))),
        ]),

        TimerAction(period=40.0, actions=[
            Node(package='go2_sim', executable='frame_capture', output='screen',
                 parameters=[{
                     'use_sim_time': True,
                     'scenario': scenario,
                     'run': run,
                     'rate_hz': LaunchConfiguration('capture_rate'),
                     'output_root': output_root,
                 }]),
        ]),
    ])
