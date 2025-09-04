from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    cfg_arg = DeclareLaunchArgument(
        'mapping_config',
        default_value=PathJoinSubstitution([FindPackageShare('alpha_platforms_leo_rover'),
                                            'config','leo_rover.yaml']),
        description='YAML mapping config')

    urdf = PathJoinSubstitution([FindPackageShare('alpha_platforms_leo_rover'),
                                 'urdf','leo_rover_min.urdf.xacro'])

    # Use a unique node name to avoid cross-host duplicates
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               name='robot_state_publisher_jetson',
               parameters=[{'robot_description': Command(['xacro ', urdf])}],
               output='screen')

    adapter = Node(package='alpha_platforms_leo_rover', executable='leorover_adapter_node',
                   name='leorover_adapter', output='screen',
                   parameters=[{'mapping_config': LaunchConfiguration('mapping_config')}],
                   namespace='alpha')

    return LaunchDescription([cfg_arg, rsp, adapter])
