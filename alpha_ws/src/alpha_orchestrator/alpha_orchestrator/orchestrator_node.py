import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String
from std_srvs.srv import Trigger
from alpha_utils.srv import OrchestratorCommand, ModeSet
from alpha_utils.msg import Event, Health, DomainHealth


class Orchestrator(Node):
    def __init__(self):
        super().__init__('alpha_orchestrator')
        # Parameters
        self.declare_parameter('config_failure_domains', 'alpha_configs/failure_domains.yaml')
        self.declare_parameter('dry_run', True)
        self.declare_parameter('compose_mapping', 'deploy/compose.mapping.yaml')
        self.declare_parameter('compose_vslam', 'deploy/compose.vslam.yaml')
        self.declare_parameter('images_lock', 'deploy/IMAGES.lock')

        # Load failure domains config
        cfg_path = self.get_parameter('config_failure_domains').get_parameter_value().string_value
        self.fd_cfg = self._load_yaml(cfg_path)

        # Interfaces
        self.srv = self.create_service(OrchestratorCommand, '/alpha/orchestrator/cmd', self.on_cmd)
        self.events_pub = self.create_publisher(Event, '/alpha/events', 10)
        self.health_sub = self.create_subscription(Health, '/alpha/health', self.on_health, QoSProfile(depth=10))
        self.health_pub = self.create_publisher(Health, '/alpha/health', 10)
        self.sub_degrade = self.create_subscription(String, '/alpha/comms/degrade_level', self.on_degrade, 10)
        self.cli_modeset = self.create_client(ModeSet, '/alpha/mode/set')
        self.cli_e_stop = self.create_client(Trigger, '/alpha/motion/e_stop')
        self.cli_resume = self.create_client(Trigger, '/alpha/motion/resume')
        self._last_health = {}

    def publish_event(self, etype: str, details: str):
        ev = Event()
        ev.stamp = self.get_clock().now().to_msg()  # type: ignore
        ev.type = etype
        ev.details = details
        self.events_pub.publish(ev)

    def _load_yaml(self, path: str) -> dict:
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.get_logger().warn(f'Failed to read failure domains config {path}: {e}; using empty config')
            return {}

    def on_health(self, msg: Health):
        # Compare domain statuses and emit events on change
        changed = []
        for d in msg.domains:
            prev = self._last_health.get(d.domain)
            if prev is None or prev != d.status:
                changed.append((d.domain, d.status))
            self._last_health[d.domain] = d.status
        for dom, status in changed:
            self.publish_event('DOMAIN_HEALTH', f'{dom}:{status}')

    def on_degrade(self, msg: String):
        lvl = (msg.data or '').strip().upper()
        status = DomainHealth.OK
        if lvl in ('L1', 'L2'):
            status = DomainHealth.DEGRADED
        elif lvl == 'L3':
            status = DomainHealth.FAILED
        dh = DomainHealth()
        dh.domain = 'comms'
        dh.status = status
        dh.reason = f'degrade:{lvl}'
        self._last_health['comms'] = status
        h = Health()
        h.domains = []
        for k, v in self._last_health.items():
            d = DomainHealth()
            d.domain = k
            d.status = v
            d.reason = ''
            h.domains.append(d)
        self.health_pub.publish(h)
        self.publish_event('DOMAIN_HEALTH', f'comms:{status}')

    def on_cmd(self, req: OrchestratorCommand.Request, resp: OrchestratorCommand.Response):
        action = (req.action or '').strip().lower()
        self.get_logger().info(f"orchestrator cmd: {action}")
        self.publish_event('ORCH_CMD', action)
        try:
            if action in ('e_stop', 'e-stop', 'estop'):
                ok = self._call_trigger(self.cli_e_stop)
                self.publish_event('E_STOP', 'requested')
                resp.accepted = ok
                resp.message = 'e_stop executed' if ok else 'e_stop unavailable'
                return resp
            elif action in ('resume', 'clear_e_stop', 'clear'):
                ok = self._call_trigger(self.cli_resume)
                self.publish_event('RESUME', 'requested')
                resp.accepted = ok
                resp.message = 'resume executed' if ok else 'resume unavailable'
                return resp
            elif action in ('recover_perception', 'recover-perception'):
                # Lookup recovery actions in config
                actions = self._lookup_recovery('perception', 'vslam_lost')
                self._execute_actions(actions)
                resp.accepted = True
                resp.message = 'recovery actions executed'
                return resp
            elif action in ('start_mapping', 'stop_mapping', 'start_vslam', 'stop_vslam'):
                ok = self._compose_action(action)
                resp.accepted = ok
                resp.message = f'{action} {"ok" if ok else "failed"}'
                return resp
            else:
                resp.accepted = False
                resp.message = f'unknown action: {action}'
                return resp
        except Exception as e:
            resp.accepted = False
            resp.message = str(e)
            return resp

    def _lookup_recovery(self, domain: str, key: str):
        try:
            return self.fd_cfg.get(domain, {}).get('recovery', {}).get(key, []) or []
        except Exception:
            return []

    def _execute_actions(self, actions):
        # Each action item is a mapping, e.g., {'switch': 'wheel_odom_only'} or {'limit_speed': 0.3} or {'mode': 'failsafe'}
        for act in actions:
            if not isinstance(act, dict):
                continue
            for k, v in act.items():
                if k == 'mode':
                    mode = str(v).upper()
                    self._set_mode(mode)
                elif k == 'limit_speed':
                    self.publish_event('RECOVERY_ACTION', f'limit_speed:{v}')
                elif k == 'switch':
                    self.publish_event('RECOVERY_ACTION', f'switch:{v}')
                else:
                    self.publish_event('RECOVERY_ACTION', f'{k}:{v}')

    def _set_mode(self, target_base_mode: str):
        dry_run = self.get_parameter('dry_run').get_parameter_value().bool_value
        if dry_run:
            self.get_logger().info(f'DRY-RUN: set base mode to {target_base_mode}')
            self.publish_event('MODE_SET', f'{target_base_mode}')
            return True
        if not self.cli_modeset.wait_for_service(timeout_sec=2.0):
            self.publish_event('ERROR', 'mode_set service unavailable')
            return False
        req = ModeSet.Request()
        req.target_base_mode = target_base_mode
        req.clear_overlays = True
        fut = self.cli_modeset.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=2.0)
        ok = bool(fut.done() and getattr(fut.result(), 'accepted', False))
        self.publish_event('MODE_SET', f'{target_base_mode}:{ok}')
        return ok

    def _call_trigger(self, client) -> bool:
        try:
            if not client.wait_for_service(timeout_sec=1.0):
                return False
            fut = client.call_async(Trigger.Request())
            rclpy.spin_until_future_complete(self, fut, timeout_sec=2.0)
            return bool(fut.done() and getattr(fut.result(), 'success', False))
        except Exception:
            return False

    def _compose_action(self, action: str) -> bool:
        import subprocess
        dry_run = self.get_parameter('dry_run').get_parameter_value().bool_value
        compose_mapping = self.get_parameter('compose_mapping').get_parameter_value().string_value
        compose_vslam = self.get_parameter('compose_vslam').get_parameter_value().string_value
        images_lock = self.get_parameter('images_lock').get_parameter_value().string_value
        try:
            if action in ('start_mapping', 'stop_mapping'):
                compose_file = compose_mapping
            else:
                compose_file = compose_vslam
            if 'start' in action:
                cmd = ['docker', 'compose', '-f', compose_file, '--env-file', images_lock, 'up', '-d']
            else:
                cmd = ['docker', 'compose', '-f', compose_file, '--env-file', images_lock, 'stop']
            self.publish_event('COMPOSE', ' '.join(cmd))
            if dry_run:
                self.get_logger().info('DRY-RUN: ' + ' '.join(cmd))
                return True
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            ok = proc.returncode == 0
            if not ok:
                self.get_logger().warn(f'compose failed: rc={proc.returncode} stderr={proc.stderr}')
            return ok
        except Exception as e:
            self.get_logger().warn(f'compose exception: {e}')
            return False


def main():
    rclpy.init()
    node = Orchestrator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
