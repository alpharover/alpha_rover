import rclpy
from rclpy.node import Node
from alpha_utils.srv import OrchestratorCommand
from alpha_utils.msg import Event
from builtin_interfaces.msg import Time as TimeMsg


class Orchestrator(Node):
    def __init__(self):
        super().__init__('alpha_orchestrator')
        self.srv = self.create_service(OrchestratorCommand, '/alpha/orchestrator/cmd', self.on_cmd)
        self.events_pub = self.create_publisher(Event, '/alpha/events', 10)

    def publish_event(self, etype: str, details: str):
        ev = Event()
        ev.stamp = self.get_clock().now().to_msg()  # type: ignore
        ev.type = etype
        ev.details = details
        self.events_pub.publish(ev)

    def on_cmd(self, req: OrchestratorCommand.Request, resp: OrchestratorCommand.Response):
        # Skeleton: ack and emit event; real actions will be wired later
        self.get_logger().info(f"orchestrator cmd: {req.action}")
        self.publish_event('ORCH_CMD', req.action)
        resp.accepted = True
        resp.message = 'ok'
        return resp


def main():
    rclpy.init()
    node = Orchestrator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

