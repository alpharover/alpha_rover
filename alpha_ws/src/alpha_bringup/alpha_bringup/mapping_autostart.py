#!/usr/bin/env python3
import subprocess
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.clock import Clock, ClockType
from std_msgs.msg import Bool


class MappingAutostart(Node):
    def __init__(self):
        super().__init__('mapping_autostart')
        # Params
        self.declare_parameter('allow_single_lidar', False)
        self.declare_parameter('degrade_timeout_s', 30)
        self.declare_parameter('compose_file', 'deploy/compose.mapping.yaml')
        self.declare_parameter('env_file', 'deploy/IMAGES.lock')

        # Gate subscription (durable)
        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.sub = self.create_subscription(Bool, '/alpha/gates/lidar_ready', self._on_gate, qos)

        self._steady = Clock(clock_type=ClockType.STEADY_TIME)
        self._gate_true = False
        self._last_false_ns: Optional[int] = None
        self._timer = self.create_timer(0.5, self._tick)
        self.get_logger().info('mapping_autostart active: strict gate; degrade behind param')

    def _on_gate(self, msg: Bool):
        now = self._steady.now().nanoseconds
        if msg.data:
            self._gate_true = True
            self._last_false_ns = None
        else:
            self._gate_true = False
            if self._last_false_ns is None:
                self._last_false_ns = now

    def _tick(self):
        allow_single = self.get_parameter('allow_single_lidar').get_parameter_value().bool_value
        timeout_s = int(self.get_parameter('degrade_timeout_s').get_parameter_value().integer_value)
        now = self._steady.now().nanoseconds

        if self._gate_true:
            # Ensure mapping is up
            self._compose(['up', '-d'])
            return

        # Gate false
        if self._mapping_running():
            # Stop after 3s of persistent false to avoid flapping
            if self._last_false_ns and (now - self._last_false_ns) / 1e9 > 3.0:
                self.get_logger().warn('lidar_ready fell false; stopping mapping')
                self._compose(['stop'])
            return

        # Consider degrade fallback
        if allow_single and self._last_false_ns and (now - self._last_false_ns) / 1e9 > timeout_s:
            self.get_logger().warn('lidar_ready timeout; starting NVBlox in DEGRADE mode')
            self._compose(['up', '-d'])

    def _compose(self, args):
        compose = self.get_parameter('compose_file').get_parameter_value().string_value
        envf = self.get_parameter('env_file').get_parameter_value().string_value
        cmd = ['docker', 'compose', '-f', compose, '--env-file', envf] + args
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except Exception as e:
            self.get_logger().error(f'docker compose failed: {e}')

    def _mapping_running(self) -> bool:
        compose = self.get_parameter('compose_file').get_parameter_value().string_value
        envf = self.get_parameter('env_file').get_parameter_value().string_value
        try:
            out = subprocess.check_output(['docker', 'compose', '-f', compose, '--env-file', envf, 'ps', '--status', 'running'], text=True)
            return 'mapping' in out
        except Exception:
            return False


def main():
    rclpy.init()
    node = MappingAutostart()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

