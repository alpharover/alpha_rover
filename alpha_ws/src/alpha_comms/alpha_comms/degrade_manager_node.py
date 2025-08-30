import time
from typing import Dict, Any

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from std_msgs.msg import String
from alpha_utils.msg import Event
from alpha_utils.srv import ModeSet


class DegradeManager(Node):
    def __init__(self):
        super().__init__('alpha_comms_degrade_manager')
        self.declare_parameter('degrade_config', 'alpha_configs/degrade_policies.yaml')
        self.declare_parameter('manage_mapping_overlay', True)
        self.declare_parameter('dry_run', True)
        self.declare_parameter('good_period_sec', 5.0)

        cfg_path = self.get_parameter('degrade_config').get_parameter_value().string_value
        self.cfg = self._load_yaml(cfg_path)
        self.levels: Dict[str, Dict[str, Any]] = self.cfg.get('levels', {})
        self.triggers = self.cfg.get('triggers', {})
        self.level_order = ['L0', 'L1', 'L2', 'L3']
        self.current_level = 'L0'
        self.last_breach_time = 0.0

        qos = QoSProfile(depth=10)
        self.sub = self.create_subscription(DiagnosticArray, '/alpha/observability/slo', self.on_slo, qos)
        self.pub_level = self.create_publisher(String, '/alpha/comms/degrade_level', 10)
        self.events_pub = self.create_publisher(Event, '/alpha/events', 10)
        self.cli_modeset = self.create_client(ModeSet, '/alpha/mode/set')
        self.timer = self.create_timer(1.0, self._tick)

        self._publish_level_event('INIT', self.current_level)

    def _load_yaml(self, path: str) -> dict:
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.get_logger().warn(f'Failed to read degrade config {path}: {e}; using defaults')
            return {}

    def _publish_level(self):
        msg = String()
        msg.data = self.current_level
        self.pub_level.publish(msg)

    def _publish_level_event(self, kind: str, detail: str):
        ev = Event()
        ev.stamp = self.get_clock().now().to_msg()  # type: ignore
        ev.type = f'DEGR_{kind}'
        ev.details = detail
        self.events_pub.publish(ev)

    def on_slo(self, arr: DiagnosticArray):
        # Determine if any slo report is WARN -> breach
        breach = any(st.level == DiagnosticStatus.WARN for st in arr.status)
        if breach:
            self.last_breach_time = self.get_clock().now().seconds_nanoseconds()[0]
            self._escalate()
        # else handled in tick for de-escalation

    def _escalate(self):
        idx = self.level_order.index(self.current_level)
        if idx < len(self.level_order) - 1:
            new_level = self.level_order[idx + 1]
            self._change_level(new_level)

    def _deescalate(self):
        idx = self.level_order.index(self.current_level)
        if idx > 0:
            new_level = self.level_order[idx - 1]
            self._change_level(new_level)

    def _change_level(self, new_level: str):
        old = self.current_level
        self.current_level = new_level
        self._publish_level()
        self._publish_level_event('LEVEL', f'{old}->{new_level}')
        # Apply mapping overlay policy
        lvl_cfg = self.levels.get(new_level, {})
        mapping_on = bool(lvl_cfg.get('mapping', True))
        if not mapping_on and self.get_parameter('manage_mapping_overlay').get_parameter_value().bool_value:
            self._ensure_mapping_overlay(False)

    def _ensure_mapping_overlay(self, enable: bool):
        dry_run = self.get_parameter('dry_run').get_parameter_value().bool_value
        if dry_run:
            self._publish_level_event('MAP_OVERLAY', f'dry_run enable={enable}')
            return
        if not self.cli_modeset.wait_for_service(timeout_sec=2.0):
            self._publish_level_event('ERROR', 'mode_set unavailable')
            return
        req = ModeSet.Request()
        if enable:
            req.enable_overlays = ['MAPPING']
        else:
            req.disable_overlays = ['MAPPING']
        fut = self.cli_modeset.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=2.0)
        ok = bool(fut.done() and getattr(fut.result(), 'accepted', False))
        self._publish_level_event('MAP_OVERLAY', f'enable={enable}:{ok}')

    def _tick(self):
        # De-escalate if no breach seen in good_period
        now_sec = self.get_clock().now().seconds_nanoseconds()[0]
        good_period = float(self.get_parameter('good_period_sec').get_parameter_value().double_value)
        if self.last_breach_time > 0 and (now_sec - self.last_breach_time) >= good_period:
            self._deescalate()


def main(args=None):
    rclpy.init(args=args)
    node = DegradeManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

