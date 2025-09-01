import pytest
import rclpy
from std_srvs.srv import Trigger

from alpha_calibration_tools.tf_ok_node import TfOk


def write_yaml(path, content):
    import yaml
    with open(path, 'w') as f:
        yaml.safe_dump(content, f)


@pytest.mark.unit
def test_tf_ok_enforce(tmp_path):
    # Create nominal/current within bounds
    nominal = {
        'frames': {
            'base_to_lidar_front': {
                'translation_m': [0.1, 0.0, 0.0],
                'rpy_rad': [0.0, 0.0, 0.0],
            }
        }
    }
    current = {
        'frames': {
            'base_to_lidar_front': {
                'translation_m': [0.101, 0.0, 0.0],  # 1 mm delta
                'rpy_rad': [0.0, 0.0, 0.001],        # ~0.057 deg
            }
        }
    }
    bounds = {
        'base_to_lidar_front': { 'pos_mm': 5, 'yaw_deg': 0.3, 'pitch_deg': 0.3, 'roll_deg': 0.3 }
    }
    nominal_path = tmp_path / 'nominal.yaml'
    current_path = tmp_path / 'current.yaml'
    bounds_path = tmp_path / 'bounds.yaml'
    write_yaml(nominal_path, nominal)
    write_yaml(current_path, current)
    write_yaml(bounds_path, bounds)

    rclpy.init()
    try:
        node = TfOk()
        node.set_parameters([
            rclpy.parameter.Parameter('enforce', rclpy.Parameter.Type.BOOL, True),
            rclpy.parameter.Parameter('bounds_config', rclpy.Parameter.Type.STRING, str(bounds_path)),
            rclpy.parameter.Parameter('nominal_extrinsics', rclpy.Parameter.Type.STRING, str(nominal_path)),
            rclpy.parameter.Parameter('current_extrinsics', rclpy.Parameter.Type.STRING, str(current_path)),
        ])
        resp = Trigger.Response()
        resp = node.on_tf_ok(Trigger.Request(), resp)
        assert resp.success
    finally:
        rclpy.shutdown()
