import random
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from builtin_interfaces.msg import Time as TimeMsg
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Float32


def _age_ms(now: TimeMsg, then: TimeMsg) -> float:
    n = now.sec * 1_000 + now.nanosec / 1_000_000.0  # type: ignore[attr-defined]
    t = then.sec * 1_000 + then.nanosec / 1_000_000.0  # type: ignore[attr-defined]
    return max(0.0, float(n - t))


class LatencyFeeders(Node):
    def __init__(self):
        super().__init__('alpha_latency_feeders')
        self.declare_parameter('map_from_lidar', True)
        self.declare_parameter('map_source_topic', '/alpha/lidar/front/points')
        self.declare_parameter('cmd_static_ms', 30.0)
        self.declare_parameter('video_static_ms', 90.0)
        self.declare_parameter('publish_period_sec', 1.0)

        qos = QoSProfile(depth=10)
        self.pub_cmd = self.create_publisher(Float32, '/alpha/metrics/cmd_latency_ms', qos)
        self.pub_map = self.create_publisher(Float32, '/alpha/metrics/map_latency_ms', qos)
        self.pub_video = self.create_publisher(Float32, '/alpha/metrics/video_latency_ms', qos)

        self.last_map_stamp: Optional[TimeMsg] = None
        if self.get_parameter('map_from_lidar').get_parameter_value().bool_value:
            topic = self.get_parameter('map_source_topic').get_parameter_value().string_value
            self.create_subscription(PointCloud2, topic, self._on_lidar, 10)

        period = float(self.get_parameter('publish_period_sec').get_parameter_value().double_value)
        self.timer = self.create_timer(period, self._tick)

    def _on_lidar(self, msg: PointCloud2):
        self.last_map_stamp = msg.header.stamp

    def _tick(self):
        now = self.get_clock().now().to_msg()  # type: ignore

        # cmd latency: static param with small jitter to simulate variability
        cmd_ms = float(self.get_parameter('cmd_static_ms').get_parameter_value().double_value)
        cmd_ms += random.uniform(-2.0, 2.0)
        self.pub_cmd.publish(Float32(data=float(max(0.0, cmd_ms))))

        # map latency: if we have a recent lidar stamp, use age; else static 60ms
        if self.last_map_stamp is not None:
            map_ms = _age_ms(now, self.last_map_stamp)
        else:
            map_ms = 60.0
        self.pub_map.publish(Float32(data=float(map_ms)))

        # video latency: static param with jitter
        video_ms = float(self.get_parameter('video_static_ms').get_parameter_value().double_value)
        video_ms += random.uniform(-5.0, 5.0)
        self.pub_video.publish(Float32(data=float(max(0.0, video_ms))))


def main(args=None):
    rclpy.init(args=args)
    node = LatencyFeeders()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

