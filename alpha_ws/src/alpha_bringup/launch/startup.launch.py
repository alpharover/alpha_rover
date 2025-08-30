from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


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
                'sequence_config': 'alpha_configs/startup_sequence.yaml',
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
                'network_config': 'alpha_configs/network.yaml',
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
                'config': 'alpha_configs/lidar_airy.yaml',
                'input_front_topic': '/alpha/lidar/front/points_raw',
                'input_rear_topic': '/alpha/lidar/rear/points_raw',
            }],
            output='screen',
        ),

        # Time sync preflight gate (skeleton)
        Node(
            package='alpha_time_sync',
            executable='preflight_gate',
            name='alpha_time_sync_gate',
            parameters=[{'always_ok': True}],
            output='screen',
        ),

        # Mode manager (skeleton)
        Node(
            package='alpha_mode_manager',
            executable='mode_manager',
            name='alpha_mode_manager',
            parameters=[{
                'modes_config': 'alpha_configs/modes.yaml',
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
                'config_failure_domains': 'alpha_configs/failure_domains.yaml',
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
                'degrade_config': 'alpha_configs/degrade_policies.yaml',
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
                'degrade_config': 'alpha_configs/degrade_policies.yaml',
                'manage_mapping_overlay': True,
                'dry_run': True,
                'good_period_sec': 5.0,
            }],
            output='screen',
        ),
])
