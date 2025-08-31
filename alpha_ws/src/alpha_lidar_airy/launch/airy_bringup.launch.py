from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition

import os
import yaml


def _load_network_cfg(path: str):
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _rslidar(ns: str, config_path: str, frame_id: str):
    return Node(
        package='rslidar_sdk',
        executable='rslidar_sdk_node',
        namespace=ns,
        parameters=[{
            'config_path': config_path,
        }],
        remappings=[
            ('/rslidar_points', f'/alpha/lidar/{ns}/points_raw'),
        ],
        output='screen',
    )


def generate_launch_description():
    # Optional overrides for absolute config paths
    config_front_arg = DeclareLaunchArgument('config_front', default_value='')
    config_rear_arg = DeclareLaunchArgument('config_rear', default_value='')
    start_mode_service_arg = DeclareLaunchArgument('start_mode_service', default_value='false')
    backend_arg = DeclareLaunchArgument('backend', default_value='cpp')
    cfg_front_override = LaunchConfiguration('config_front')
    cfg_rear_override = LaunchConfiguration('config_rear')
    start_mode_service = LaunchConfiguration('start_mode_service')
    # Resolve network config relative to workspace root if a relative path
    cfg_path = os.environ.get('ALPHA_NETWORK_CONFIG', 'alpha_configs/network.yaml')
    net = _load_network_cfg(cfg_path)
    front = net.get('lidar', {}).get('front', {})
    rear = net.get('lidar', {}).get('rear', {})

    # Resolve lidar_airy config robustly
    cfg_candidates = [
        os.environ.get('ALPHA_LIDAR_AIRY_CONFIG', ''),
        'alpha_configs/lidar_airy.yaml',
        os.path.join(os.getcwd(), 'alpha_configs', 'lidar_airy.yaml'),
        os.path.join(os.path.expanduser('~'), 'alpha_rover', 'alpha_configs', 'lidar_airy.yaml'),
    ]
    cfg_candidates = [c for c in cfg_candidates if c]
    lidar_cfg = next((os.path.abspath(c) for c in cfg_candidates if os.path.isfile(c)), cfg_candidates[0])

    # Resolve rslidar SDK config files (front/rear)
    # Resolve with overrides first
    front_override = os.environ.get('ALPHA_RSLIDAR_FRONT', '')
    rear_override = os.environ.get('ALPHA_RSLIDAR_REAR', '')
    candidates_front = [
        str(cfg_front_override) if str(cfg_front_override) else '',
        front_override,
        'alpha_configs/lidar_rslidar/front.yaml',
        os.path.join(os.getcwd(), 'alpha_configs', 'lidar_rslidar', 'front.yaml'),
        os.path.join(os.path.expanduser('~'), 'alpha_rover', 'alpha_configs', 'lidar_rslidar', 'front.yaml'),
    ]
    candidates_rear = [
        str(cfg_rear_override) if str(cfg_rear_override) else '',
        rear_override,
        'alpha_configs/lidar_rslidar/rear.yaml',
        os.path.join(os.getcwd(), 'alpha_configs', 'lidar_rslidar', 'rear.yaml'),
        os.path.join(os.path.expanduser('~'), 'alpha_rover', 'alpha_configs', 'lidar_rslidar', 'rear.yaml'),
    ]
    rsl_front = next((os.path.abspath(p) for p in candidates_front if p and os.path.isfile(p)), 'alpha_configs/lidar_rslidar/front.yaml')
    rsl_rear = next((os.path.abspath(p) for p in candidates_rear if p and os.path.isfile(p)), 'alpha_configs/lidar_rslidar/rear.yaml')

    # Resolve network config for mode service (absolute best-effort)
    net_candidates = [
        os.environ.get('ALPHA_NETWORK_CONFIG', ''),
        'alpha_configs/network.yaml',
        os.path.join(os.getcwd(), 'alpha_configs', 'network.yaml'),
        os.path.join(os.path.expanduser('~'), 'alpha_rover', 'alpha_configs', 'network.yaml'),
    ]
    net_cfg = next((os.path.abspath(p) for p in net_candidates if p and os.path.isfile(p)), net_candidates[1])

    nodes = [
        config_front_arg, config_rear_arg, start_mode_service_arg, backend_arg,
        _rslidar('front', rsl_front, 'alpha_lidar_front'),
        _rslidar('rear',  rsl_rear,  'alpha_lidar_rear'),
        Node(
            package='alpha_lidar_airy',
            executable='mode_service_node',
            name='mode_service_node',
            parameters=[{
                'network_config': net_cfg,
                'http_enabled': True,
            }],
            output='screen',
            condition=IfCondition(start_mode_service),
        ),
        Node(
            package='alpha_lidar_airy',
            executable='reorder_node',
            name='reorder_node',
            parameters=[{
                'config': lidar_cfg,
                'range_gate_enabled': False,
                'backend': LaunchConfiguration('backend'),
                'timestamp_policy': 'sensor',
            }],
            output='screen',
            condition=IfCondition(PythonExpression(["'", LaunchConfiguration('backend'), "' != 'cpp' "]))
        ),
        Node(
            package='alpha_lidar_airy_cpp',
            executable='reorder_node_cpp',
            name='reorder_node_cpp',
            parameters=[{
                'config': lidar_cfg,
                'input_front_topic': '/alpha/lidar/front/points_raw',
                'input_rear_topic': '/alpha/lidar/rear/points_raw',
                'timestamp_policy': 'sensor',
            }],
            output='screen',
            condition=IfCondition(PythonExpression(["'", LaunchConfiguration('backend'), "' == 'cpp' "]))
        ),
    ]

    return LaunchDescription(nodes)
