from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('oak_nvblox_bringup')
    default_params = os.path.join(pkg_share, 'config', 'nvblox_from_oak.yaml')

    params_file = LaunchConfiguration('params_file')
    lidar_points_topic = LaunchConfiguration('lidar_points_topic')
    use_repack = LaunchConfiguration('use_repack')
    repack_output_topic = LaunchConfiguration('repack_output_topic')
    repack_flatten = LaunchConfiguration('repack_flatten')
    repack_out_frame = LaunchConfiguration('repack_out_frame')
    repack_angle_csv = LaunchConfiguration('repack_angle_csv')
    voxel_size = LaunchConfiguration('voxel_size')
    max_queue_len = LaunchConfiguration('max_queue_len')
    lidar_integrate_hz = LaunchConfiguration('lidar_integrate_hz')
    streamer_mbps = LaunchConfiguration('streamer_mbps')
    repack_throttle_n = LaunchConfiguration('repack_throttle_n')

    repack = ExecuteProcess(
        cmd=[
            'python3', '-m', 'lidar_tools.pc_repack',
            '--input', LaunchConfiguration('lidar_points_topic'),
            '--output', repack_output_topic,
            '--flatten', repack_flatten,
            '--out-frame', repack_out_frame,
            '--angle-csv', repack_angle_csv,
        ],
        output='screen',
        condition=IfCondition(use_repack),
    )

    # C++ reordering node (faster than Python)
    repack_cpp = Node(
        package='lidar_tools_cpp',
        executable='pc_reorder',
        name='pc_reorder',
        output='screen',
        parameters=[
            {'input_topic': lidar_points_topic},
            {'output_topic': repack_output_topic},
            {'out_frame': repack_out_frame},
            {'angle_csv': repack_angle_csv},
            {'throttle_n': repack_throttle_n},
            {'qos_depth': 1},
        ],
        condition=IfCondition(LaunchConfiguration('use_cpp_repack')),
    )

    # Common parameter set for both raw and repacked pipelines
    common_params = [
        params_file,
        {
            # Inputs
            'use_color': False,
            'use_depth': False,
            'use_lidar': True,
            'num_cameras': 0,

            # Airy intrinsics
            'lidar_width': 900,
            'lidar_height': 96,
            'use_non_equal_vertical_fov_lidar_params': True,
            # Asymmetric vertical FOV: Airy scans 0..+90 deg (upward hemisphere)
            # NVBlox requires this to be strictly negative; Airy doesn't scan below 0,
            # so use a tiny negative to pass the check without filtering anything.
            'min_angle_below_zero_elevation_rad': -0.001,
            'max_angle_above_zero_elevation_rad': 1.5707963,

            # Ranges (per spec)
            'lidar_min_valid_range_m': 0.10,
            'lidar_max_valid_range_m': 60.0,

            # Frames / TF
            'use_tf_transforms': True,
            'global_frame': 'base_link',  # keep local mapping; swap to 'map' when odom/map are available
            'pose_frame': 'base_link',
            'map_clearing_frame_id': 'base_link',

            # QoS + rates / buffering
            'input_qos': 'SENSOR_DATA',
            'integrate_lidar_rate_hz': lidar_integrate_hz,
            'maximum_input_queue_length': max_queue_len,
            'print_queue_drops_to_console': True,

            # Visualization / debug
            'voxel_size': voxel_size,
            'esdf_mode': '3d',
            'layer_visualization_min_tsdf_weight': 0.0,
            'layer_visualization_exclusion_radius_m': 0.0,
            'layer_visualization_exclusion_height_m': 0.0,
            'layer_streamer_bandwidth_limit_mbps': streamer_mbps,
            'print_rates_to_console': True,
            'print_delays_to_console': True,

            # Increase LiDAR integration distances for mapping larger spaces
            'static_mapper.lidar_projective_integrator_max_integration_distance_m': 25.0,
            'dynamic_mapper.lidar_projective_integrator_max_integration_distance_m': 25.0,
        },
    ]

    nvblox_repacked = Node(
        package='nvblox_ros',
        executable='nvblox_node',
        name='nvblox_node',
        output='screen',
        parameters=common_params,
        remappings=[('pointcloud', repack_output_topic)],
        condition=IfCondition(use_repack),
    )

    nvblox_raw = Node(
        package='nvblox_ros',
        executable='nvblox_node',
        name='nvblox_node',
        output='screen',
        parameters=common_params,
        remappings=[('pointcloud', lidar_points_topic)],
        condition=UnlessCondition(use_repack),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Path to nvblox parameters YAML.'
        ),
        DeclareLaunchArgument('voxel_size', default_value='0.30',
                              description='NVBlox voxel size in meters (set at node start).'),
        DeclareLaunchArgument('max_queue_len', default_value='3',
                              description='NVBlox maximum_input_queue_length (favor low latency).'),
        DeclareLaunchArgument('lidar_integrate_hz', default_value='5.0',
                              description='NVBlox integrate_lidar_rate_hz to limit work.'),
        DeclareLaunchArgument('streamer_mbps', default_value='3.0',
                              description='Limit layer streamer bandwidth for markers.'),
        DeclareLaunchArgument('lidar_points_topic', default_value='/airy_201/rslidar_points',
                              description='Raw LiDAR point cloud topic'),
        DeclareLaunchArgument('use_repack', default_value='true',
                              description='Enable point cloud repacking'),
        DeclareLaunchArgument('use_cpp_repack', default_value='true',
                              description='Use fast C++ row reorder instead of Python repack'),
        DeclareLaunchArgument('repack_output_topic', default_value='/airy_201/repacked_points',
                              description='Output topic for repacked cloud'),
        DeclareLaunchArgument('repack_flatten', default_value='false',
                              description='Flatten organized cloud to height=1'),
        DeclareLaunchArgument('repack_out_frame', default_value='airy_rear',
                              description='Override frame_id in repacked output'),
        DeclareLaunchArgument('repack_angle_csv', default_value='',
                              description='CSV with per-channel vertical angles to reorder rows'),
        DeclareLaunchArgument('repack_throttle_n', default_value='2',
                              description='Forward every Nth frame in C++ repack to reduce load'),
        repack,
        repack_cpp,
        nvblox_repacked,
        nvblox_raw,
    ])
