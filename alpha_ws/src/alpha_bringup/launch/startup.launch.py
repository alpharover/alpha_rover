from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os


def _abs(path: str) -> str:
    candidates = [
        path,
        os.path.join(os.getcwd(), path) if not os.path.isabs(path) else path,
        os.path.join(os.path.expanduser('~'), 'alpha_rover', path) if not os.path.isabs(path) else path,
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    return path


def generate_launch_description():
    config_dir = LaunchConfiguration('config_dir')
    return LaunchDescription([
        DeclareLaunchArgument('config_dir', default_value='alpha_configs'),

        # Config Manager: serves /alpha/config/get
        Node(
            package='alpha_bringup',
            executable='config_manager',
            name='alpha_config_manager',
            parameters=[{'config_dir': config_dir}],
            output='screen',
        ),

        # Startup Sequencer: dry-run by default
        Node(
            package='alpha_bringup',
            executable='startup_sequencer',
            name='alpha_startup_sequencer',
            parameters=[{
                'sequence_config': _abs('alpha_configs/startup_sequence.yaml'),
                'dry_run': True,
            }],
            output='screen',
        ),

        # LiDAR mode service (dry-run unless http_enabled:=true)
        Node(
            package='alpha_lidar_airy',
            executable='mode_service_node',
            name='alpha_airy_mode_service',
            parameters=[{
                'network_config': _abs('alpha_configs/network.yaml'),
                'http_enabled': False,
            }],
            output='screen',
        ),

        # LiDAR reorder node
        Node(
            package='alpha_lidar_airy',
            executable='reorder_node',
            name='alpha_airy_reorder',
            parameters=[{
                'config': _abs('alpha_configs/lidar_airy.yaml'),
                'input_front_topic': '/alpha/lidar/front/points_raw',
                'input_rear_topic': '/alpha/lidar/rear/points_raw',
                'backend': 'numpy',
                'timestamp_policy': 'sensor',
                'target_rate_hz': 0.0,
                }],
            output='screen',
        ),

        # LiDAR ready gate (publishes /alpha/gates/lidar_ready)
        Node(
            package='alpha_bringup',
            executable='lidar_ready_gate',
            name='alpha_lidar_ready_gate',
            parameters=[{
                'warmup_s': 10.0,
                'window_s': 3.0,
                'min_rate_hz': 9.0,
                'flip_low_hz': 8.0,
                'front_topic': '/alpha/lidar/front/points',
                'rear_topic': '/alpha/lidar/rear/points',
            }],
            output='screen',
        ),

        # Time sync preflight gate (skeleton)
        Node(
            package='alpha_time_sync',
            executable='preflight_gate',
            name='alpha_time_sync_gate',
            parameters=[{
                'always_ok': True,
                'enforce': False,
                'bounds_config': _abs('alpha_configs/calibration_bounds.yaml'),
                'nominal_extrinsics': _abs('alpha_configs/extrinsics_seed.yaml'),
                'current_extrinsics': _abs('alpha_configs/extrinsics_current.yaml'),
                'compare_from_config': True,
            }],
            output='screen',
        ),

        # TF preflight (skeleton)
        Node(
            package='alpha_calibration_tools',
            executable='tf_ok',
            name='alpha_tf_ok',
            parameters=[{
                'always_ok': True,
                'enforce': False,
                'bounds_config': _abs('alpha_configs/calibration_bounds.yaml'),
                'nominal_extrinsics': _abs('alpha_configs/extrinsics_seed.yaml'),
                'current_extrinsics': _abs('alpha_configs/extrinsics_current.yaml'),
                'compare_from_config': True,
            }],
            output='screen',
        ),

        # Mode manager (skeleton)
        Node(
            package='alpha_mode_manager',
            executable='mode_manager',
            name='alpha_mode_manager',
            parameters=[{
                'modes_config': _abs('alpha_configs/modes.yaml'),
                'enforce_guards': True,
            }],
            output='screen',
        ),

        # Orchestrator (skeleton)
        Node(
            package='alpha_orchestrator',
            executable='orchestrator',
            name='alpha_orchestrator',
            parameters=[{
                'config_failure_domains': _abs('alpha_configs/failure_domains.yaml'),
                'dry_run': True,
            }],
            output='screen',
        ),

        # Observability SLO publisher
        Node(
            package='alpha_observability',
            executable='slo_publisher',
            name='alpha_slo_publisher',
            parameters=[{
                'degrade_config': _abs('alpha_configs/degrade_policies.yaml'),
                'publish_period_sec': 1.0,
                'window_size': 200,
            }],
            output='screen',
        ),
    

        # Comms degrade manager
        Node(
            package='alpha_comms',
            executable='degrade_manager',
            name='alpha_degrade_manager',
            parameters=[{
                'degrade_config': _abs('alpha_configs/degrade_policies.yaml'),
                'manage_mapping_overlay': True,
                'dry_run': True,
                'good_period_sec': 5.0,
            }],
            output='screen',
        ),


        # Forensic recorder (ring + trigger)
        Node(
            package='alpha_recorder',
            executable='ring_recorder',
            name='alpha_ring_recorder',
            parameters=[{
                'profile_config': 'alpha_configs/recorder_profiles.yaml',
                'ring_dir': 'data/ring',
                'trigger_dir': 'data/triggers',
                'bag_duration_sec': 10,
                'enabled': True,
            }],
            output='screen',
        ),


        # Latency feeders (placeholder samplers)
        Node(
            package='alpha_observability',
            executable='latency_feeders',
            name='alpha_latency_feeders',
            parameters=[{
                'map_from_lidar': True,
                'map_source_topic': '/alpha/lidar/front/points',
                'cmd_static_ms': 30.0,
                'video_static_ms': 90.0,
                'publish_period_sec': 1.0,
            }],
            output='screen',
        ),


        # Video budget applier (publishes target bitrate/fps)
        Node(
            package='alpha_comms',
            executable='video_budget_applier',
            name='alpha_video_budget',
            parameters=[{
                'default_fps': 30,
                'default_bitrate': 6000000,
            }],
            output='screen',
        ),


        # Video controller (applies target settings; shell hook optional)
        Node(
            package='alpha_comms',
            executable='video_controller',
            name='alpha_video_controller',
            parameters=[{
                'apply_shell_cmd': '',  # e.g., 'nvenc_ctl --fps {fps} --bitrate {bitrate}'
            }],
            output='screen',
        ),

        # Mapping autostart wired to durable lidar_ready gate
        Node(
            package='alpha_bringup',
            executable='mapping_autostart',
            name='alpha_mapping_autostart',
            parameters=[{
                'allow_single_lidar': False,
                'degrade_timeout_s': 30,
                'compose_file': 'deploy/compose.mapping.yaml',
                'env_file': 'deploy/IMAGES.lock',
            }],
            output='screen',
        ),
])
