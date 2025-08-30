import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class TfOk(Node):
    def __init__(self):
        super().__init__('alpha_tf_ok')
        self.declare_parameter('always_ok', True)
        self.srv = self.create_service(Trigger, '/alpha_calibration_tools/tf_ok', self.on_tf_ok)

    def on_tf_ok(self, req: Trigger.Request, resp: Trigger.Response):
        ok = self.get_parameter('always_ok').get_parameter_value().bool_value
        resp.success = bool(ok)
        resp.message = 'ok' if ok else 'not ok'
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

