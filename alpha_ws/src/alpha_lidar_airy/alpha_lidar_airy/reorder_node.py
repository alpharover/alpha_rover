import os
import csv
import hashlib
import math
import struct
import time
from collections import deque
from typing import List, Optional

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

try:
    import numpy as np  # type: ignore
    _NP_OK = True
except Exception:
    _NP_OK = False


def _load_yaml(path: str) -> dict:
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # Gracefully handle missing/invalid config by returning empty
        return {}


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
        self.declare_parameter('strict', False)
        self.declare_parameter('target_rate_hz', 0.0)  # 0 => no throttle
        self.declare_parameter('range_gate_enabled', False)
        self.declare_parameter('range_min_m', 0.10)
        self.declare_parameter('range_max_m', 60.0)
        self.declare_parameter('backend', 'numpy')  # python|numpy|cpp
        self.declare_parameter('timestamp_policy', 'sensor')  # sensor|node
        cfg_path = self.get_parameter('config').get_parameter_value().string_value
        cfg = _load_yaml(cfg_path)

        self._reorder_enabled = bool(cfg.get('reorder_enabled', True))
        self._expected_h = int(cfg.get('expected_dims', {}).get('height', 96))
        self._expected_w = int(cfg.get('expected_dims', {}).get('width', 900))
        self._range_min = float(self.get_parameter('range_min_m').get_parameter_value().double_value)
        self._range_max = float(self.get_parameter('range_max_m').get_parameter_value().double_value)
        # Allow YAML to override range gate bounds if provided
        try:
            rg = cfg.get('range_m', {}) if isinstance(cfg, dict) else {}
            if isinstance(rg, dict):
                if rg.get('min') is not None:
                    self._range_min = float(rg['min'])
                if rg.get('max') is not None:
                    self._range_max = float(rg['max'])
        except Exception:
            pass
        self._range_gate_enabled = bool(self.get_parameter('range_gate_enabled').get_parameter_value().bool_value)
        self._timestamp_policy = (self.get_parameter('timestamp_policy').get_parameter_value().string_value or 'sensor').lower()
        self._backend = (self.get_parameter('backend').get_parameter_value().string_value or 'numpy').lower()
        if self._backend == 'numpy' and not _NP_OK:
            self.get_logger().warn('NumPy not available; falling back to python backend')
            self._backend = 'python'

        table_path = cfg.get('vertical_angle_table_path')
        # Resolve relative to the config file directory if not absolute
        if table_path and not os.path.isabs(table_path):
            table_path = os.path.join(os.path.dirname(os.path.abspath(cfg_path)), table_path)
        self._angle_table = _read_angle_table(table_path) if table_path else None
        self._row_order: Optional[List[int]] = None
        strict = self.get_parameter('strict').get_parameter_value().bool_value
        if self._angle_table is None:
            msg = 'Angle table not found or failed to parse'
            if strict:
                raise RuntimeError(msg)
            self.get_logger().warn(msg + '; pass-through mode active')
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
                    msg = f'Angle table length {len(self._angle_table)} != expected height {self._expected_h}'
                    if strict:
                        raise RuntimeError(msg)
                    self.get_logger().warn(msg + '; pass-through active')
                else:
                    order = sorted(range(len(self._angle_table)), key=lambda i: self._angle_table[i])
                    self._row_order = order
            except Exception as e:
                self.get_logger().warn(f'Failed to compute row order: {e}')

        qos = qos_profile_sensor_data

        # Publishers for reordered clouds (sensor data QoS)
        self._pub_front = self.create_publisher(PointCloud2, '/alpha/lidar/front/points', qos_profile_sensor_data)
        self._pub_rear = self.create_publisher(PointCloud2, '/alpha/lidar/rear/points', qos_profile_sensor_data)

        # Subscriptions to raw clouds
        front_topic = self.get_parameter('input_front_topic').get_parameter_value().string_value
        rear_topic = self.get_parameter('input_rear_topic').get_parameter_value().string_value
        self._sub_front = self.create_subscription(PointCloud2, front_topic, self._on_front, qos)
        self._sub_rear = self.create_subscription(PointCloud2, rear_topic, self._on_rear, qos)

        self.get_logger().info(
            f'Reorder node ready (backend={self._backend}, ts_policy={self._timestamp_policy}, reorder_enabled={self._reorder_enabled}, expected={self._expected_h}x{self._expected_w})'
        )
        # Degrade budget subscription to adjust target rate
        try:
            from alpha_utils.msg import DegradeBudget  # type: ignore
            self._budget_sub = self.create_subscription(DegradeBudget, '/alpha/comms/budget_intent', self._on_budget, 10)
        except Exception:
            self._budget_sub = None
        self._target_rate_hz = float(self.get_parameter('target_rate_hz').get_parameter_value().double_value)
        self._last_pub_front = 0.0
        self._last_pub_rear = 0.0
        # Metrics
        self._lat_front = deque(maxlen=600)
        self._lat_rear = deque(maxlen=600)
        self._count_front = deque(maxlen=100)
        self._count_rear = deque(maxlen=100)
        self._pad_frames_front = 0
        self._pad_frames_rear = 0
        self._diag_pub = self.create_publisher(DiagnosticArray, '/diagnostics', 10)
        self._diag_timer = self.create_timer(1.0, self._publish_diagnostics)

    def _publish_diagnostics(self):
        try:
            def p50p95(items):
                if not items:
                    return (0.0, 0.0)
                arr = sorted(items)
                n = len(arr)
                p50 = arr[min(n - 1, int(0.50 * n))]
                p95 = arr[min(n - 1, int(0.95 * n))]
                return (p50, p95)

            now = time.time()
            def rate(deq: deque):
                while deq and now - deq[0] > 10.0:
                    deq.popleft()
                if len(deq) < 2:
                    return 0.0
                duration = deq[-1] - deq[0]
                return (len(deq) - 1) / duration if duration > 0 else 0.0

            p50_f, p95_f = p50p95(list(self._lat_front))
            p50_r, p95_r = p50p95(list(self._lat_rear))
            rate_f = rate(self._count_front)
            rate_r = rate(self._count_rear)

            def kv(k, v):
                return KeyValue(key=k, value=str(v))

            st = DiagnosticStatus()
            st.level = DiagnosticStatus.OK
            st.name = 'alpha_lidar_airy/reorder'
            st.message = 'reorder metrics'
            st.values = [
                kv('reorder_backend', self._backend),
                kv('reorder_latency_ms.front.p50', round(p50_f * 1000.0, 3)),
                kv('reorder_latency_ms.front.p95', round(p95_f * 1000.0, 3)),
                kv('reorder_latency_ms.rear.p50', round(p50_r * 1000.0, 3)),
                kv('reorder_latency_ms.rear.p95', round(p95_r * 1000.0, 3)),
                kv('points_rate_hz.front', round(rate_f, 3)),
                kv('points_rate_hz.rear', round(rate_r, 3)),
                kv('dropped_or_padded_frames.front', self._pad_frames_front),
                kv('dropped_or_padded_frames.rear', self._pad_frames_rear),
            ]
            arr = DiagnosticArray()
            arr.status = [st]
            self._diag_pub.publish(arr)
        except Exception:
            pass

    def _process(self, msg: PointCloud2) -> PointCloud2:
        # Prepare output message skeleton
        out = PointCloud2()
        out.header = msg.header
        out.fields = msg.fields
        out.is_bigendian = msg.is_bigendian
        out.point_step = msg.point_step
        out.is_dense = False

        # Copy data into mutable buffer
        data = bytearray(bytes(msg.data))
        h = msg.height or 0
        w = msg.width or 0

        # Transpose if dimensions are swapped (e.g., 900x96 instead of 96x900)
        if (h == self._expected_w and w == self._expected_h) or (w == self._expected_h and h > w):
            try:
                step = msg.point_step
                src_row_step = msg.row_step
                new_h = self._expected_h
                new_w = self._expected_w
                if self._backend == 'numpy' and _NP_OK and src_row_step == step * w:
                    buf = np.frombuffer(data, dtype=np.uint8)
                    arr = buf.reshape(h, w, step)
                    arr_t = np.transpose(arr, (1, 0, 2))
                    data = bytearray(arr_t.reshape(new_h * new_w * step).tobytes())
                else:
                    new_row_step = step * new_w
                    new_bytes = bytearray(new_row_step * new_h)
                    mv_src = memoryview(data)
                    mv_dst = memoryview(new_bytes)
                    for r in range(new_h):
                        for c in range(new_w):
                            src_off = c * src_row_step + r * step
                            dst_off = r * new_row_step + c * step
                            mv_dst[dst_off:dst_off+step] = mv_src[src_off:src_off+step]
                    data = new_bytes
                h, w = new_h, new_w
            except Exception as e:
                self.get_logger().warn(f'transpose failed: {e}')

        # (Defer dimension warning until after normalization below)

        # Row reorder if enabled and order matches height
        if self._reorder_enabled and self._row_order and len(self._row_order) == h:
            try:
                row_step = out.point_step * w
                if self._backend == 'numpy' and _NP_OK:
                    buf = np.frombuffer(data, dtype=np.uint8)
                    arr = buf.reshape(h, row_step)
                    order = np.array(self._row_order, dtype=np.int64)
                    data = bytearray(arr[order, :].reshape(h * row_step).tobytes())
                else:
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

        # Range gate (optional): set x,y,z to NaN for out-of-range points
        if self._range_gate_enabled:
            try:
                x_off = y_off = z_off = None
                for f in msg.fields:
                    if f.name == 'x': x_off = f.offset
                    elif f.name == 'y': y_off = f.offset
                    elif f.name == 'z': z_off = f.offset
                if x_off is not None and y_off is not None and z_off is not None:
                    step = out.point_step
                    row_step = step * w
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
                                continue
            except Exception as e:
                self.get_logger().warn(f'Range gate failed: {e}')

        # Normalize to exact expected dims (pad/truncate)
        try:
            step = out.point_step
            # Width normalization first if height matches
            if h == self._expected_h and w != self._expected_w:
                new_w = self._expected_w
                new_row_step = step * new_w
                new_bytes = bytearray(new_row_step * h)
                mv_src = memoryview(data)
                mv_dst = memoryview(new_bytes)
                for r in range(h):
                    cols = min(w, new_w)
                    mv_dst[r*new_row_step : r*new_row_step + cols*step] = mv_src[r*(step*w) : r*(step*w) + cols*step]
                data = new_bytes
                if new_w > w:
                    # padded columns
                    self._pad_frames_front += int('front' in (out.header.frame_id or ''))
                    self._pad_frames_rear += int('rear' in (out.header.frame_id or ''))
                w = new_w
            # Height normalization if needed
            if h != self._expected_h:
                new_h = self._expected_h
                row_step = step * w
                new_bytes = bytearray(row_step * new_h)
                mv_src = memoryview(data)
                mv_dst = memoryview(new_bytes)
                rows = min(h, new_h)
                mv_dst[0:rows*row_step] = mv_src[0:rows*row_step]
                data = new_bytes
                if new_h > h:
                    self._pad_frames_front += int('front' in (out.header.frame_id or ''))
                    self._pad_frames_rear += int('rear' in (out.header.frame_id or ''))
                h = new_h
        except Exception as e:
            self.get_logger().warn(f'normalize dims failed: {e}')

        out.height = h
        out.width = w
        out.row_step = out.point_step * w
        out.data = bytes(data)
        # Timestamp policy
        try:
            if self._timestamp_policy == 'node':
                out.header.stamp = self.get_clock().now().to_msg()
            else:
                out.header.stamp = msg.header.stamp
        except Exception:
            pass

        # Final sanity: warn if still unexpected after normalization
        if out.height != self._expected_h or out.width != self._expected_w:
            self.get_logger().warn(
                f'cloud dims {out.height}x{out.width} != expected {self._expected_h}x{self._expected_w}; forwarding anyway'
            )
        return out

    def _on_front(self, msg: PointCloud2):
        if self._should_publish('front'):
            t0 = time.time()
            out = self._process(msg)
            self._pub_front.publish(out)
            self._lat_front.append(time.time() - t0)
            self._count_front.append(time.time())

    def _on_rear(self, msg: PointCloud2):
        if self._should_publish('rear'):
            t0 = time.time()
            out = self._process(msg)
            self._pub_rear.publish(out)
            self._lat_rear.append(time.time() - t0)
            self._count_rear.append(time.time())

    def _should_publish(self, which: str) -> bool:
        if self._target_rate_hz is None or self._target_rate_hz <= 0.0:
            return True
        now = self.get_clock().now().nanoseconds / 1e9  # float seconds
        if which == 'front':
            last = self._last_pub_front
            if now - last >= (1.0 / self._target_rate_hz):
                self._last_pub_front = now
                return True
            return False
        else:
            last = self._last_pub_rear
            if now - last >= (1.0 / self._target_rate_hz):
                self._last_pub_rear = now
                return True
            return False

    def _on_budget(self, msg):
        try:
            hz = float(getattr(msg, 'lidar_hz', 0))
            if hz > 0:
                self._target_rate_hz = hz
                self.get_logger().info(f'set target_rate_hz={hz} from budget level={getattr(msg, "level", "")}')
        except Exception:
            pass


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
