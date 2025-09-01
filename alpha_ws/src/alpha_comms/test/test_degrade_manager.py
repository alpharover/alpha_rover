import time

import pytest
import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus

from alpha_comms.degrade_manager_node import DegradeManager


def make_breach_array():
    arr = DiagnosticArray()
    st = DiagnosticStatus()
    st.level = DiagnosticStatus.WARN
    arr.status = [st]
    return arr


@pytest.mark.unit
def test_escalate_and_deescalate():
    rclpy.init()
    try:
        node = DegradeManager()
        # Start at L0
        assert node.current_level == 'L0'
        # Breach -> escalate to L1
        node.on_slo(make_breach_array())
        assert node.current_level == 'L1'
        # Next breach -> L2
        node.on_slo(make_breach_array())
        assert node.current_level == 'L2'
        # De-escalate after good period
        node.current_level = 'L2'
        node.last_breach_time = node.get_clock().now().seconds_nanoseconds()[0] - 10
        node._tick()
        assert node.current_level == 'L1'
    finally:
        rclpy.shutdown()
