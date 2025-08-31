#!/usr/bin/env python3
import time
import argparse
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2


EXPECTED = {'front': (96, 900), 'rear': (96, 900)}


class LidarAccept(Node):
    def __init__(self, warmup_s: float, rel_max_skew_ms: float, abs_max_skew_ms: float, window_s: float):
        super().__init__('lidar_accept')
        self.warmup_s = warmup_s
        self.rel_max_skew_s = rel_max_skew_ms / 1000.0
        self.abs_max_skew_s = abs_max_skew_ms / 1000.0
        self.window_s = window_s
        self.start_time = time.monotonic()
        self._subs = []
        # Buffers per ns
        self.raw_stamps = {k: [] for k in EXPECTED}
        self.points_stamps = {k: [] for k in EXPECTED}
        self.rel_skews = {k: [] for k in EXPECTED}
        self.abs_skews = {k: [] for k in EXPECTED}
        self.dims = {k: None for k in EXPECTED}

        for ns in EXPECTED:
            raw = f'/alpha/lidar/{ns}/points_raw'
            out = f'/alpha/lidar/{ns}/points'
            self._subs.append(self.create_subscription(PointCloud2, raw, self._cb_raw(ns), qos_profile_sensor_data))
            self._subs.append(self.create_subscription(PointCloud2, out, self._cb_points(ns), qos_profile_sensor_data))
            self.get_logger().info(f'Waiting for: {raw} and {out}')

    def _cb_raw(self, ns):
        def _f(msg: PointCloud2):
            stamp_ns = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
            self.raw_stamps[ns].append(stamp_ns)
            # trim to last 2s
            cutoff = stamp_ns - 2_000_000_000
            self.raw_stamps[ns] = [s for s in self.raw_stamps[ns] if s >= cutoff]
        return _f

    def _cb_points(self, ns):
        def _f(msg: PointCloud2):
            now_ns = int(self.get_clock().now().nanoseconds)
            stamp_ns = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
            self.points_stamps[ns].append(stamp_ns)
            # absolute skew (info only)
            self.abs_skews[ns].append(abs(now_ns - stamp_ns) / 1e9)
            # dims tracking
            self.dims[ns] = (msg.height, msg.width)
            # match with nearest raw stamp within 15 ms
            if self.raw_stamps[ns]:
                nearest = min(self.raw_stamps[ns], key=lambda s: abs(s - stamp_ns))
                rel = abs(nearest - stamp_ns) / 1e9
                # only record after warmup
                if time.monotonic() - self.start_time >= self.warmup_s and rel <= 0.015:
                    self.rel_skews[ns].append(rel)
            # trim points list to last 2s
            cutoff = stamp_ns - 2_000_000_000
            self.points_stamps[ns] = [s for s in self.points_stamps[ns] if s >= cutoff]
        return _f


def _pct(values, p):
    if not values:
        return None
    arr = sorted(values)
    idx = min(len(arr) - 1, max(0, int(round(p * (len(arr) - 1)))))
    return arr[idx]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--warmup-s', type=float, default=10.0, help='Warm-up window (seconds) before enforcing skew')
    parser.add_argument('--relative-max-skew-ms', type=float, default=12.0, help='Relative skew P95 threshold (ms)')
    parser.add_argument('--absolute-max-skew-ms', type=float, default=20.0, help='Absolute skew info P95 threshold (ms)')
    parser.add_argument('--dims-h', type=int, default=96)
    parser.add_argument('--dims-w', type=int, default=900)
    parser.add_argument('--window-s', type=float, default=20.0, help='Observation window seconds')
    args = parser.parse_args()

    rclpy.init()
    node = LidarAccept(args.warmup_s, args.relative_max_skew_ms, args.absolute_max_skew_ms, args.window_s)
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    end = time.monotonic() + node.window_s
    try:
        while time.monotonic() < end and rclpy.ok():
            ex.spin_once(timeout_sec=0.2)
    finally:
        try:
            ex.remove_node(node)
            ex.shutdown()
        except Exception:
            pass

        # Evaluate
        dims_ok = True
        rel_ok = True
        results = {}
        for ns, expected in EXPECTED.items():
            dims_ok = dims_ok and (node.dims[ns] == expected)
            p50 = _pct(node.rel_skews[ns], 0.50)
            p95 = _pct(node.rel_skews[ns], 0.95)
            results[ns] = {
                'pairs': len(node.rel_skews[ns]),
                'rel_p50_ms': None if p50 is None else p50 * 1000.0,
                'rel_p95_ms': None if p95 is None else p95 * 1000.0,
                'dims': node.dims[ns],
            }
            if p95 is None or p95 > node.rel_max_skew_s:
                rel_ok = False

        node.get_logger().info(f'Acceptance results: {results}')
        all_ok = dims_ok and rel_ok
        node.get_logger().info(f'LiDAR accept: dimensions={dims_ok}, relative_skew={rel_ok}')
        node.destroy_node()
        rclpy.shutdown()
        if not all_ok:
            raise SystemExit(2)
