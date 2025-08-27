#!/usr/bin/env python3
import argparse
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import PointCloud2, PointField


def str2bool(v: str) -> bool:
    return v.lower() in ('1', 'true', 't', 'yes', 'y', 'on')


def parse_angle_csv(path: str) -> Optional[list[float]]:
    try:
        import csv
        angles = []
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Accept either 'Vertical_Angle_deg' or 'vertical_angle_deg'
                key = 'Vertical_Angle_deg' if 'Vertical_Angle_deg' in row else (
                    'vertical_angle_deg' if 'vertical_angle_deg' in row else None)
                if key is None:
                    continue
                try:
                    angles.append(float(row[key]))
                except Exception:
                    continue
        return angles if angles else None
    except Exception:
        return None


class PcRepack(Node):
    def __init__(self, input_topic: str, output_topic: str, flatten: bool, out_frame: Optional[str], angle_csv: Optional[str]):
        super().__init__('pc_repack')
        self.flatten = flatten
        self.out_frame = out_frame
        self.row_reorder: Optional[list[int]] = None
        if angle_csv:
            angles = parse_angle_csv(angle_csv)
            if angles:
                # Build reorder indices by sorting by angle ascending (low→high)
                # Incoming row index i is assumed to correspond to channel i (0-based)
                # If CSV has 1-based channels, the relative order is preserved by sorting angles only
                self.row_reorder = sorted(range(len(angles)), key=lambda i: angles[i])
                self.get_logger().info(f'Loaded {len(angles)} vertical angles; applying row reorder')
            else:
                self.get_logger().warn('Failed to parse angle CSV; proceeding without reorder')

        self.sub = self.create_subscription(
            PointCloud2, input_topic, self.cb, qos_profile_sensor_data)
        self.pub = self.create_publisher(PointCloud2, output_topic, qos_profile_sensor_data)

        self.get_logger().info(
            f'Repacking {input_topic} -> {output_topic}; flatten={self.flatten}; out_frame={self.out_frame or "(preserve)"}; reorder={(angle_csv or "")}')

    def cb(self, msg: PointCloud2):
        # Prepare new message, optionally flatten to height=1
        out = PointCloud2()
        out.header = msg.header
        if self.out_frame:
            out.header.frame_id = self.out_frame

        # Preserve incoming fields and layout exactly to avoid schema mismatch
        out.fields = list(msg.fields)
        out.is_bigendian = msg.is_bigendian
        out.point_step = msg.point_step

        do_reorder = self.row_reorder is not None and msg.height > 1 and len(self.row_reorder) == msg.height

        if self.flatten and msg.height > 1 and not do_reorder:
            out.height = 1
            out.width = msg.width * msg.height
            out.row_step = out.width * out.point_step
            out.is_dense = msg.is_dense
            # Data is already contiguous in PointCloud2; a copy is sufficient
            out.data = bytes(msg.data)
        elif do_reorder and not self.flatten:
            # Reorder rows according to vertical angle CSV
            try:
                row_step = msg.row_step
                buf = bytearray(row_step * msg.height)
                for new_row, src_row in enumerate(self.row_reorder):
                    start_src = src_row * row_step
                    end_src = start_src + row_step
                    start_dst = new_row * row_step
                    buf[start_dst:start_dst + row_step] = msg.data[start_src:end_src]
                out.height = msg.height
                out.width = msg.width
                out.row_step = msg.row_step
                out.is_dense = msg.is_dense
                out.data = bytes(buf)
            except Exception as e:
                self.get_logger().warn(f'Row reorder failed ({e}); forwarding original data')
                out.height = msg.height
                out.width = msg.width
                out.row_step = msg.row_step
                out.is_dense = msg.is_dense
                out.data = bytes(msg.data)
        else:
            out.height = msg.height
            out.width = msg.width
            out.row_step = msg.row_step
            out.is_dense = msg.is_dense
            out.data = bytes(msg.data)

        self.pub.publish(out)


def main(argv=None):
    rclpy.init(args=argv)

    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--flatten', type=str2bool, default=False, help='Flatten to height=1, width=N (true/false)')
    parser.add_argument('--out-frame', default='', help='Override frame_id in output')
    parser.add_argument('--angle-csv', default='', help='CSV with per-channel vertical angles to reorder rows')
    args = parser.parse_args()

    node = PcRepack(args.input, args.output, args.flatten, args.out_frame or None, args.angle_csv or None)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
