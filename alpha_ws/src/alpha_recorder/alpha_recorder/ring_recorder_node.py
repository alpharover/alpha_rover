import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String
from alpha_utils.srv import TriggerRecord


def _now_str() -> str:
    return datetime.utcnow().strftime('%Y%m%d_%H%M%S')


class RingRecorder(Node):
    def __init__(self):
        super().__init__('alpha_ring_recorder')
        self.declare_parameter('profile_config', 'alpha_configs/recorder_profiles.yaml')
        self.declare_parameter('ring_dir', 'data/ring')
        self.declare_parameter('trigger_dir', 'data/triggers')
        self.declare_parameter('bag_duration_sec', 10)
        self.declare_parameter('enabled', True)

        cfg_path = self.get_parameter('profile_config').get_parameter_value().string_value
        self.profile = self._load_profile(cfg_path)
        self.ring_dir = Path(self.get_parameter('ring_dir').get_parameter_value().string_value)
        self.trigger_dir = Path(self.get_parameter('trigger_dir').get_parameter_value().string_value)
        self.bag_duration_sec = int(self.get_parameter('bag_duration_sec').get_parameter_value().integer_value)
        self.enabled = self.get_parameter('enabled').get_parameter_value().bool_value

        self.ring_dir.mkdir(parents=True, exist_ok=True)
        self.trigger_dir.mkdir(parents=True, exist_ok=True)

        self.status_pub = self.create_publisher(String, '/alpha/recorder/status', QoSProfile(depth=10))
        self.srv = self.create_service(TriggerRecord, '/alpha/recorder/trigger', self.on_trigger)

        self.ring_proc = None
        self._ensure_ring_running()
        self.timer = self.create_timer(2.0, self._tick)

    def _load_profile(self, path: str) -> dict:
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.get_logger().warn(f'Failed to read recorder profile {path}: {e}; using defaults')
            return {'continuous': {'topics': []}, 'triggered': {'pre_sec': 30, 'post_sec': 60}}

    def _status(self, text: str):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)

    def _ensure_ring_running(self):
        if not self.enabled:
            self._status('RING_DISABLED')
            return
        if self.ring_proc and self.ring_proc.poll() is None:
            return
        topics: List[str] = list(self.profile.get('continuous', {}).get('topics', []))
        # Compute keep count from retention
        retention = int(self.profile.get('continuous', {}).get('retention_sec', 300))
        keep_n = max(1, int((retention + self.bag_duration_sec - 1) // self.bag_duration_sec))
        # Launch ros2 bag record with rotation; use cwd=ring_dir
        cmd = [
            'ros2', 'bag', 'record',
            '--max-bag-duration', str(self.bag_duration_sec),
        ]
        if topics:
            cmd.extend(topics)
        else:
            cmd.append('--all')
        self.get_logger().info(f'Starting ring recorder: {cmd} (cwd={self.ring_dir})')
        try:
            self.ring_proc = subprocess.Popen(cmd, cwd=str(self.ring_dir))
            self._status('RING_ACTIVE')
        except Exception as e:
            self.get_logger().error(f'Failed to start ring recorder: {e}')
            self._status('RING_ERROR')

        # Trim old segments periodically in timer
        self.keep_n = keep_n

    def _list_ring_segments(self) -> List[Path]:
        # ros2 bag creates directories per run/segment; consider any directory with metadata.yaml
        segs = []
        for p in self.ring_dir.iterdir():
            try:
                if p.is_dir() and (p / 'metadata.yaml').exists():
                    segs.append(p)
            except Exception:
                continue
        segs.sort(key=lambda p: p.stat().st_mtime)
        return segs

    def _trim_ring(self):
        segs = self._list_ring_segments()
        excess = len(segs) - self.keep_n
        for i in range(max(0, excess)):
            try:
                shutil.rmtree(segs[i], ignore_errors=True)
            except Exception:
                pass

    def _tick(self):
        self._ensure_ring_running()
        self._trim_ring()

    def on_trigger(self, req: TriggerRecord.Request, resp: TriggerRecord.Response):
        reason = req.reason or 'manual'
        pre_sec = int(self.profile.get('triggered', {}).get('pre_sec', 30))
        post_sec = int(self.profile.get('triggered', {}).get('post_sec', 60))
        # Copy last N segments covering pre_sec
        n_pre = max(1, int((pre_sec + self.bag_duration_sec - 1) // self.bag_duration_sec))
        segs = self._list_ring_segments()
        picked = segs[-n_pre:] if segs else []
        bag_id = f'{_now_str()}_{reason.replace(" ", "_")}'
        dest = self.trigger_dir / bag_id
        dest.mkdir(parents=True, exist_ok=True)
        for p in picked:
            try:
                shutil.copytree(p, dest / p.name)
            except Exception as e:
                self.get_logger().warn(f'Failed to copy {p} to trigger: {e}')

        # Start post-capture in the background to dest directory
        topics: List[str] = list(self.profile.get('triggered', {}).get('topics', []))
        post_cmd = ['ros2', 'bag', 'record']
        if topics:
            post_cmd.extend(topics)
        else:
            post_cmd.append('--all')
        self.get_logger().info(f'Starting post-capture for {post_sec}s into {dest} (cmd={post_cmd})')

        def _run_post():
            try:
                proc = subprocess.Popen(post_cmd, cwd=str(dest))
                time.sleep(post_sec)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
            except Exception as e:
                self.get_logger().error(f'post-capture failed: {e}')

        threading.Thread(target=_run_post, daemon=True).start()
        resp.started = True
        resp.bag_id = bag_id
        resp.message = 'ok'
        self._status(f'TRIGGERED:{bag_id}')
        return resp


def main(args=None):
    rclpy.init(args=args)
    node = RingRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

