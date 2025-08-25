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
    # Camera 0 (OAK-D Pro)
    depth0_topic = LaunchConfiguration('depth0_topic')
    depth0_info_topic = LaunchConfiguration('depth0_info_topic')
    # Camera 1 (OAK-D SR)
    depth1_topic = LaunchConfiguration('depth1_topic')
    depth1_info_topic = LaunchConfiguration('depth1_info_topic')
    # LiDAR
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
                'num_cameras': 2,
                'lidar_min_valid_range_m': lidar_min_range,
                'lidar_max_valid_range_m': lidar_max_range,
            },
        ],
        remappings=[
            # Cameras
            ('camera_0/depth/image', depth0_topic),
            ('camera_0/depth/camera_info', depth0_info_topic),
            ('camera_1/depth/image', depth1_topic),
            ('camera_1/depth/camera_info', depth1_info_topic),
            # LiDAR
            ('pointcloud', lidar_points_topic),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params,
                              description='Path to nvblox parameters YAML.'),
        # Camera 0 (Pro)
        DeclareLaunchArgument('depth0_topic', default_value='/oak_d_pro/camera/stereo/image_raw'),
        DeclareLaunchArgument('depth0_info_topic', default_value='/oak_d_pro/camera/stereo/camera_info'),
        # Camera 1 (SR)
        DeclareLaunchArgument('depth1_topic', default_value='/oak_d_sr/camera/stereo/image_raw'),
        DeclareLaunchArgument('depth1_info_topic', default_value='/oak_d_sr/camera/stereo/camera_info'),
        # LiDAR
        DeclareLaunchArgument('lidar_points_topic', default_value='/airy_200/rslidar_points'),
        DeclareLaunchArgument('lidar_min_valid_range_m', default_value='0.25'),
        DeclareLaunchArgument('lidar_max_valid_range_m', default_value='40.0'),
        nvblox,
    ])

