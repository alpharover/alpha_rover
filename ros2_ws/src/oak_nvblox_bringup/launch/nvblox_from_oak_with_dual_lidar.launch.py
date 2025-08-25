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
    front_lidar_topic = LaunchConfiguration('front_lidar_topic')
    rear_lidar_topic = LaunchConfiguration('rear_lidar_topic')
    merged_topic = LaunchConfiguration('merged_topic')
    lidar_min_range = LaunchConfiguration('lidar_min_valid_range_m')
    lidar_max_range = LaunchConfiguration('lidar_max_valid_range_m')
    target_frame = LaunchConfiguration('target_frame')

    merger = Node(
        package='oak_nvblox_bringup',
        executable='pointcloud_merge.py',
        name='pointcloud_merge',
        output='screen',
        parameters=[
            {
                'front_topic': front_lidar_topic,
                'rear_topic': rear_lidar_topic,
                'output_topic': merged_topic,
                'target_frame': target_frame,
                'publish_rate_hz': 20.0,
            }
        ],
    )

    nvblox = Node(
        package='nvblox_ros',
        executable='nvblox_node',
        name='nvblox_node',
        output='screen',
        parameters=[
            params_file,
            {
                'use_color': False,
                'use_lidar': True,
                'num_cameras': 1,
                'lidar_min_valid_range_m': lidar_min_range,
                'lidar_max_valid_range_m': lidar_max_range,
            },
        ],
        remappings=[
            ('camera_0/depth/image', depth_topic),
            ('camera_0/depth/camera_info', depth_info_topic),
            ('pointcloud', merged_topic),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('depth_topic', default_value='/oak_d_pro/camera/stereo/image_raw'),
        DeclareLaunchArgument('depth_info_topic', default_value='/oak_d_pro/camera/stereo/camera_info'),
        DeclareLaunchArgument('front_lidar_topic', default_value='/airy_200/rslidar_points'),
        DeclareLaunchArgument('rear_lidar_topic', default_value='/airy_201/rslidar_points'),
        DeclareLaunchArgument('merged_topic', default_value='/merged/lidar_points'),
        DeclareLaunchArgument('target_frame', default_value='base_link'),
        DeclareLaunchArgument('lidar_min_valid_range_m', default_value='0.25'),
        DeclareLaunchArgument('lidar_max_valid_range_m', default_value='40.0'),
        merger,
        nvblox,
    ])

