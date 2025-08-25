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
    lidar_points_topic = LaunchConfiguration('lidar_points_topic')
    lidar_min_range = LaunchConfiguration('lidar_min_valid_range_m')
    lidar_max_range = LaunchConfiguration('lidar_max_valid_range_m')

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
            # Cameras
            ('camera_0/depth/image', depth_topic),
            ('camera_0/depth/camera_info', depth_info_topic),
            # LiDAR
            ('pointcloud', lidar_points_topic),
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
        DeclareLaunchArgument(
            'lidar_points_topic',
            default_value='/airy_200/rslidar_points',
            description='LiDAR point cloud topic to fuse into nvblox.'
        ),
        DeclareLaunchArgument(
            'lidar_min_valid_range_m',
            default_value='0.25',
            description='Minimum valid LiDAR range (meters).'
        ),
        DeclareLaunchArgument(
            'lidar_max_valid_range_m',
            default_value='40.0',
            description='Maximum valid LiDAR range (meters).'
        ),
        nvblox,
    ])
