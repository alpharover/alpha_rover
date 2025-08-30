import time
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_srvs.srv import Trigger
from alpha_utils.srv import ModeSet
from alpha_utils.msg import ModeState


class ModeManager(Node):
    def __init__(self):
        super().__init__('alpha_mode_manager')
        # Parameters
        self.declare_parameter('modes_config', 'alpha_configs/modes.yaml')
        self.declare_parameter('enforce_guards', True)

        # Load config
        cfg_path = self.get_parameter('modes_config').get_parameter_value().string_value
        self.modes_cfg = self._load_modes_cfg(cfg_path)
        self.allowed_overlays = set(self.modes_cfg.get('overlays', []))
        self.exclusive_bases = set(self.modes_cfg.get('exclusive', []))

        # State
        self.state = ModeState()
        self.state.base_mode = self.modes_cfg.get('base', 'TELEOP')
        self.state.overlays = []
        self.state.failsafe = (self.state.base_mode.upper() == 'FAILSAFE')

        # Interfaces
        self.pub = self.create_publisher(ModeState, '/alpha/mode/state', 10)
        self.srv = self.create_service(ModeSet, '/alpha/mode/set', self.on_set)
        self.timer = self.create_timer(1.0, self._tick)

        # Guard service clients (optional)
        self.cli_ptp = self.create_client(Trigger, '/alpha/time_sync/preflight_gate')
        self.cli_tfok = self.create_client(Trigger, '/alpha_calibration_tools/tf_ok')

        # Publish initial state
        self._tick()

    def _load_modes_cfg(self, path: str) -> dict:
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.get_logger().warn(f'Failed to read modes config {path}: {e}; using defaults')
            return {'base': 'TELEOP', 'overlays': ['NIGHT','LOW_POWER','MAPPING'], 'exclusive': ['FAILSAFE','DOCKING','RTH_TOPO']}

    def _tick(self):
        self.pub.publish(self.state)

    def on_set(self, req: ModeSet.Request, resp: ModeSet.Response):
        try:
            # Work on a copy
            new_state = ModeState()
            new_state.base_mode = self.state.base_mode
            new_state.overlays = list(self.state.overlays)
            new_state.failsafe = self.state.failsafe

            # Update overlays
            if req.clear_overlays:
                new_state.overlays = []

            # Disable overlays
            if req.disable_overlays:
                new_state.overlays = [o for o in new_state.overlays if o not in req.disable_overlays]

            # Enable overlays with validation and guards
            for o in req.enable_overlays:
                o_up = o.strip().upper()
                # Normalize to config casing if present
                match = next((x for x in self.allowed_overlays if x.upper() == o_up), None)
                if match is None:
                    resp.accepted = False
                    resp.message = f'overlay not allowed: {o}'
                    resp.current = self.state
                    return resp
                if match not in new_state.overlays:
                    if match.upper() == 'MAPPING' and self.get_parameter('enforce_guards').get_parameter_value().bool_value:
                        if not self._guards_ok_for_mapping(timeout_sec=2.0):
                            resp.accepted = False
                            resp.message = 'guards failed for MAPPING (ptp_ok and tf_ok required)'
                            resp.current = self.state
                            return resp
                    new_state.overlays.append(match)

            # Base mode changes
            if req.target_base_mode:
                target = req.target_base_mode.strip()
                # Normalize casing if matches any known exclusive base name
                ex_match = next((x for x in self.exclusive_bases if x.upper() == target.upper()), None)
                if ex_match:
                    new_state.base_mode = ex_match
                    # Exclusive modes clear overlays
                    new_state.overlays = []
                else:
                    # Any other string is accepted as non-exclusive mode
                    new_state.base_mode = target
                new_state.failsafe = (new_state.base_mode.upper() == 'FAILSAFE')

            # Apply
            self.state = new_state
            self._tick()  # publish immediately
            resp.accepted = True
            resp.message = 'ok'
            resp.current = self.state
        except Exception as e:
            resp.accepted = False
            resp.message = str(e)
            resp.current = self.state
        return resp

    def _guards_ok_for_mapping(self, timeout_sec: float = 2.0) -> bool:
        # Call optional Trigger services; if unavailable, treat as failure when enforce_guards=true
        ok = True
        if self.cli_ptp and self.cli_tfok:
            ok = ok and self._call_trigger(self.cli_ptp, timeout_sec)
            ok = ok and self._call_trigger(self.cli_tfok, timeout_sec)
        else:
            ok = False
        return ok

    def _call_trigger(self, client, timeout_sec: float) -> bool:
        if not client.wait_for_service(timeout_sec=timeout_sec):
            return False
        fut = client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout_sec)
        if not fut.done():
            return False
        resp = fut.result()
        return bool(resp and getattr(resp, 'success', False))


def main():
    rclpy.init()
    node = ModeManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
