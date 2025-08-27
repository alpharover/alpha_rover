#!/usr/bin/env python3
import argparse
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2


class WaitForCloud(Node):
    def __init__(self, topic: str, timeout: float, min_h: int, min_w: int):
        super().__init__('wait_for_cloud')
        self.topic = topic
        self.deadline = time.time() + timeout
        self.min_h = min_h
        self.min_w = min_w
        self.seen = False
        self.dim_ok = False
        self.frame_id = None
        qos = QoSProfile(depth=1)
        qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        qos.history = QoSHistoryPolicy.KEEP_LAST
        self.sub = self.create_subscription(PointCloud2, topic, self.cb, qos)

    def cb(self, msg: PointCloud2):
        self.seen = True
        self.frame_id = msg.header.frame_id
        self.dim_ok = (msg.height >= self.min_h and msg.width >= self.min_w)
        # Stop once first message arrives
        rclpy.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('topic')
    ap.add_argument('--timeout', type=float, default=6.0)
    ap.add_argument('--min-h', type=int, default=1)
    ap.add_argument('--min-w', type=int, default=1)
    args = ap.parse_args()

    rclpy.init(args=None)
    node = WaitForCloud(args.topic, args.timeout, args.min_h, args.min_w)
    try:
        while rclpy.ok() and time.time() < node.deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        # If shutdown from callback, flags are set; else timeout
        if not node.seen:
            print(f"wait_for_cloud: no messages on {args.topic} within {args.timeout}s", file=sys.stderr)
            return 2
        if not node.dim_ok:
            print(f"wait_for_cloud: dims too small on {args.topic} (need H>={args.min_h}, W>={args.min_w}, got unknown)", file=sys.stderr)
            return 3
        print(f"wait_for_cloud: OK topic={args.topic} frame={node.frame_id}")
        return 0
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    sys.exit(main())
