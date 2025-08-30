import math
import struct
from pathlib import Path

import rclpy
from sensor_msgs.msg import PointCloud2, PointField

from alpha_lidar_airy.reorder_node import AiryReorderNode, _read_angle_table


def make_cloud(height: int, width: int, rows_values):
    # rows_values: list of tuples per row: [(x,y,z), (x,y,z), ...] length width
    assert len(rows_values) == height
    fields = [
        PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg = PointCloud2()
    msg.height = height
    msg.width = width
    msg.fields = fields
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = msg.point_step * width
    msg.is_dense = False
    data = bytearray(msg.row_step * height)
    mv = memoryview(data)
    for r in range(height):
        for c in range(width):
            x, y, z = rows_values[r][c]
            off = r * msg.row_step + c * msg.point_step
            struct.pack_into('<f', mv, off + 0, float(x))
            struct.pack_into('<f', mv, off + 4, float(y))
            struct.pack_into('<f', mv, off + 8, float(z))
    msg.data = bytes(data)
    return msg


def read_row_x_values(msg: PointCloud2):
    xs = []
    mv = memoryview(msg.data)
    for r in range(msg.height):
        row = []
        for c in range(msg.width):
            off = r * msg.row_step + c * msg.point_step
            x = struct.unpack_from('<f', mv, off + 0)[0]
            row.append(x)
        xs.append(row)
    return xs


def test_angle_table_parser_header_csv(tmp_path: Path):
    csv = tmp_path / 'angles.csv'
    csv.write_text('Channel,Vertical_Angle_deg\n1,10\n2,0\n3,20\n')
    vals = _read_angle_table(str(csv))
    assert vals == [10.0, 0.0, 20.0]


def test_reorder_and_range_gate(tmp_path: Path):
    # Prepare CSV and YAML config
    csv = tmp_path / 'angles.csv'
    # Angles such that order becomes [1,0,2]
    csv.write_text('Channel,Vertical_Angle_deg\n1,10\n2,0\n3,20\n')
    yaml = tmp_path / 'lidar_airy.yaml'
    yaml.write_text(
        'vertical_angle_table_path: angles.csv\n'
        'reorder_enabled: true\n'
        'log_table_hash: false\n'
        'expected_dims: { height: 3, width: 2 }\n'
        'fov: { min_angle_below_zero_elevation_rad: -0.001, max_angle_above_zero_elevation_rad: 1.5707963 }\n'
        'range_m: { min: 0.10, max: 1.0 }\n'
    )

    # Initialize node with param override
    rclpy.init(args=[
        '--ros-args',
        '-p', f'config:={str(yaml)}',
        '-p', 'strict:=true',
        '-p', 'input_front_topic:=/ignore',
        '-p', 'input_rear_topic:=/ignore',
    ])
    try:
        node = AiryReorderNode()
        # Build a 3x2 cloud. Fill x values as row markers: row0->100, row1->200, row2->300
        # Set second column to distance 2.0 (>1.0) to trigger NaN gating.
        rows = [
            [(100.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
            [(200.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
            [(300.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
        ]
        msg = make_cloud(3, 2, rows)
        out = node._process(msg)
        xs = read_row_x_values(out)
        # After reorder by [1,0,2]: expect row order x markers [[200, NaN], [100, NaN], [300, NaN]]
        assert math.isclose(xs[0][0], 200.0)
        assert math.isnan(xs[0][1])
        assert math.isclose(xs[1][0], 100.0)
        assert math.isnan(xs[1][1])
        assert math.isclose(xs[2][0], 300.0)
        assert math.isnan(xs[2][1])
    finally:
        rclpy.shutdown()

