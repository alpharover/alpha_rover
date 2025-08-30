import time
import yaml
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from alpha_utils.srv import SetLidarMode


class StartupSequencer(Node):
    def __init__(self):
        super().__init__('alpha_startup_sequencer')
        self.declare_parameter('sequence_config', 'alpha_configs/startup_sequence.yaml')
        self.declare_parameter('dry_run', True)
        self.status_pub = self.create_publisher(String, '/alpha/mapping/startup_status', 10)
        self.cli = self.create_client(SetLidarMode, '/alpha/ui/cmd/lidar_mode')

    def publish_status(self, s: str):
        msg = String()
        msg.data = s
        self.status_pub.publish(msg)
        self.get_logger().info(f'status={s}')

    def _call_set_mode(self, target: str, op_mode: int, timeout_sec: float = 3.0) -> bool:
        if not self.cli.wait_for_service(timeout_sec=timeout_sec):
            self.get_logger().warn('lidar_mode service not available')
            return False
        req = SetLidarMode.Request()
        req.target = target
        req.op_mode = op_mode
        fut = self.cli.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout_sec)
        if not fut.done():
            self.get_logger().warn('lidar_mode call timed out')
            return False
        resp = fut.result()
        ok = bool(resp and resp.accepted)
        if not ok:
            self.get_logger().warn(f'lidar_mode rejected: {getattr(resp, "message", "no message")}')
        return ok

    def run(self):
        cfg_path = self.get_parameter('sequence_config').get_parameter_value().string_value
        dry_run = self.get_parameter('dry_run').get_parameter_value().bool_value
        with open(cfg_path, 'r') as f:
            seq = yaml.safe_load(f)
        steps = seq.get('steps', [])
        self.publish_status('WAITING_FOR_LIDAR')
        for step in steps:
            if 'set_lidar_mode' in step:
                params = step['set_lidar_mode']
                target = params.get('target', 'both')
                op_mode = int(params.get('op_mode', 1))
                if dry_run:
                    self.get_logger().info(f'DRY-RUN: set_lidar_mode target={target} op_mode={op_mode}')
                else:
                    self._call_set_mode(target, op_mode)
            elif 'wait' in step:
                sec = float(step['wait'].get('seconds', 1))
                self.publish_status('SPINNING_UP')
                time.sleep(sec)
            elif 'start_node' in step:
                params = step['start_node']
                self.get_logger().info(f"START_NODE placeholder: {params}")
            else:
                self.get_logger().warn(f'Unknown step: {step}')
        self.publish_status('STARTED')


def main():
    rclpy.init()
    node = StartupSequencer()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()

