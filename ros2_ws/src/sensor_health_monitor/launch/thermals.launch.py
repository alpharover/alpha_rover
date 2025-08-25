from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='sensor_health_monitor',
            executable='jetson_thermals',
            name='jetson_thermals',
            output='screen',
            parameters=[{'rate_hz': 1.0, 'warn_c': 80.0, 'error_c': 90.0}],
        )
    ])

