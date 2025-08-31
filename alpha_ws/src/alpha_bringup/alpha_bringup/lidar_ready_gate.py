import time
from collections import deque
from typing import Deque

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool


class LidarReadyGate(Node):
    def __init__(self):
        super().__init__('alpha_lidar_ready_gate')
        # Params
        self.declare_parameter('warmup_s', 10.0)
        self.declare_parameter('window_s', 3.0)
        self.declare_parameter('min_rate_hz', 9.0)
        self.declare_parameter('flip_low_hz', 8.0)
        self.declare_parameter('front_topic', '/alpha/lidar/front/points')
        self.declare_parameter('rear_topic', '/alpha/lidar/rear/points')

        self.warmup_s = float(self.get_parameter('warmup_s').value)
        self.window_s = float(self.get_parameter('window_s').value)
        self.min_rate_hz = float(self.get_parameter('min_rate_hz').value)
        self.flip_low_hz = float(self.get_parameter('flip_low_hz').value)
        self.front_topic = str(self.get_parameter('front_topic').value)
        self.rear_topic = str(self.get_parameter('rear_topic').value)

        self._front: Deque[float] = deque(maxlen=100)
        self._rear: Deque[float] = deque(maxlen=100)
        self._t0 = time.time()
        self._last_state = False

        qos = qos_profile_sensor_data
        self.create_subscription(PointCloud2, self.front_topic, self._cb_front, qos)
        self.create_subscription(PointCloud2, self.rear_topic, self._cb_rear, qos)
        self.pub = self.create_publisher(Bool, '/alpha/gates/lidar_ready', 10)
        self.timer = self.create_timer(0.5, self._tick)
        self.get_logger().info(f'lidar_ready gate active: warmup={self.warmup_s}s min_rate={self.min_rate_hz}Hz window={self.window_s}s')

    def _cb_front(self, _msg: PointCloud2):
        self._front.append(time.time())

    def _cb_rear(self, _msg: PointCloud2):
        self._rear.append(time.time())

    def _rate(self, buf: Deque[float]) -> float:
        now = time.time()
        while buf and now - buf[0] > self.window_s:
            buf.popleft()
        if len(buf) < 2:
            return 0.0
        dt = buf[-1] - buf[0]
        return (len(buf) - 1) / dt if dt > 0 else 0.0

    def _tick(self):
        now = time.time()
        warm = (now - self._t0) >= self.warmup_s
        rate_f = self._rate(self._front)
        rate_r = self._rate(self._rear)
        ready = warm and (rate_f >= self.min_rate_hz) and (rate_r >= self.min_rate_hz)
        # Hysteresis: if previously true, don't flip false unless both < flip_low_hz
        if self._last_state and not ready:
            if rate_f >= self.flip_low_hz or rate_r >= self.flip_low_hz:
                ready = True
        if ready != self._last_state:
            self.get_logger().info(f'lidar_ready={ready} warm={warm} rate_f={rate_f:.2f}Hz rate_r={rate_r:.2f}Hz')
            self._last_state = ready
        self.pub.publish(Bool(data=ready))


def main():
    rclpy.init()
    node = LidarReadyGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

