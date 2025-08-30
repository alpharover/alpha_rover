import shlex
import subprocess
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import Int32, String
from alpha_utils.msg import Event


class VideoController(Node):
    def __init__(self):
        super().__init__('alpha_video_controller')
        self.declare_parameter('apply_shell_cmd', '')  # optional shell template, e.g., 'nvenc_ctl --fps {fps} --bitrate {bitrate}'
        qos = QoSProfile(depth=10)
        self.sub_fps = self.create_subscription(Int32, '/alpha/video/target_fps', self._on_fps, qos)
        self.sub_br = self.create_subscription(Int32, '/alpha/video/target_bitrate', self._on_br, qos)
        self.status_pub = self.create_publisher(String, '/alpha/video/status', 10)
        self.events_pub = self.create_publisher(Event, '/alpha/events', 10)
        self._last_fps: Optional[int] = None
        self._last_br: Optional[int] = None

    def _apply(self):
        if self._last_fps is None or self._last_br is None:
            return
        status = String()
        status.data = f'APPLIED fps={self._last_fps} bitrate={self._last_br}'
        self.status_pub.publish(status)
        ev = Event()
        ev.stamp = self.get_clock().now().to_msg()  # type: ignore
        ev.type = 'VIDEO_APPLY'
        ev.details = status.data
        self.events_pub.publish(ev)
        cmd_tmpl = self.get_parameter('apply_shell_cmd').get_parameter_value().string_value
        if cmd_tmpl:
            try:
                cmd = cmd_tmpl.format(fps=self._last_fps, bitrate=self._last_br)
                self.get_logger().info(f'Applying video settings via shell: {cmd}')
                subprocess.Popen(shlex.split(cmd))
            except Exception as e:
                self.get_logger().warn(f'apply_shell_cmd failed: {e}')

    def _on_fps(self, msg: Int32):
        self._last_fps = int(msg.data)
        self._apply()

    def _on_br(self, msg: Int32):
        self._last_br = int(msg.data)
        self._apply()


def main(args=None):
    rclpy.init(args=args)
    node = VideoController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

