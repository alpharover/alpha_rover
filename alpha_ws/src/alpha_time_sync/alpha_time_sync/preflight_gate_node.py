import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String
from std_srvs.srv import Trigger


class PreflightGate(Node):
    def __init__(self):
        super().__init__('alpha_time_sync_gate')
        self.declare_parameter('always_ok', True)
        self.pub = self.create_publisher(String, '/alpha/time_sync/status', QoSProfile(depth=10))
        self.srv = self.create_service(Trigger, '/alpha/time_sync/preflight_gate', self.on_gate)
        self.timer = self.create_timer(1.0, self._tick)

    def _tick(self):
        msg = String()
        msg.data = 'PTP_OK' if self.get_parameter('always_ok').get_parameter_value().bool_value else 'PTP_UNKNOWN'
        self.pub.publish(msg)

    def on_gate(self, req: Trigger.Request, resp: Trigger.Response):
        ok = self.get_parameter('always_ok').get_parameter_value().bool_value
        resp.success = bool(ok)
        resp.message = 'ok' if ok else 'not ok'
        return resp


def main(args=None):
    rclpy.init(args=args)
    node = PreflightGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

