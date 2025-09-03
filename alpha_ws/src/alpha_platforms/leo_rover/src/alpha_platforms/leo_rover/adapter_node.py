import importlib
import yaml
from copy import deepcopy
from typing import Any, Dict
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rclpy.executors import MultiThreadedExecutor

from std_msgs.msg import Bool
from ament_index_python.packages import get_package_share_directory


def _import_msg(type_str: str):
    mod, _, cls = type_str.rpartition('/')
    mod = mod.replace('/', '.')
    return getattr(importlib.import_module(mod), cls)


def _qos_profile(x: Any) -> QoSProfile:
    if isinstance(x, dict):
        return QoSProfile(
            depth=int(x.get('depth', 5)),
            reliability=(ReliabilityPolicy.RELIABLE if str(x.get('reliability','')).lower()=='reliable' else ReliabilityPolicy.BEST_EFFORT),
            durability=(DurabilityPolicy.TRANSIENT_LOCAL if str(x.get('durability','')).lower()=='transient_local' else DurabilityPolicy.VOLATILE),
            history=HistoryPolicy.KEEP_LAST,
        )
    name = str(x).upper()
    if name in ('SENSOR_DATA','SENSOR_DATA_QOS'):
        return QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST)
    if name in ('RELIABLE_TRANSIENT_LOCAL','LATCHED'):
        return QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL, history=HistoryPolicy.KEEP_LAST)
    if name in ('RELIABLE',):
        return QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST)
    return QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST)


class Bridge:
    def __init__(self, node: Node, cfg: Dict[str, Any]):
        self.node = node
        self.type_str = cfg['type']
        self.MsgType = _import_msg(self.type_str)
        self.in_topic = cfg['in']
        self.out_topic = cfg['out']
        self.in_qos = _qos_profile(cfg.get('in_qos','RELIABLE'))
        self.out_qos = _qos_profile(cfg.get('out_qos','RELIABLE'))
        self.frame_override = cfg.get('frame_id_override')
        self.child_frame_override = cfg.get('child_frame_id_override')
        self.stamp = cfg.get('stamp','passthrough')
        self.pub = node.create_publisher(self.MsgType, self.out_topic, self.out_qos)

        def cb(msg):
            out = msg
            try:
                out = deepcopy(msg)
            except Exception:
                pass
            h = getattr(out, 'header', None)
            if h is not None:
                if self.frame_override:
                    h.frame_id = self.frame_override
                if self.stamp == 'now':
                    h.stamp = self.node.get_clock().now().to_msg()
            if self.child_frame_override and hasattr(out,'child_frame_id'):
                out.child_frame_id = self.child_frame_override
            self.pub.publish(out)

        self.sub = node.create_subscription(self.MsgType, self.in_topic, cb, self.in_qos)
        node.get_logger().info(f"[bridge] {self.type_str}: {self.in_topic} -> {self.out_topic}")


class LeoAdapter(Node):
    def __init__(self):
        super().__init__('leorover_adapter')
        pkg_share = Path(get_package_share_directory('alpha_platforms_leo_rover'))
        default_cfg = pkg_share / 'config' / 'leo_rover.yaml'
        cfg_path = Path(self.declare_parameter('mapping_config', str(default_cfg)).value)
        with open(cfg_path,'r') as f:
            self.cfg = yaml.safe_load(f) or {}

        # Start with configured mappings
        configured = list(self.cfg.get('mappings', []))

        # Helper to see if an output mapping already exists
        def has_out(out_topic: str, type_str: str) -> bool:
            for m in configured:
                if m.get('out') == out_topic and m.get('type') == type_str:
                    return True
            return False

        # Always ensure /alpha/cmd_vel -> /cmd_vel bridge exists
        twist_map = {
            'type': 'geometry_msgs/msg/Twist',
            'in': '/alpha/cmd_vel',
            'out': '/cmd_vel',
            'in_qos': 'RELIABLE',
            'out_qos': 'RELIABLE',
        }
        if not any(m.get('type') == twist_map['type'] and m.get('in') == twist_map['in'] and m.get('out') == twist_map['out'] for m in configured):
            configured.append(twist_map)

        # Auto-discover odom/camera topics on the platform side (non-/alpha)
        try:
            topics = self.get_topic_names_and_types(no_demangle=True)
        except TypeError:
            # Fallback for rclpy versions without keyword
            topics = self.get_topic_names_and_types()

        # Build a quick lookup of type->topics
        type_to_topics = {}
        for name, types in topics:
            # Skip our own namespace topics
            if name.startswith('/alpha/'):
                continue
            for t in types:
                type_to_topics.setdefault(t, []).append(name)

        # Odometry -> /alpha/odom (RELIABLE)
        odom_type = 'nav_msgs/msg/Odometry'
        if not has_out('/alpha/odom', odom_type):
            srcs = type_to_topics.get(odom_type, [])
            if srcs:
                configured.append({
                    'type': odom_type,
                    'in': srcs[0],
                    'out': '/alpha/odom',
                    'in_qos': 'RELIABLE',
                    'out_qos': 'RELIABLE',
                })

        # Image -> two targets (SENSOR_DATA)
        img_type = 'sensor_msgs/msg/Image'
        img_srcs = type_to_topics.get(img_type, [])
        if img_srcs:
            img_in = img_srcs[0]
            for out_topic in ('/alpha/camera/front/image', '/alpha/cam/front/image_color'):
                if not has_out(out_topic, img_type):
                    configured.append({
                        'type': img_type,
                        'in': img_in,
                        'out': out_topic,
                        'in_qos': 'SENSOR_DATA',
                        'out_qos': 'SENSOR_DATA',
                    })

        # CameraInfo -> two targets (RELIABLE)
        cinfo_type = 'sensor_msgs/msg/CameraInfo'
        cinfo_srcs = type_to_topics.get(cinfo_type, [])
        if cinfo_srcs:
            cinfo_in = cinfo_srcs[0]
            for out_topic in ('/alpha/camera/front/camera_info', '/alpha/cam/front/camera_info'):
                if not has_out(out_topic, cinfo_type):
                    configured.append({
                        'type': cinfo_type,
                        'in': cinfo_in,
                        'out': out_topic,
                        'in_qos': 'RELIABLE',
                        'out_qos': 'RELIABLE',
                    })

        # Instantiate bridges
        self.bridges = [Bridge(self, m) for m in configured]

        # Heartbeat
        # Publish heartbeat under this node's namespace (alpha/health/adapter_alive)
        self.hb = self.create_publisher(Bool, 'health/adapter_alive', QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        self.get_logger().info(f"Node NS={self.get_namespace()} name={self.get_name()} — heartbeat topic=/{self.get_namespace().strip('/')}/health/adapter_alive")
        # Publish once immediately so the topic appears quickly
        try:
            self.hb.publish(Bool(data=True))
        except Exception:
            pass
        self.create_timer(1.0, lambda: self.hb.publish(Bool(data=True)))
        self.get_logger().info(f"Loaded config: {cfg_path}; active bridges={len(self.bridges)}")


def main():
    rclpy.init()
    node = LeoAdapter()
    exec = MultiThreadedExecutor()
    exec.add_node(node)
    try:
        exec.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
