import statistics
from collections import deque
from typing import Deque, Dict

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import Float32
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from alpha_utils.msg import Event


class SlidingP95:
    def __init__(self, capacity: int = 200):
        self.capacity = capacity
        self.buf: Deque[float] = deque(maxlen=capacity)

    def add(self, v: float):
        self.buf.append(v)

    def p95(self) -> float:
        if not self.buf:
            return 0.0
        data = sorted(self.buf)
        idx = max(0, int(0.95 * (len(data) - 1)))
        return float(data[idx])


class SloPublisher(Node):
    def __init__(self):
        super().__init__('alpha_slo_publisher')
        self.declare_parameter('degrade_config', 'alpha_configs/degrade_policies.yaml')
        self.declare_parameter('publish_period_sec', 1.0)
        self.declare_parameter('window_size', 200)

        self.thresholds = self._load_thresholds(self.get_parameter('degrade_config').get_parameter_value().string_value)

        qos = QoSProfile(depth=10)
        self.pub = self.create_publisher(DiagnosticArray, '/alpha/observability/slo', qos)
        self.events_pub = self.create_publisher(Event, '/alpha/events', 10)

        ws = int(self.get_parameter('window_size').get_parameter_value().integer_value)
        self.metrics: Dict[str, SlidingP95] = {
            'cmd': SlidingP95(ws),
            'map': SlidingP95(ws),
            'video': SlidingP95(ws),
        }

        # Inputs: sample topics (ms)
        self.sub_cmd = self.create_subscription(Float32, '/alpha/metrics/cmd_latency_ms', self._on_cmd, 10)
        self.sub_map = self.create_subscription(Float32, '/alpha/metrics/map_latency_ms', self._on_map, 10)
        self.sub_video = self.create_subscription(Float32, '/alpha/metrics/video_latency_ms', self._on_video, 10)

        period = float(self.get_parameter('publish_period_sec').get_parameter_value().double_value)
        self.timer = self.create_timer(period, self._tick)

    def _load_thresholds(self, path: str) -> Dict[str, float]:
        try:
            with open(path, 'r') as f:
                cfg = yaml.safe_load(f) or {}
            t = cfg.get('triggers', {})
            return {
                'cmd': float(t.get('slo_p95_cmd_ms', 60)),
                'map': float(t.get('slo_p95_map_ms', 90)),
                'video': float(t.get('slo_p95_video_ms', 120)),
            }
        except Exception:
            return {'cmd': 60.0, 'map': 90.0, 'video': 120.0}

    def _on_cmd(self, msg: Float32):
        self.metrics['cmd'].add(float(msg.data))

    def _on_map(self, msg: Float32):
        self.metrics['map'].add(float(msg.data))

    def _on_video(self, msg: Float32):
        self.metrics['video'].add(float(msg.data))

    def _tick(self):
        vals = {k: v.p95() for k, v in self.metrics.items()}
        # Publish DiagnosticArray
        arr = DiagnosticArray()
        arr.status = []
        for key, p95 in vals.items():
            th = self.thresholds.get(key, 0.0)
            st = DiagnosticStatus()
            st.name = f'slo_p95_{key}_ms'
            st.hardware_id = 'alpha'
            st.level = DiagnosticStatus.OK if p95 <= th else DiagnosticStatus.WARN
            st.message = 'ok' if st.level == DiagnosticStatus.OK else 'breach'
            st.values = [KeyValue(key='p95_ms', value=f'{p95:.1f}'), KeyValue(key='threshold_ms', value=str(th))]
            arr.status.append(st)
        self.pub.publish(arr)

        # Emit events for breaches
        for key, p95 in vals.items():
            th = self.thresholds.get(key, 0.0)
            if p95 > th:
                ev = Event()
                ev.stamp = self.get_clock().now().to_msg()  # type: ignore
                ev.type = 'SLO_BREACH'
                ev.details = f'{key}:{p95:.1f}>{th:.1f}'
                self.events_pub.publish(ev)


def main(args=None):
    rclpy.init(args=args)
    node = SloPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

