#!/usr/bin/env python3
import argparse
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from visualization_msgs.msg import MarkerArray
from sensor_msgs.msg import PointCloud2


MSG_TYPES = {
    'MarkerArray': MarkerArray,
    'PointCloud2': PointCloud2,
}


class WaitForTopic(Node):
    def __init__(self, topic: str, msg_type, timeout: float):
        super().__init__('wait_for_topic')
        self.deadline = time.time() + timeout
        self.seen = False
        qos = QoSProfile(depth=1)
        qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        qos.history = QoSHistoryPolicy.KEEP_LAST
        self.sub = self.create_subscription(msg_type, topic, self.cb, qos)

    def cb(self, msg):
        self.seen = True
        rclpy.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('topic')
    ap.add_argument('type', choices=MSG_TYPES.keys())
    ap.add_argument('--timeout', type=float, default=8.0)
    args = ap.parse_args()

    rclpy.init(args=None)
    node = WaitForTopic(args.topic, MSG_TYPES[args.type], args.timeout)
    try:
        while rclpy.ok() and time.time() < node.deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if not node.seen:
            print(f"wait_for_topic: no messages on {args.topic} within {args.timeout}s", file=sys.stderr)
            return 2
        print(f"wait_for_topic: OK topic={args.topic}")
        return 0
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    sys.exit(main())
