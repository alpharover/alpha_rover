from launch import LaunchDescription
from launch_ros.actions import Node
import yaml


def _load_oak_cfg(path: str):
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _oak(name, ns, frame_id, fps, width, height, mxid=""):
    return Node(
        package='depthai_ros_driver',
        executable='camera_node',
        namespace=ns,
        name=name,
        parameters=[{
            # DepthAI v2.11 monolithic node parameters (nested):
            'camera': {
                'i_mx_id': mxid,
                'i_pipeline_type': 'RGBD',
                'i_usb_speed': 'SUPER_PLUS',
                'i_publish_tf_from_calibration': False,
            },
            'rgb': {
                'i_fps': int(fps),
                'i_width': int(width),
                'i_height': int(height),
                'i_publish_topic': True,
            },
            'stereo': {
                'i_align_depth': True,
                'i_lr_check': True,
                'i_subpixel': True,
            },
        }],
        remappings=[
            # Relative remaps (match inside namespace)
            ('rgb/image_raw', f'/alpha/cam/{ns}/image_color'),
            ('rgb/camera_info', f'/alpha/cam/{ns}/camera_info'),
            # Absolute fallbacks (match fully qualified names produced by driver)
            (f'/{ns}/{name}/rgb/image_raw', f'/alpha/cam/{ns}/image_color'),
            (f'/{ns}/{name}/rgb/camera_info', f'/alpha/cam/{ns}/camera_info'),
        ],
        output='screen',
    )


def generate_launch_description():
    cfg = _load_oak_cfg('alpha_configs/oak_cams.yaml')
    front = cfg.get('oak', {}).get('front', {})
    rear = cfg.get('oak', {}).get('rear', {})
    return LaunchDescription([
        _oak('oak_front', 'front', 'alpha_cam_front', front.get('fps', 30), front.get('width', 1280), front.get('height', 720), front.get('serial', '')),
        _oak('oak_rear',  'rear',  'alpha_cam_rear',  rear.get('fps', 30),  rear.get('width', 1280),  rear.get('height', 720),  rear.get('serial', '')),
    ])
