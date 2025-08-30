import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import Int32
from alpha_utils.msg import DegradeBudget, Event


class VideoBudgetApplier(Node):
    def __init__(self):
        super().__init__('alpha_video_budget_applier')
        self.declare_parameter('default_fps', 30)
        self.declare_parameter('default_bitrate', 6_000_000)

        qos = QoSProfile(depth=10)
        self.pub_fps = self.create_publisher(Int32, '/alpha/video/target_fps', qos)
        self.pub_bitrate = self.create_publisher(Int32, '/alpha/video/target_bitrate', qos)
        self.events_pub = self.create_publisher(Event, '/alpha/events', 10)

        self.create_subscription(DegradeBudget, '/alpha/comms/budget_intent', self._on_budget, 10)

        # Publish defaults on start
        self._apply(
            fps=int(self.get_parameter('default_fps').get_parameter_value().integer_value),
            bitrate=int(self.get_parameter('default_bitrate').get_parameter_value().integer_value),
            level='INIT'
        )

    def _apply(self, fps: int, bitrate: int, level: str):
        self.pub_fps.publish(Int32(data=int(max(0, fps))))
        self.pub_bitrate.publish(Int32(data=int(max(0, bitrate))))
        ev = Event()
        ev.stamp = self.get_clock().now().to_msg()  # type: ignore
        ev.type = 'VIDEO_BUDGET'
        ev.details = f'level={level} fps={fps} bitrate={bitrate}'
        self.events_pub.publish(ev)

    def _on_budget(self, msg: DegradeBudget):
        fps = int(msg.video_fps) if msg.video_fps >= 0 else int(self.get_parameter('default_fps').get_parameter_value().integer_value)
        br = int(msg.video_bitrate) if msg.video_bitrate >= 0 else int(self.get_parameter('default_bitrate').get_parameter_value().integer_value)
        self._apply(fps=fps, bitrate=br, level=msg.level)


def main(args=None):
    rclpy.init(args=args)
    node = VideoBudgetApplier()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
