from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command, TextSubstitution
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('oak_multi_bringup')
    default_urdf = os.path.join(pkg_share, 'urdf', 'oak_sensors.urdf.xacro')
    # Fallback to source-relative path if URDF not installed
    if not os.path.exists(default_urdf):
        default_urdf = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'urdf', 'oak_sensors.urdf.xacro'))

    urdf_file = LaunchConfiguration('urdf_file')
    use_gui = LaunchConfiguration('use_gui')
    robot_description = {
        'robot_description': ParameterValue(Command([TextSubstitution(text='xacro '), urdf_file]), value_type=str),
        'use_sim_time': False,
    }

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'urdf_file',
            default_value=default_urdf,
            description='Path to the URDF/Xacro file describing sensor frames.'
        ),
        DeclareLaunchArgument('use_gui', default_value='false'),
        rsp,
    ])
