import json
import os
import urllib.request
import urllib.error
from typing import Dict, Optional, Tuple
from urllib import parse as _parse

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSReliabilityPolicy

from alpha_utils.srv import SetLidarMode
from alpha_utils.msg import LidarState


def _load_yaml(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


class AiryModeService(Node):
    def __init__(self):
        super().__init__('alpha_airy_mode_service')
        self.declare_parameter('network_config', 'alpha_configs/network.yaml')
        self.declare_parameter('http_enabled', False)
        self.declare_parameter('http_timeout_sec', 1.0)
        self.declare_parameter('http_config_key', 'lidar_airy')
        self.declare_parameter('http_endpoints', '')  # optional direct YAML path, else use config key under alpha_configs/lidar_airy.yaml

        self._states: Dict[str, Tuple[int, bool]] = {
            'front': (0, False),
            'rear': (0, False),
        }

        # Load network and optional HTTP endpoints from config
        net_path = self.get_parameter('network_config').get_parameter_value().string_value
        # Resolve network config robustly if a relative path is provided
        candidates = [
            net_path,
            os.path.join(os.getcwd(), net_path) if net_path and not os.path.isabs(net_path) else net_path,
            os.environ.get('ALPHA_NETWORK_CONFIG', ''),
        ]
        candidates = [c for c in candidates if c]
        found = next((c for c in candidates if os.path.isfile(c)), None)
        self._net = _load_yaml(found or net_path)
        # HTTP endpoint config: either provided via param or looked up from alpha_configs/lidar_airy.yaml under 'http'
        endpoints_param = self.get_parameter('http_endpoints').get_parameter_value().string_value
        if endpoints_param:
            self._http_cfg = _load_yaml(endpoints_param)
        else:
            try:
                http_cfg = _load_yaml('alpha_configs/lidar_airy.yaml').get('http', {})
            except Exception:
                http_cfg = {}
            self._http_cfg = http_cfg

        qos = QoSProfile(
            depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
        )
        self._pub = self.create_publisher(LidarState, '/alpha/lidar/state', qos)
        self._srv = self.create_service(SetLidarMode, '/alpha/ui/cmd/lidar_mode', self._on_set_mode)
        self._timer = self.create_timer(0.5, self._tick)

        self.get_logger().info('AIRY mode service ready. http_enabled=%s' % self.get_parameter('http_enabled').get_parameter_value().bool_value)

    def _ip_for(self, which: str) -> Optional[str]:
        try:
            return self._net['lidar'][which]['ip']
        except Exception:
            return None

    def _endpoint(self, mode: int) -> Optional[Dict]:
        # Expect config structure in alpha_configs/lidar_airy.yaml:
        # http:
        #   endpoints:
        #     run: {method: POST, path: "/api/operation_mode", body: '{"mode":1}', headers: {Content-Type: application/json}}
        #     standby: {method: POST, path: "/api/operation_mode", body: '{"mode":0}', headers: {Content-Type: application/json}}
        ep = (self._http_cfg or {}).get('endpoints', {})
        return ep.get('run' if mode == 1 else 'standby')

    def _http_call(self, ip: str, endpoint: Dict) -> Tuple[bool, str]:
        method = (endpoint.get('method') or 'POST').upper()
        path = endpoint.get('path') or '/'
        body = endpoint.get('body')
        headers = endpoint.get('headers') or {}
        url = f'http://{ip}{path}'
        data = body.encode('utf-8') if isinstance(body, str) else None
        req = urllib.request.Request(url=url, data=data, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        timeout = float(self.get_parameter('http_timeout_sec').get_parameter_value().double_value)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, 'status', 200)
                if 200 <= status < 300:
                    return True, f'HTTP {status}'
                return False, f'HTTP {status}'
        except urllib.error.HTTPError as e:
            return False, f'HTTPError {e.code}: {e.reason}'
        except Exception as e:
            return False, str(e)

    # --- Legacy firmware fallback (observed on AIRY):
    # Reads /setting_data.json, updates 'OpM', then POSTs form fields back to
    # /Parameter_Setting.html (or fallback to /cgi-bin/param_setting.cgi).
    def _http_get_json(self, url: str, timeout: float) -> Tuple[bool, Dict]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = resp.read()
                text = data.decode('utf-8', errors='ignore')
                return True, json.loads(text)
        except Exception:
            return False, {}

    def _http_post_form(self, url: str, fields: Dict, timeout: float, referer: Optional[str] = None) -> Tuple[bool, str]:
        data = _parse.urlencode(fields).encode()
        req = urllib.request.Request(url, data=data)
        # Emulate browser form submission as observed in device UI
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux) ALPHA-Rover')
        if referer:
            req.add_header('Referer', referer)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp.read()
                status = getattr(resp, 'status', 200)
                return (200 <= status < 400), f'HTTP {status}'
        except urllib.error.HTTPError as e:
            # Some firmwares redirect or return 500 even when accepted; treat 2xx/3xx as success
            if 200 <= e.code < 400:
                return True, f'HTTP {e.code}'
            return False, f'HTTPError {e.code}: {e.reason}'
        except Exception as e:
            return False, str(e)

    def _apply_mode_via_legacy_form(self, ip: str, mode: int) -> Tuple[bool, str]:
        timeout = float(self.get_parameter('http_timeout_sec').get_parameter_value().double_value)
        ok, settings = self._http_get_json(f'http://{ip}/setting_data.json', timeout)
        if not ok or not isinstance(settings, dict):
            return False, 'failed to fetch setting_data.json'
        # Update OpM (operation mode) and prepare fields
        settings['OpM'] = str(mode)
        fields = {k: v for k, v in settings.items()}
        fields['save_param'] = 'Save'
        # Warm up UI page once (some firmwares expect a prior GET)
        try:
            urllib.request.urlopen(f'http://{ip}/Parameter_Setting.html', timeout=timeout).read()
        except Exception:
            pass

        ok, msg = self._http_post_form(
            f'http://{ip}/Parameter_Setting.html', fields, timeout, referer=f'http://{ip}/Parameter_Setting.html'
        )
        if not ok:
            # Fallback to CGI handler if HTML path fails
            ok2, msg2 = self._http_post_form(
                f'http://{ip}/cgi-bin/param_setting.cgi', fields, timeout, referer=f'http://{ip}/Parameter_Setting.html'
            )
            if not ok2:
                return False, msg2
        # Verify OpM applied
        ok_s, settings2 = self._http_get_json(f'http://{ip}/setting_data.json', timeout)
        applied = ok_s and str(settings2.get('OpM')) == str(mode)
        return True, ('legacy_form_ok' if applied else 'legacy_form_posted_unverified')

    def _apply_mode(self, which: str, mode: int) -> Tuple[bool, str]:
        ip = self._ip_for(which)
        if not ip:
            return False, f'IP not found for {which}'

        http_enabled = self.get_parameter('http_enabled').get_parameter_value().bool_value
        if not http_enabled:
            # Dry run: update internal state only
            self._states[which] = (mode, mode == 1)
            return True, 'dry-run'

        # Attempt configured endpoint first (if provided)
        endpoint = self._endpoint(mode)
        if endpoint:
            ok, msg = self._http_call(ip, endpoint)
            if ok:
                self._states[which] = (mode, mode == 1)
                return ok, msg
            # Fall through to legacy if endpoint failed

        # Legacy firmware fallback
        ok, msg = self._apply_mode_via_legacy_form(ip, mode)
        if ok:
            self._states[which] = (mode, mode == 1)
        return ok, msg

    def _publish_state(self, which: str):
        ip = self._ip_for(which) or ''
        op_mode, ready = self._states.get(which, (0, False))
        m = LidarState()
        m.id = which
        m.ip = ip
        m.op_mode = int(op_mode)
        m.ready = bool(ready)
        self._pub.publish(m)

    def _tick(self):
        self._publish_state('front')
        self._publish_state('rear')

    def _on_set_mode(self, req: SetLidarMode.Request, resp: SetLidarMode.Response):
        targets = []
        if req.target in ('front', 'rear'):
            targets = [req.target]
        elif req.target == 'both' or not req.target:
            targets = ['front', 'rear']
        else:
            targets = [req.target]

        accepted = True
        messages = []
        states = []
        for t in targets:
            ok, msg = self._apply_mode(t, int(req.op_mode))
            accepted = accepted and ok
            messages.append(f'{t}:{msg}')
            op_mode, ready = self._states.get(t, (0, False))
            st = LidarState()
            st.id = t
            st.ip = self._ip_for(t) or ''
            st.op_mode = int(op_mode)
            st.ready = bool(ready)
            states.append(st)

        resp.accepted = bool(accepted)
        resp.message = '; '.join(messages)
        resp.states = states  # type: ignore[attr-defined]
        return resp


def main(args=None):
    rclpy.init(args=args)
    node = AiryModeService()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
