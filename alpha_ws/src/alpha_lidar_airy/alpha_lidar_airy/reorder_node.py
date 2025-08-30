import os
import csv
import hashlib
import math
import struct
from typing import List, Optional

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2


def _load_yaml(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def _read_angle_table(path: str) -> Optional[List[float]]:
    """Read vertical angles from CSV. Supports two formats:
    1) Single-column CSV of numeric angles (deg or rad).
    2) Multi-column CSV with a header containing 'Vertical_Angle_deg' (legacy).
    Returns a list of floats in the given units (order-only semantics).
    """
    try:
        with open(path, 'r', newline='') as f:
            # Peek first line to detect header
            first = f.readline()
            f.seek(0)
            sample = [c.strip() for c in next(csv.reader([first]))]
            def is_float(s: str) -> bool:
                try:
                    float(s)
                    return True
                except Exception:
                    return False
            has_header = any(not is_float(tok) for tok in sample)
            if has_header:
                dr = csv.DictReader(f)
                # common header keys (case-insensitive)
                keys = [k for k in (dr.fieldnames or [])]
                keymap = {k.lower(): k for k in keys}
                col = None
                for candidate in ['vertical_angle_deg', 'vertical_angle', 'angle_deg', 'angle']:
                    if candidate in keymap:
                        col = keymap[candidate]
                        break
                if col is None and keys:
                    # Fallback: prefer the first column that parses as float on first row
                    try:
                        peek = next(iter(dr))
                        for k in keys:
                            try:
                                float((peek.get(k) or '').strip())
                                col = k
                                break
                            except Exception:
                                continue
                        # Rewind after peeking
                        f.seek(0)
                        dr = csv.DictReader(f)
                    except StopIteration:
                        return None
                if col is None:
                    return None
                vals: List[float] = []
                for row in dr:
                    cell = (row.get(col) or '').strip()
                    if not cell:
                        continue
                    try:
                        vals.append(float(cell))
                    except Exception:
                        continue
                return vals if vals else None
            else:
                # Single or multi-token numeric rows: take first column per line
                vals: List[float] = []
                for row in csv.reader(f):
                    if not row:
                        continue
                    cell = row[0].strip()
                    if not cell:
                        continue
                    vals.append(float(cell))
                return vals if vals else None
    except Exception:
        return None


class AiryReorderNode(Node):
    def __init__(self):
        super().__init__('alpha_airy_reorder')
        self.declare_parameter('config', 'alpha_configs/lidar_airy.yaml')
        self.declare_parameter('input_front_topic', '/alpha/lidar/front/points_raw')
        self.declare_parameter('input_rear_topic', '/alpha/lidar/rear/points_raw')
        cfg_path = self.get_parameter('config').get_parameter_value().string_value
        cfg = _load_yaml(cfg_path)

        self._reorder_enabled = bool(cfg.get('reorder_enabled', True))
        self._expected_h = int(cfg.get('expected_dims', {}).get('height', 96))
        self._expected_w = int(cfg.get('expected_dims', {}).get('width', 900))
        self._range_min = float(cfg.get('range_m', {}).get('min', 0.10))
        self._range_max = float(cfg.get('range_m', {}).get('max', 60.0))

        table_path = cfg.get('vertical_angle_table_path')
        # Resolve relative to the config file directory if not absolute
        if table_path and not os.path.isabs(table_path):
            table_path = os.path.join(os.path.dirname(os.path.abspath(cfg_path)), table_path)
        self._angle_table = _read_angle_table(table_path) if table_path else None
        self._row_order: Optional[List[int]] = None
        if self._angle_table is None:
            self.get_logger().warn('Angle table not found or failed to parse; pass-through mode active')
        else:
            # Log a stable hash for provenance
            try:
                with open(table_path, 'rb') as f:
                    raw = f.read()
                h = hashlib.sha256(raw).hexdigest()
                if bool(cfg.get('log_table_hash', True)):
                    self.get_logger().info(f'angle_table_sha256={h}')
            except Exception:
                pass
            # Precompute destination row order (ascending by angle)
            try:
                if len(self._angle_table) != self._expected_h:
                    self.get_logger().warn(f'Angle table length {len(self._angle_table)} != expected height {self._expected_h}; pass-through active')
                else:
                    order = sorted(range(len(self._angle_table)), key=lambda i: self._angle_table[i])
                    self._row_order = order
            except Exception as e:
                self.get_logger().warn(f'Failed to compute row order: {e}')

        qos = QoSProfile(
            depth=5,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
        )

        # Publishers for reordered clouds
        self._pub_front = self.create_publisher(PointCloud2, '/alpha/lidar/front/points', 10)
        self._pub_rear = self.create_publisher(PointCloud2, '/alpha/lidar/rear/points', 10)

        # Subscriptions to raw clouds
        front_topic = self.get_parameter('input_front_topic').get_parameter_value().string_value
        rear_topic = self.get_parameter('input_rear_topic').get_parameter_value().string_value
        self._sub_front = self.create_subscription(PointCloud2, front_topic, self._on_front, qos)
        self._sub_rear = self.create_subscription(PointCloud2, rear_topic, self._on_rear, qos)

        self.get_logger().info(f'Reorder node ready (reorder_enabled={self._reorder_enabled}, expected={self._expected_h}x{self._expected_w})')

    def _process(self, msg: PointCloud2) -> PointCloud2:
        # Validate dims
        if msg.height and msg.width:
            if msg.height != self._expected_h or msg.width != self._expected_w:
                self.get_logger().warn(f'cloud dims {msg.height}x{msg.width} != expected {self._expected_h}x{self._expected_w}; forwarding anyway')
        # Prepare output message (copy metadata)
        out = PointCloud2()
        out.header = msg.header
        out.height = msg.height
        out.width = msg.width
        out.fields = msg.fields
        out.is_bigendian = msg.is_bigendian
        out.point_step = msg.point_step
        out.row_step = msg.row_step
        out.is_dense = False

        # Work on a mutable bytearray
        src_bytes = bytes(msg.data)
        data = bytearray(src_bytes)

        # Row reorder if enabled and we have a valid order matching height
        if self._reorder_enabled and self._row_order and len(self._row_order) == msg.height:
            try:
                row_step = msg.row_step
                h = msg.height
                new_bytes = bytearray(row_step * h)
                for dest_row, src_row in enumerate(self._row_order):
                    if src_row >= h:
                        continue
                    src_off = src_row * row_step
                    dst_off = dest_row * row_step
                    new_bytes[dst_off:dst_off + row_step] = data[src_off:src_off + row_step]
                data = new_bytes
            except Exception as e:
                self.get_logger().warn(f'Row reorder failed: {e}')

        # Range gate: set x,y,z to NaN for out-of-range points if x/y/z present
        try:
            # Discover field offsets
            x_off = y_off = z_off = None
            for f in msg.fields:
                if f.name == 'x':
                    x_off = f.offset
                elif f.name == 'y':
                    y_off = f.offset
                elif f.name == 'z':
                    z_off = f.offset
            if x_off is not None and y_off is not None and z_off is not None:
                step = msg.point_step
                row_step = msg.row_step
                h = msg.height or 0
                w = msg.width or 0
                mv = memoryview(data)
                nan_bytes = struct.pack('<f', math.nan)
                for r in range(h):
                    base = r * row_step
                    for c in range(w):
                        off = base + c * step
                        try:
                            x = struct.unpack_from('<f', mv, off + x_off)[0]
                            y = struct.unpack_from('<f', mv, off + y_off)[0]
                            z = struct.unpack_from('<f', mv, off + z_off)[0]
                            d = math.sqrt(x*x + y*y + z*z)
                            if not (self._range_min <= d <= self._range_max):
                                mv[off + x_off: off + x_off + 4] = nan_bytes
                                mv[off + y_off: off + y_off + 4] = nan_bytes
                                mv[off + z_off: off + z_off + 4] = nan_bytes
                        except Exception:
                            # Skip malformed point
                            continue
        except Exception as e:
            self.get_logger().warn(f'Range gate failed: {e}')

        out.data = bytes(data)
        return out

    def _on_front(self, msg: PointCloud2):
        out = self._process(msg)
        self._pub_front.publish(out)

    def _on_rear(self, msg: PointCloud2):
        out = self._process(msg)
        self._pub_rear.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = AiryReorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
