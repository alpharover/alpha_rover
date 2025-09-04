#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import String

CTRL_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

ANN = '/alpha/test/announce'
RDY = '/alpha/test/ready'
GO  = '/alpha/test/go'
DONE= '/alpha/test/done'

class Coordinator(Node):
    def __init__(self):
        super().__init__('jetson_coordinator')
        self.announce_pub = self.create_publisher(String, ANN, CTRL_QOS)
        self.go_pub       = self.create_publisher(String, GO,  CTRL_QOS)
        self.done_pub     = self.create_publisher(String, DONE,CTRL_QOS)
        self.ready_sub    = self.create_subscription(String, RDY, self._on_ready, CTRL_QOS)
        self.done_sub     = self.create_subscription(String, DONE, self._on_done, CTRL_QOS)
        self._waiting_id: Optional[str] = None
        self._ready_seen = False
        self._pi_done: Optional[dict] = None

    def _on_ready(self, msg: String):
        try:
            data = json.loads(msg.data)
        except Exception:
            return
        if self._waiting_id and data.get('id') == self._waiting_id:
            self._ready_seen = True
            self.get_logger().info(f"ready for id={self._waiting_id}")

    def _on_done(self, msg: String):
        try:
            data = json.loads(msg.data)
        except Exception:
            return
        if self._waiting_id and data.get('id') == self._waiting_id:
            # Accept first done from Pi; store
            self._pi_done = data
            self.get_logger().info(f"pi done for id={self._waiting_id}: {data}")

    def announce(self, tid: str, name: str, params: dict):
        msg = {
            'side': 'jetson',
            'id': tid,
            'name': name,
            'status': 'announce',
            'params': params,
            'ts': time.time()
        }
        self.announce_pub.publish(String(data=json.dumps(msg)))

    def publish_go(self, tid: str):
        msg = {'side': 'jetson', 'id': tid, 'status': 'go', 'ts': time.time()}
        self.go_pub.publish(String(data=json.dumps(msg)))

    def publish_done(self, tid: str, result: str, note: str):
        msg = {'side': 'jetson', 'id': tid, 'status': 'done', 'result': result, 'note': note, 'ts': time.time()}
        self.done_pub.publish(String(data=json.dumps(msg)))

    def wait_for_ready(self, tid: str, timeout_s: float) -> bool:
        self._waiting_id = tid
        self._ready_seen = False
        self._pi_done = None
        t0 = time.time()
        # Re-announce every 2s until ready
        next_announce = t0
        while time.time() - t0 < timeout_s and rclpy.ok():
            now = time.time()
            if now >= next_announce:
                # Re-emit last announce (so late subscribers see it even if transient missed)
                # Using params from previous name is not stored; send minimal announce with id only
                self.announce_pub.publish(String(data=json.dumps({'side':'jetson','id':tid,'status':'announce','ts':time.time()})))
                next_announce = now + 2.0
            rclpy.spin_once(self, timeout_sec=0.2)
            if self._ready_seen:
                return True
        return False

    def wait_for_pi_done(self, tid: str, timeout_s: float) -> Optional[dict]:
        t0 = time.time()
        while time.time() - t0 < timeout_s and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.2)
            if self._pi_done is not None:
                return self._pi_done
        return None


def sh(cmd: str, env=None, timeout: Optional[int]=None) -> int:
    return subprocess.call(cmd, shell=True, env=env, timeout=timeout)


def run_smoke_chatter(node: Coordinator, tid: str) -> (str, str):
    # Start a namespaced talker for a bounded duration
    env = os.environ.copy()
    # Run for ~12 seconds; remap /chatter -> /alpha/test/chatter and node name to talker@jetson
    cmd = "timeout 12s ros2 run demo_nodes_cpp talker --ros-args -r chatter:=/alpha/test/chatter -r __node:=talker_jetson"
    node.get_logger().info(f"starting talker: {cmd}")
    rc = sh(cmd, env=env)
    note = f"talker exited rc={rc}"
    # Wait for Pi done up to 10s after talker exit
    pi_done = node.wait_for_pi_done(tid, timeout_s=10.0)
    if pi_done and pi_done.get('result') == 'pass':
        return 'pass', note
    else:
        return 'fail', note + f"; pi_done={pi_done}"


def run_heartbeat(node: Coordinator, tid: str) -> (str, str):
    # Ensure adapter heartbeat visible locally (explicit type) as a sanity check
    env = os.environ.copy()
    check_cmd = "timeout 6s ros2 topic echo --once /alpha/health/adapter_alive std_msgs/msg/Bool >/dev/null 2>&1"
    local_ok = (sh(check_cmd, env=env) == 0)
    note = f"local_hb={'ok' if local_ok else 'miss'}"
    # Wait for Pi done up to 15s
    pi_done = node.wait_for_pi_done(tid, timeout_s=15.0)
    if pi_done and pi_done.get('result') == 'pass':
        return 'pass', note
    else:
        return 'fail', note + f"; pi_done={pi_done}"


def main():
    rclpy.init()
    node = Coordinator()
    # Determine which test(s)
    tests = ['smoke_chatter', 'heartbeat']
    all_pass = True

    # Pre-clean: kill stray talkers; ensure at most one robot_state_publisher
    # Kill all demo talkers/listeners leftover
    sh("pkill -f 'demo_nodes_cpp talker' || true")
    sh("pkill -x talker || true")
    sh("pkill -x listener || true")
    # Robot state publisher duplicates: keep oldest; kill newer
    try:
        out = subprocess.check_output("pgrep -af robot_state_publisher | awk '{print $1}'", shell=True, text=True).strip().split() if True else []
    except subprocess.CalledProcessError:
        out = []
    if len(out) > 1:
        keep = out[0]
        for pid in out[1:]:
            sh(f"kill {pid} || true")
    # Run tests
    results = []
    for name in tests:
        tid = f"{name}-{int(time.time())}"
        if name == 'smoke_chatter':
            params = {'ns': '/alpha/test', 'topic': '/alpha/test/chatter'}
        else:
            params = {'ns': '/alpha/test'}
        node.get_logger().info(f"announce {name} id={tid}")
        node.announce(tid, name, params)
        if not node.wait_for_ready(tid, timeout_s=60.0):
            node.publish_done(tid, 'fail', 'no-ready-from-pi')
            results.append((name, 'fail', 'no-ready-from-pi'))
            all_pass = False
            continue
        node.publish_go(tid)
        if name == 'smoke_chatter':
            result, note = run_smoke_chatter(node, tid)
        else:
            result, note = run_heartbeat(node, tid)
        node.publish_done(tid, result, note)
        results.append((name, result, note))
        # small gap
        time.sleep(1.0)

    # Print a concise summary for stdout
    for name, result, note in results:
        print(f"TEST {name}: {result} — {note}")

    rclpy.shutdown()

if __name__ == '__main__':
    main()
