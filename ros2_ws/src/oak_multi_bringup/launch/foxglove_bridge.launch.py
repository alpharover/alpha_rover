from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('oak_multi_bringup')
    default_params = os.path.join(pkg_share, 'config', 'foxglove_qos.yaml')

    params_file = LaunchConfiguration('params_file')
    port = LaunchConfiguration('port')

    bridge = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        output='screen',
        parameters=[params_file, {'port': port}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Path to foxglove_bridge QoS params (includes best-effort for point clouds).',
        ),
        DeclareLaunchArgument(
            'port', default_value='8765',
            description='WebSocket port for foxglove_bridge',
        ),
        bridge,
    ])

