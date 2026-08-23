#!/usr/bin/env python3
"""
Nav2 for the inspection runs.

Brings up the planner (Dijkstra via NavFn), the DWB controller, costmaps,
behaviours and the waypoint follower, then activates the lifecycle nodes.

No map_server and no AMCL: SLAM already publishes /map and map->odom.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('go2_sim')
    default_params = os.path.join(pkg, 'config', 'nav2_sim_params.yaml')

    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')

    lifecycle_nodes = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother',
    ]

    common = [params_file, {'use_sim_time': use_sim_time}]

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        Node(package='nav2_controller', executable='controller_server',
             output='screen', parameters=common,
             # The controller's output goes through cmd_vel_bridge, mirroring
             # the real robot, where go2_cmd_processor sits between Nav2 and
             # the Unitree SDK.
             remappings=[('cmd_vel', 'cmd_vel_nav')]),

        Node(package='nav2_smoother', executable='smoother_server',
             name='smoother_server', output='screen', parameters=common),

        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen', parameters=common),

        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen', parameters=common),

        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen', parameters=common),

        Node(package='nav2_waypoint_follower', executable='waypoint_follower',
             name='waypoint_follower', output='screen', parameters=common),

        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             name='velocity_smoother', output='screen', parameters=common,
             remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')]),

        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[{'use_sim_time': use_sim_time,
                          'autostart': True,
                          'node_names': lifecycle_nodes}]),
    ])
