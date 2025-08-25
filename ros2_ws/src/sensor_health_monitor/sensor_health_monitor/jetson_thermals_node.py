import glob
import os
import time
from typing import Dict, Tuple

import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue


def read_thermal_zones() -> Dict[str, float]:
    zones = {}
    for type_path in glob.glob('/sys/devices/virtual/thermal/thermal_zone*/type'):
        try:
            zone_dir = os.path.dirname(type_path)
            with open(type_path, 'r') as f:
                name = f.read().strip()
            with open(os.path.join(zone_dir, 'temp'), 'r') as f:
                # values are typically in millidegree C
                millideg = int(f.read().strip())
                temp_c = millideg / 1000.0
            zones[name] = temp_c
        except Exception:
            continue
    return zones


def classify(name: str) -> str:
    n = name.lower()
    if 'gpu' in n:
        return 'GPU'
    if 'cpu' in n:
        return 'CPU'
    if 'pmic' in n:
        return 'PMIC'
    if 'board' in n or 'p-therm' in n or 'skin' in n:
        return 'BOARD'
    if 'cv' in n or 'soc' in n or 'ao' in n:
        return 'SOC'
    return name


class JetsonThermals(Node):
    def __init__(self):
        super().__init__('jetson_thermals')
        self.pub = self.create_publisher(DiagnosticArray, '/diagnostics', 10)
        hz = self.declare_parameter('rate_hz', 1.0).get_parameter_value().double_value
        self.warn_c = self.declare_parameter('warn_c', 80.0).get_parameter_value().double_value
        self.error_c = self.declare_parameter('error_c', 90.0).get_parameter_value().double_value
        self.timer = self.create_timer(1.0 / max(0.1, hz), self.tick)

    def tick(self):
        zones = read_thermal_zones()
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()

        for raw_name, temp in zones.items():
            status = DiagnosticStatus()
            status.name = f'jetson/{classify(raw_name)}'
            status.hardware_id = 'jetson'
            if temp >= self.error_c:
                status.level = DiagnosticStatus.ERROR
                status.message = 'OVERHEAT'
            elif temp >= self.warn_c:
                status.level = DiagnosticStatus.WARN
                status.message = 'HOT'
            else:
                status.level = DiagnosticStatus.OK
                status.message = 'OK'

            kv = KeyValue()
            kv.key = 'temperature_celsius'
            kv.value = f'{temp:.2f}'
            status.values.append(kv)
            kv2 = KeyValue()
            kv2.key = 'raw_zone'
            kv2.value = raw_name
            status.values.append(kv2)
            arr.status.append(status)

        self.pub.publish(arr)


def main():
    rclpy.init()
    node = JetsonThermals()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

