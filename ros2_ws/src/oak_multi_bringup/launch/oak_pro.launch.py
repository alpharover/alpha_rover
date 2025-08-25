from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('oak_multi_bringup')
    default_params = os.path.join(pkg_share, 'config', 'oak_pro_only.yaml')
    params_file = LaunchConfiguration('params_file')

    container = ComposableNodeContainer(
        name='oak_pro_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        output='screen',
        arguments=['--ros-args', '--log-level', 'info'],
        composable_node_descriptions=[
            ComposableNode(
                package='depthai_ros_driver',
                plugin='depthai_ros_driver::Camera',
                name='camera',
                namespace='oak_d_pro',
                parameters=[params_file],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
            # Colorized point cloud from aligned depth and RGB
            ComposableNode(
                package='depth_image_proc',
                plugin='depth_image_proc::PointCloudXyzrgbNode',
                name='pointcloud',
                namespace='oak_d_pro',
                remappings=[
                    ('rgb/image_rect_color', '/oak_d_pro/camera/rgb/image_raw'),
                    ('rgb/camera_info', '/oak_d_pro/camera/rgb/camera_info'),
                    ('depth_registered/image_rect', '/oak_d_pro/camera/stereo/image_raw'),
                ],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
        emulate_tty=True,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Path to the YAML file with parameters for the OAK-D-Pro camera.'
        ),
        container,
        # TFs now provided by robot_state_publisher (see robot_state.launch.py)
    ])
