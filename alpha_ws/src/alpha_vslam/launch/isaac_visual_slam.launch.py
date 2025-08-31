from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Minimal wrapper to start Isaac ROS Visual SLAM. Adjust parameters as needed.
    return LaunchDescription([
        Node(
            package='isaac_ros_visual_slam',
            executable='visual_slam_node',
            name='alpha_visual_slam',
            parameters=[{
                'rectified_images': False,
                'enable_slam_visualization': False,
                'denoise_input_images': False,
            }],
            remappings=[
                # Adjust these to match OAK topics; placeholders for now
                ('/stereo_camera/left/image', '/alpha/cam/front/image_color'),
                ('/stereo_camera/left/camera_info', '/alpha/cam/front/camera_info'),
                # If using stereo, also map right camera topics accordingly
            ],
            output='screen',
        )
    ])

