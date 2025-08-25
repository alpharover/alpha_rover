import re
from typing import Dict, Optional

import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from sensor_msgs.msg import Temperature


def parse_float(s: str) -> Optional[float]:
    try:
        return float(s)
    except Exception:
        try:
            # try to extract first float-like substring
            m = re.search(r"-?\d+\.?\d*", s)
            if m:
                return float(m.group(0))
        except Exception:
            pass
    return None


class OakTempBridge(Node):
    def __init__(self):
        super().__init__('oak_temp_bridge')
        # namespaces to watch; match against name or hardware_id
        self.namespaces = self.declare_parameter('namespaces', ['oak_d_pro', 'oak_d_sr']).get_parameter_value().string_array_value
        self.topic = self.declare_parameter('diagnostics_topic', '/diagnostics').get_parameter_value().string_value

        # publishers per namespace
        self.pubs: Dict[str, rclpy.publisher.Publisher] = {}
        for ns in self.namespaces:
            self.pubs[ns] = self.create_publisher(Temperature, f'/{ns}/device_temperature', 10)

        self.sub = self.create_subscription(DiagnosticArray, self.topic, self.diag_cb, 10)
        self.get_logger().info(f'Bridging OAK temperatures from {self.topic} to /<ns>/device_temperature for: {self.namespaces}')

    def diag_cb(self, msg: DiagnosticArray):
        # scan statuses for our namespaces, look for temperature-like keys
        for status in msg.status:
            status_text = (status.name + ' ' + status.hardware_id).lower()
            target_ns = None
            for ns in self.namespaces:
                if ns in status_text:
                    target_ns = ns
                    break
            if not target_ns:
                continue

            # candidate keys
            candidate = None
            candidate_key = None
            for kv in status.values:
                key_lower = kv.key.lower()
                if 'temp' in key_lower:
                    val = parse_float(kv.value)
                    if val is not None:
                        # prefer chip/core temps by name heuristic
                        if candidate is None or 'chip' in key_lower or 'core' in key_lower:
                            candidate = val
                            candidate_key = kv.key

            if candidate is not None:
                tmsg = Temperature()
                tmsg.header.stamp = msg.header.stamp
                tmsg.header.frame_id = target_ns
                tmsg.temperature = float(candidate)
                tmsg.variance = 0.0
                self.pubs[target_ns].publish(tmsg)
            else:
                # nothing to publish for this status
                pass


def main():
    rclpy.init()
    node = OakTempBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

