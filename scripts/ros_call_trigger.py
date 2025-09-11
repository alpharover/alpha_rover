#!/usr/bin/env python3
import sys
import argparse
import rclpy
from rclpy.node import Node
from rclpy.task import Future
from std_srvs.srv import Trigger


class TriggerClient(Node):
    def __init__(self, service_name: str):
        super().__init__('trigger_client')
        self.cli = self.create_client(Trigger, service_name)
        self.req = Trigger.Request()

    def call(self, timeout: float) -> bool:
        if not self.cli.wait_for_service(timeout_sec=timeout):
            self.get_logger().error(f'Service not available: {self.cli.srv_name}')
            return False
        future: Future = self.cli.call_async(self.req)
        if rclpy.spin_until_future_complete(self, future, timeout_sec=timeout):
            resp = future.result()
            if resp is None:
                self.get_logger().error('No response (result is None)')
                return False
            self.get_logger().info(f'success={resp.success} message="{resp.message}"')
            return bool(resp.success)
        else:
            self.get_logger().error('Timed out waiting for service response')
            return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Call a std_srvs/Trigger service.')
    parser.add_argument('service', help='Service name, e.g., /firmware/boot')
    parser.add_argument('--timeout', type=float, default=30.0, help='Timeout seconds for discovery and response')
    args = parser.parse_args(argv)

    rclpy.init()
    node = TriggerClient(args.service)
    try:
        ok = node.call(timeout=args.timeout)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

