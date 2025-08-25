import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    
    # Correctly find the path to our custom config file
    config = os.path.join(
        get_package_share_directory('rslidar_sdk'),
        'config',
        'dual_airy_config.yaml' # <--- This is our change
    )

    return LaunchDescription([
        Node(
            package='rslidar_sdk',
            executable='rslidar_sdk_node',
            name='rslidar_sdk_node',
            output='screen',
            parameters=[{'config_path': config}],
        )
    ])
