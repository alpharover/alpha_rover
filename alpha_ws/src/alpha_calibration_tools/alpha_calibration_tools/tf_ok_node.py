import math
import yaml
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class TfOk(Node):
    def __init__(self):
        super().__init__('alpha_tf_ok')
        self.declare_parameter('always_ok', True)
        self.declare_parameter('enforce', False)
        self.declare_parameter('bounds_config', 'alpha_configs/calibration_bounds.yaml')
        self.declare_parameter('nominal_extrinsics', 'alpha_configs/extrinsics_seed.yaml')
        self.declare_parameter('current_extrinsics', 'alpha_configs/extrinsics_current.yaml')
        self.declare_parameter('compare_from_config', True)
        self.srv = self.create_service(Trigger, '/alpha_calibration_tools/tf_ok', self.on_tf_ok)

    def _load_yaml(self, path: str):
        try:
            return yaml.safe_load(Path(path).read_text())
        except Exception as e:
            self.get_logger().warn(f'failed to read yaml {path}: {e}')
            return None

    def _rad_to_deg(self, rad):
        try:
            return [float(x) * 180.0 / math.pi for x in rad]
        except Exception:
            return [0.0, 0.0, 0.0]

    def _compare_configs(self, bounds_path: str, nominal_path: str, current_path: str) -> (bool, str):
        bounds = self._load_yaml(bounds_path)
        nominal = self._load_yaml(nominal_path)
        current = self._load_yaml(current_path)
        if bounds is None or nominal is None or current is None:
            return True, 'config missing; skipping'
        nframes = nominal.get('frames', {})
        cframes = current.get('frames', {})
        for frame, lim in bounds.items():
            n = nframes.get(frame)
            c = cframes.get(frame)
            if not n or not c:
                # Missing frame; skip
                continue
            # translation_m arrays
            try:
                n_t = [float(x) for x in n.get('translation_m', [0, 0, 0])]
                c_t = [float(x) for x in c.get('translation_m', [0, 0, 0])]
                dpos = math.sqrt(sum((c_t[i] - n_t[i]) ** 2 for i in range(3))) * 1000.0  # mm
            except Exception:
                dpos = 0.0
            # rpy_rad arrays
            try:
                n_r = self._rad_to_deg(n.get('rpy_rad', [0, 0, 0]))
                c_r = self._rad_to_deg(c.get('rpy_rad', [0, 0, 0]))
                dyaw = abs(c_r[2] - n_r[2])
                dpitch = abs(c_r[1] - n_r[1])
                droll = abs(c_r[0] - n_r[0])
            except Exception:
                dyaw = dpitch = droll = 0.0
            if dpos > float(lim.get('pos_mm', 0)):
                return False, f'{frame}: pos {dpos:.2f}mm > {lim.get("pos_mm")}'
            if dyaw > float(lim.get('yaw_deg', 0)):
                return False, f'{frame}: yaw {dyaw:.3f}deg > {lim.get("yaw_deg")}'
            if dpitch > float(lim.get('pitch_deg', 0)):
                return False, f'{frame}: pitch {dpitch:.3f}deg > {lim.get("pitch_deg")}'
            if droll > float(lim.get('roll_deg', 0)):
                return False, f'{frame}: roll {droll:.3f}deg > {lim.get("roll_deg")}'
        return True, 'ok'

    def on_tf_ok(self, req: Trigger.Request, resp: Trigger.Response):
        # If enforce flag is off, return based on always_ok
        if not self.get_parameter('enforce').get_parameter_value().bool_value:
            ok = self.get_parameter('always_ok').get_parameter_value().bool_value
            resp.success = bool(ok)
            resp.message = 'ok' if ok else 'not ok'
            return resp
        # Else, compare configs (for now; tf2 integration later)
        bounds = self.get_parameter('bounds_config').get_parameter_value().string_value
        nominal = self.get_parameter('nominal_extrinsics').get_parameter_value().string_value
        current = self.get_parameter('current_extrinsics').get_parameter_value().string_value
        ok, msg = self._compare_configs(bounds, nominal, current)
        resp.success = bool(ok)
        resp.message = msg
        return resp


def main(args=None):
    rclpy.init(args=args)
    node = TfOk()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
