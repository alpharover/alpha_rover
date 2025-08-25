from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('oak_multi_bringup')
    default_params = os.path.join(pkg_share, 'config', 'oak_sr_only.yaml')
    params_file = LaunchConfiguration('params_file')

    # Static TF args (defaults updated for SR rear-facing mount)
    tf_x = LaunchConfiguration('tf_x')
    tf_y = LaunchConfiguration('tf_y')
    tf_z = LaunchConfiguration('tf_z')
    tf_qx = LaunchConfiguration('tf_qx')
    tf_qy = LaunchConfiguration('tf_qy')
    tf_qz = LaunchConfiguration('tf_qz')
    tf_qw = LaunchConfiguration('tf_qw')
    parent_frame = LaunchConfiguration('parent_frame')
    child_frame = LaunchConfiguration('child_frame')

    container = ComposableNodeContainer(
        name='oak_sr_container',
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
                namespace='oak_d_sr',
                parameters=[params_file],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
            # XYZ point cloud from depth and camera_info (no RGB on SR)
            ComposableNode(
                package='depth_image_proc',
                plugin='depth_image_proc::PointCloudXyzNode',
                name='pointcloud',
                namespace='oak_d_sr',
                remappings=[
                    # PointCloudXyzNode expects 'image_rect' and 'camera_info'
                    ('image_rect', '/oak_d_sr/camera/stereo/image_raw'),
                    ('camera_info', '/oak_d_sr/camera/stereo/camera_info'),
                ],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
        emulate_tty=True,
    )

    return LaunchDescription([
        # Params
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Path to the YAML file with parameters for the OAK-D-SR camera.'
        ),
        container,
        # TFs now provided by robot_state_publisher (see robot_state.launch.py)
    ])
