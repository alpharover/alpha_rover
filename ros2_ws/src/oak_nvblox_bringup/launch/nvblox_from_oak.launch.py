from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('oak_nvblox_bringup')
    default_params = os.path.join(pkg_share, 'config', 'nvblox_from_oak.yaml')

    params_file = LaunchConfiguration('params_file')
    depth_topic = LaunchConfiguration('depth_topic')
    depth_info_topic = LaunchConfiguration('depth_info_topic')
    color_topic = LaunchConfiguration('color_topic')
    color_info_topic = LaunchConfiguration('color_info_topic')

    nvblox = Node(
        package='nvblox_ros',
        executable='nvblox_node',
        name='nvblox_node',
        output='screen',
        parameters=[params_file, {'use_color': False}],
        remappings=[
            # nvblox expects these generic inputs per camera index 0
            ('camera_0/depth/image', depth_topic),
            ('camera_0/depth/camera_info', depth_info_topic),
            # omit color remaps when not using color
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Path to nvblox parameters YAML.'
        ),
        DeclareLaunchArgument(
            'depth_topic',
            default_value='/oak_d_pro/camera/stereo/image_raw',
            description='Depth image topic (16UC1 or 32FC1).'
        ),
        DeclareLaunchArgument(
            'depth_info_topic',
            default_value='/oak_d_pro/camera/stereo/camera_info',
            description='Depth camera_info topic.'
        ),
        # Color topics are optional; if needed, add remaps back via this launch file
        nvblox,
    ])
