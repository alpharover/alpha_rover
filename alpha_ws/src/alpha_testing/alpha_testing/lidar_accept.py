#!/usr/bin/env python3
import time
import argparse
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from rclpy.time import Time


EXPECTED = {'front': (96, 900), 'rear': (96, 900)}


class LidarAccept(Node):
    def __init__(self, max_skew_s: float, window_s: float):
        super().__init__('lidar_accept')
        self.max_skew_s = max_skew_s
        self.window_s = window_s
        self.ok = {k: False for k in EXPECTED}
        self.stats = {k: {'seen': 0, 'last_skew_s': None, 'dims': None} for k in EXPECTED}
        # Match typical publisher QoS (default rclpy publisher is RELIABLE)
        qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.RELIABLE, history=QoSHistoryPolicy.KEEP_LAST)
        for ns in EXPECTED:
            topic = f'/alpha/lidar/{ns}/points'
            self.create_subscription(PointCloud2, topic, self._cb(ns), qos)
            self.get_logger().info(f'Waiting for: {topic}')

    def _cb(self, ns):
        def _f(msg: PointCloud2):
            dims = (msg.height, msg.width)
            now = self.get_clock().now()
            stamp = Time(seconds=msg.header.stamp.sec, nanoseconds=msg.header.stamp.nanosec)
            skew = abs((now - stamp).nanoseconds) / 1e9
            self.stats[ns]['seen'] += 1
            self.stats[ns]['last_skew_s'] = skew
            self.stats[ns]['dims'] = dims
            if dims == EXPECTED[ns] and skew <= self.max_skew_s:
                self.ok[ns] = True
        return _f


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-skew-ms', type=float, default=20.0, help='Skew threshold in milliseconds (default 20)')
    parser.add_argument('--window-s', type=float, default=15.0, help='Observation window seconds (default 15)')
    args = parser.parse_args()

    rclpy.init()
    node = LidarAccept(max_skew_s=args.max_skew_ms / 1000.0, window_s=args.window_s)
    start = time.time()
    try:
        while time.time() - start < node.window_s:
            rclpy.spin_once(node, timeout_sec=0.2)
            if all(node.ok.values()):
                break
    finally:
        node.get_logger().info(f"LiDAR stats: {node.stats}")
        all_ok = all(node.ok.values())
        node.get_logger().info(f"LiDAR accept: {node.ok}")
        node.destroy_node()
        rclpy.shutdown()
        if not all_ok:
            raise SystemExit(2)
