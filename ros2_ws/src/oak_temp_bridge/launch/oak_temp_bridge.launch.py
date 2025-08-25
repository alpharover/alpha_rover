from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='oak_temp_bridge',
            executable='oak_temp_bridge',
            name='oak_temp_bridge',
            output='screen',
            parameters=[{'namespaces': ['oak_d_pro', 'oak_d_sr']}],
        )
    ])

