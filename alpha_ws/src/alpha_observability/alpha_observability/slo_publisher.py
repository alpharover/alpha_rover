import time
import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue


class SloPublisher(Node):
    def __init__(self):
        super().__init__('alpha_slo_publisher')
        self.timer = self.create_timer(1.0, self._tick)
        self.pub = self.create_publisher(DiagnosticArray, '/alpha/observability/slo', 10)

    def _tick(self):
        now = self.get_clock().now().to_msg()
        arr = DiagnosticArray()
        arr.header.stamp = now
        status = DiagnosticStatus()
        status.name = 'alpha/slo'
        status.level = DiagnosticStatus.OK
        status.message = 'SLO metrics (placeholder)'
        status.values = [
            KeyValue(key='cmd_latency_p95_ms', value='0'),
            KeyValue(key='map_latency_p95_ms', value='0'),
            KeyValue(key='video_latency_p95_ms', value='0'),
        ]
        arr.status = [status]
        self.pub.publish(arr)


def main():
    rclpy.init()
    node = SloPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

