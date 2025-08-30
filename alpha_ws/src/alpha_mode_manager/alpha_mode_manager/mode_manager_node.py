import rclpy
from rclpy.node import Node
from alpha_utils.srv import ModeSet
from alpha_utils.msg import ModeState


class ModeManager(Node):
    def __init__(self):
        super().__init__('alpha_mode_manager')
        self.state = ModeState()
        self.state.base_mode = 'TELEOP'
        self.state.overlays = []
        self.state.failsafe = False
        self.pub = self.create_publisher(ModeState, '/alpha/mode/state', 10)
        self.srv = self.create_service(ModeSet, '/alpha/mode/set', self.on_set)
        self.timer = self.create_timer(1.0, self._tick)

    def _tick(self):
        self.pub.publish(self.state)

    def on_set(self, req: ModeSet.Request, resp: ModeSet.Response):
        try:
            if req.clear_overlays:
                self.state.overlays = []
            # enable overlays
            for o in req.enable_overlays:
                if o not in self.state.overlays:
                    self.state.overlays.append(o)
            # disable overlays
            if req.disable_overlays:
                self.state.overlays = [o for o in self.state.overlays if o not in req.disable_overlays]
            # set base mode
            if req.target_base_mode:
                self.state.base_mode = req.target_base_mode
                self.state.failsafe = (self.state.base_mode.upper() == 'FAILSAFE')
            resp.accepted = True
            resp.message = 'ok'
            resp.current = self.state
        except Exception as e:
            resp.accepted = False
            resp.message = str(e)
            resp.current = self.state
        return resp


def main():
    rclpy.init()
    node = ModeManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

