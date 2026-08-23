#!/usr/bin/env python3
"""
Bring up Gazebo with a construction-site scenario world and spawn the Go2.

Starts: gzserver (+ optional gzclient), robot_state_publisher, the robot spawn,
the cmd_vel bridge that stands in for go2_cmd_processor, and
pointcloud_to_laserscan (Nav2's costmaps and the lighter SLAM backend both want
a 2D scan, while the paper's RTAB-Map configuration consumes the full cloud).
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = get_package_share_directory('go2_sim')

    scenario = LaunchConfiguration('scenario')
    gui = LaunchConfiguration('gui')
    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_odom_tf = LaunchConfiguration('publish_odom_tf')
    lidar_beams = LaunchConfiguration('lidar_beams')
    lidar_samples = LaunchConfiguration('lidar_samples')

    world = PathJoinSubstitution([
        pkg, 'worlds', ['construction_scenario_', scenario, '.world']])

    xacro_file = os.path.join(pkg, 'urdf', 'go2_sim.urdf.xacro')
    # ParameterValue(..., value_type=str) is required: without it the launch
    # system tries to parse the expanded URDF as YAML and fails.
    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' publish_odom_tf:=', publish_odom_tf,
            ' lidar_beams:=', lidar_beams,
            ' lidar_samples:=', lidar_samples,
        ]),
        value_type=str)

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('gazebo_ros'), 'launch', 'gzserver.launch.py'])),
        launch_arguments={'world': world, 'verbose': 'true',
                          'pause': 'false'}.items())

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('gazebo_ros'), 'launch', 'gzclient.launch.py'])),
        condition=IfCondition(gui))

    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='A',
                              description='Scenario to load: A, B or C.'),
        DeclareLaunchArgument('gui', default_value='false',
                              description='Run the Gazebo GUI. Off by default: '
                                          'software rendering makes it very slow.'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('publish_odom_tf', default_value='false',
                              description='false when icp_odometry owns odom->base.'),
        DeclareLaunchArgument('lidar_beams', default_value='16'),
        DeclareLaunchArgument('lidar_samples', default_value='440'),
        DeclareLaunchArgument('x', default_value='1.2'),
        DeclareLaunchArgument('y', default_value='1.2'),
        DeclareLaunchArgument('yaw', default_value='0.0'),

        gzserver,
        gzclient,

        Node(package='robot_state_publisher', executable='robot_state_publisher',
             output='screen',
             parameters=[{'use_sim_time': use_sim_time,
                          'robot_description': robot_description}]),

        # Delayed: /spawn_entity only exists once gzserver has finished loading
        # the world, and these worlds are ~100 links of primitives under
        # software rendering. Spawning immediately loses the race.
        TimerAction(period=10.0, actions=[
            Node(package='gazebo_ros', executable='spawn_entity.py',
                 output='screen',
                 arguments=['-topic', 'robot_description', '-entity', 'go2',
                            '-x', LaunchConfiguration('x'),
                            '-y', LaunchConfiguration('y'),
                            '-z', '0.05',
                            '-Y', LaunchConfiguration('yaw'),
                            '-spawn_service_timeout', '180.0']),
        ]),

        Node(package='go2_sim', executable='cmd_vel_bridge', output='screen',
             parameters=[{'use_sim_time': use_sim_time}]),

        # Flatten the Helios-32 cloud into a 2D scan. The height slice ignores
        # the floor and anything above the robot, keeping only what it could
        # actually collide with.
        Node(package='pointcloud_to_laserscan',
             executable='pointcloud_to_laserscan_node',
             name='pointcloud_to_laserscan',
             output='screen',
             remappings=[('cloud_in', '/rslidar_points'), ('scan', '/scan')],
             parameters=[{
                 'use_sim_time': use_sim_time,
                 'target_frame': 'base_footprint',
                 'transform_tolerance': 0.05,
                 'min_height': -0.20,
                 'max_height': 0.90,
                 'angle_min': -3.14159,
                 'angle_max': 3.14159,
                 'angle_increment': 0.0087,
                 'scan_time': 0.2,
                 'range_min': 0.25,
                 'range_max': 25.0,
                 'use_inf': True,
             }]),
    ])
