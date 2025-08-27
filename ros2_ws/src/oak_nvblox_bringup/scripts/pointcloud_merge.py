#!/usr/bin/env python3

import math
from typing import List, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformListener
from rclpy.duration import Duration
from rclpy.time import Time


def transform_points(points: np.ndarray, tf: TransformStamped) -> np.ndarray:
    t = tf.transform.translation
    q = tf.transform.rotation
    # Convert quaternion to rotation matrix
    x, y, z, w = q.x, q.y, q.z, q.w
    # Rotation matrix from quaternion
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float32)
    t_vec = np.array([t.x, t.y, t.z], dtype=np.float32)
    return (R @ points.T).T + t_vec


class PointCloudMerge(Node):
    def __init__(self):
        super().__init__('pointcloud_merge')

        self.declare_parameter('front_topic', '/airy_200/rslidar_points')
        self.declare_parameter('rear_topic', '/airy_201/rslidar_points')
        self.declare_parameter('output_topic', '/merged/lidar_points')
        self.declare_parameter('target_frame', 'base_link')
        self.declare_parameter('publish_rate_hz', 20.0)

        self.front_topic = self.get_parameter('front_topic').get_parameter_value().string_value
        self.rear_topic = self.get_parameter('rear_topic').get_parameter_value().string_value
        self.output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.target_frame = self.get_parameter('target_frame').get_parameter_value().string_value
        self.publish_dt = 1.0 / float(self.get_parameter('publish_rate_hz').get_parameter_value().double_value)

        # Use SENSOR_DATA-like QoS on both ends for compatibility
        qos_sub = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        qos_pub = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.front_msg: Optional[PointCloud2] = None
        self.rear_msg: Optional[PointCloud2] = None

        self.front_sub = self.create_subscription(PointCloud2, self.front_topic, self._front_cb, qos_sub)
        self.rear_sub = self.create_subscription(PointCloud2, self.rear_topic, self._rear_cb, qos_sub)
        self.pub = self.create_publisher(PointCloud2, self.output_topic, qos_pub)

        self.timer = self.create_timer(self.publish_dt, self._on_timer)
        self.get_logger().info(
            f"Merging pointclouds: front={self.front_topic}, rear={self.rear_topic} -> {self.output_topic} in {self.target_frame}"
        )

    def _front_cb(self, msg: PointCloud2):
        self.front_msg = msg

    def _rear_cb(self, msg: PointCloud2):
        self.rear_msg = msg

    def _transform_cloud(self, msg: PointCloud2) -> Optional[np.ndarray]:
        try:
            tf = self.tf_buffer.lookup_transform(
                self.target_frame,
                msg.header.frame_id,
                Time.from_msg(msg.header.stamp),
                timeout=Duration(seconds=0.05),
            )
        except Exception as e:
            self.get_logger().debug(f"TF lookup failed {msg.header.frame_id}->{self.target_frame}: {e}")
            return None
        # Extract XYZ points
        pts = np.array(list(point_cloud2.read_points(msg, field_names=('x', 'y', 'z'), skip_nans=True)), dtype=np.float32)
        if pts.size == 0:
            return np.zeros((0, 3), dtype=np.float32)
        return transform_points(pts, tf)

    def _on_timer(self):
        clouds: List[np.ndarray] = []
        latest_stamp = None

        if self.front_msg is not None:
            arr = self._transform_cloud(self.front_msg)
            if arr is not None:
                clouds.append(arr)
                latest_stamp = self.front_msg.header.stamp

        if self.rear_msg is not None:
            arr = self._transform_cloud(self.rear_msg)
            if arr is not None:
                clouds.append(arr)
                latest_stamp = self.rear_msg.header.stamp if latest_stamp is None else latest_stamp

        if not clouds:
            return

        merged = np.vstack(clouds) if len(clouds) > 1 else clouds[0]
        # Build PointCloud2 with x,y,z only (float32)
        header = PointCloud2().header
        header.frame_id = self.target_frame
        header.stamp = latest_stamp if latest_stamp is not None else self.get_clock().now().to_msg()
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        pc2 = point_cloud2.create_cloud(header, fields, merged.tolist())
        self.pub.publish(pc2)


def main():
    rclpy.init()
    node = PointCloudMerge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
