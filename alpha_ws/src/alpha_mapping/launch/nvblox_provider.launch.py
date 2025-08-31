from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='alpha_mapping',
            executable='mapping_node',
            name='alpha_mapping_provider',
            parameters=[{
                'config': 'alpha_configs/mapping_provider.yaml',
                'provider_plugin': 'alpha_mapping/NvbloxProvider',
            }],
            output='screen',
        )
    ])

