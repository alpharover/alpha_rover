import os
import glob
import signal
import yaml
import rclpy
from rclpy.node import Node
from alpha_utils.srv import GetConfig


def _read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


class ConfigManager(Node):
    def __init__(self):
        super().__init__('alpha_config_manager')
        self.declare_parameter('config_dir', '')
        self.config_dir = self._resolve_config_dir()
        self.get_logger().info(f"Config directory: {self.config_dir}")
        self._cache = {}
        self._load_all()
        self._srv = self.create_service(GetConfig, '/alpha/config/get', self._on_get_config)

        # Optional: support SIGHUP to reload in dev
        signal.signal(signal.SIGHUP, self._on_sighup)

    def _resolve_config_dir(self) -> str:
        # Priority: param > env > default ./alpha_configs
        param = self.get_parameter('config_dir').get_parameter_value().string_value
        if param:
            return os.path.abspath(param)
        env = os.environ.get('ALPHA_CONFIG_DIR')
        if env:
            return os.path.abspath(env)
        # Default: look for alpha_configs relative to cwd
        default = os.path.abspath(os.path.join(os.getcwd(), 'alpha_configs'))
        return default

    def _load_all(self):
        self._cache.clear()
        if not os.path.isdir(self.config_dir):
            self.get_logger().warn(f"Config dir not found: {self.config_dir}")
            return
        for path in glob.glob(os.path.join(self.config_dir, '*.yaml')):
            key = os.path.splitext(os.path.basename(path))[0]
            try:
                # Validate basic YAML syntax
                yaml.safe_load(_read_file(path))
                self._cache[key] = path
                self.get_logger().info(f"Loaded config: {key} -> {path}")
            except Exception as e:
                self.get_logger().error(f"Failed to parse {path}: {e}")

    def _on_get_config(self, request: GetConfig.Request, response: GetConfig.Response):
        key = request.key.strip()
        if not key:
            response.found = False
            response.yaml = ''
            response.message = 'key is empty'
            return response
        path = self._cache.get(key)
        if not path:
            response.found = False
            response.yaml = ''
            response.message = f'key not found: {key}'
            return response
        try:
            content = _read_file(path)
            # Ensure it’s valid YAML before serving
            yaml.safe_load(content)
            response.found = True
            response.yaml = content
            response.message = 'ok'
        except Exception as e:
            response.found = False
            response.yaml = ''
            response.message = f'error reading {key}: {e}'
        return response

    def _on_sighup(self, signum, frame):
        self.get_logger().info('SIGHUP received; reloading configs')
        self._load_all()


def main(args=None):
    rclpy.init(args=args)
    node = ConfigManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

