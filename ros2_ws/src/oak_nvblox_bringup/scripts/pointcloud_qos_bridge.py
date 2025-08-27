#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2


class PointCloudQoSBridge(Node):
    def __init__(self):
        super().__init__('pointcloud_qos_bridge')

        self.declare_parameter('input_topic', '/airy_200/rslidar_points')
        self.declare_parameter('output_topic', '/nvblox_node/pointcloud')
        self.declare_parameter('queue_depth', 10)

        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        depth = int(self.get_parameter('queue_depth').get_parameter_value().integer_value)

        # Subscribers: use RELIABLE to match drivers that publish reliable by default
        qos_sub = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=depth)
        qos_sub.reliability = ReliabilityPolicy.RELIABLE

        # Publishers: use SENSOR_DATA-like QoS (best-effort) to match nvblox input_qos
        qos_pub = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=depth)
        qos_pub.reliability = ReliabilityPolicy.BEST_EFFORT

        self.pub = self.create_publisher(PointCloud2, output_topic, qos_pub)
        self.sub = self.create_subscription(PointCloud2, input_topic, self._cb, qos_sub)

        self.get_logger().info(
            f"Bridging pointcloud QoS: {input_topic} (RELIABLE) -> {output_topic} (BEST_EFFORT)"
        )

    def _cb(self, msg: PointCloud2):
        # Forward message directly; leave frame_id/timestamp unchanged
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = PointCloudQoSBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

