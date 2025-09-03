# CODEX Session Handoff — Cabin Overlay Context (Temporary)

Purpose: carry forward the full context needed to resume work locally (non‑SSH) after possible network changes. Do not commit secrets. Safe to share with the next Codex session.

## Snapshot — System & Env (as seen in prior session)
- Host: Jetson (Ubuntu 22.04, ROS 2 Humble installed)
- NICs/IPs:
  - Wi‑Fi `wlP1p1s0`: 192.168.1.175/24
  - Wired `eno1`: 192.168.1.10/24 (platform LAN)
  - Docker bridge: 172.17.0.1/16
- ROS env (Cabin mode):
  - `ROS_DOMAIN_ID=42`
  - `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
  - `ROS_LOCALHOST_ONLY=0`
  - `ROS_SUPER_CLIENT=1`
  - `ROS_DISCOVERY_SERVER=192.168.1.175:11811` (Wi‑Fi IP)
- Discovery server: use Fast DDS discovery server on port 11811 (see “Resume Steps”).

## Repo & Workspace
- Repo: `~/alpha_rover`
- Workspace: `~/alpha_rover/alpha_ws`
- New package scaffolded: `alpha_platforms_leo_rover` (Python, ament)
  - Purpose: Adapter for Leo Rover — normalize topics/TF to `/alpha/...`, provide QoS bridges and minimal TF via `robot_state_publisher`.
  - Files (relative to `alpha_ws/src/alpha_platforms/leo_rover/`):
    - `package.xml` (ament_python export)
    - `setup.py`, `setup.cfg`, `resource/alpha_platforms_leo_rover`
    - `src/alpha_platforms/leo_rover/adapter_node.py`
    - `launch/leorover_adapter.launch.py` (starts `robot_state_publisher` + adapter node, namespaced `alpha`)
    - `config/leo_rover.yaml` (initial `Twist` bridge `/alpha/cmd_vel` → `/cmd_vel`)
    - `urdf/leo_rover_min.urdf.xacro` (minimal links/frames)
    - `tests/test_config.py`

## Current State
- Build: `alpha_platforms_leo_rover` builds cleanly; discoverable by `ros2 pkg list`.
- Mapping config auto‑gen: created `config/leo_rover.yaml` with default Twist bridge. No `Odometry/Image/CameraInfo` sources were detected at the time, so only Twist mapping exists. Post‑gen alias append logic is ready (see below) to publish both camera names when sources exist.
- Networking: `eno1` already set to `192.168.1.10/24`. No netplan changes applied during the session to avoid SSH disruption.

## Resume Steps (Local Terminal, not SSH)
1) ROS env and Discovery (Cabin)
```bash
# Base ROS env
source /opt/ros/humble/setup.bash

# Start Fast DDS Discovery pinned to Wi‑Fi IP (adjust IP if needed)
nohup fastdds discovery --server-id 0 --port 11811 \
  > /tmp/fastdds_discovery.log 2>&1 &
# Export discovery env (Wi‑Fi IP shown above was 192.168.1.175)
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=0
export ROS_SUPER_CLIENT=1
export ROS_DISCOVERY_SERVER="192.168.1.175:11811"
```

2) Build & Source
```bash
cd ~/alpha_rover/alpha_ws
colcon build --symlink-install --packages-select alpha_platforms_leo_rover
source install/setup.bash
```

3) Auto‑Generate Adapter Mapping (with camera aliases)
```bash
# Probe current graph (best effort)
ros2 topic list -t > /tmp/topics.txt || true
ODOM=$(grep -E 'nav_msgs/msg/Odometry' /tmp/topics.txt | awk '{print $1}' | head -n1 || true)
IMG=$(grep -E 'sensor_msgs/msg/Image' /tmp/topics.txt | awk '{print $1}' | head -n1 || true)
CAMINFO=$(grep -E 'sensor_msgs/msg/CameraInfo' /tmp/topics.txt | awk '{print $1}' | head -n1 || true)
CFG="$HOME/alpha_rover/alpha_ws/src/alpha_platforms/leo_rover/config/leo_rover.yaml"
{
  echo "mappings:"
  echo "  - type: geometry_msgs/msg/Twist"
  echo "    in:  /alpha/cmd_vel"
  echo "    out: /cmd_vel"
  echo "    in_qos: RELIABLE"
  echo "    out_qos: RELIABLE"
  if [ -n "${ODOM:-}" ]; then
cat <<EOF2
  - type: nav_msgs/msg/Odometry
    in:  ${ODOM}
    out: /alpha/odom
    in_qos: RELIABLE
    out_qos: RELIABLE
EOF2
  fi
  if [ -n "${IMG:-}" ]; then
cat <<EOF3
  - type: sensor_msgs/msg/Image
    in:  ${IMG}
    out: /alpha/camera/front/image
    in_qos: SENSOR_DATA
    out_qos: SENSOR_DATA
EOF3
  fi
  if [ -n "${CAMINFO:-}" ]; then
cat <<EOF4
  - type: sensor_msgs/msg/CameraInfo
    in:  ${CAMINFO}
    out: /alpha/camera/front/camera_info
    in_qos: RELIABLE
    out_qos: RELIABLE
EOF4
  fi
} > "$CFG"

# Append camera aliases to publish both canonical names
if [ -n "${IMG:-}" ]; then
  cat >> "$CFG" <<EOF
  - type: sensor_msgs/msg/Image
    in:  ${IMG}
    out: /alpha/cam/front/image_color
    in_qos: SENSOR_DATA
    out_qos: SENSOR_DATA
EOF
fi
if [ -n "${CAMINFO:-}" ]; then
  cat >> "$CFG" <<EOF
  - type: sensor_msgs/msg/CameraInfo
    in:  ${CAMINFO}
    out: /alpha/cam/front/camera_info
    in_qos: RELIABLE
    out_qos: RELIABLE
EOF
fi
```

4) Launch Adapter
```bash
ros2 launch alpha_platforms_leo_rover leorover_adapter.launch.py \
  mapping_config:=$HOME/alpha_rover/alpha_ws/src/alpha_platforms/leo_rover/config/leo_rover.yaml
```

5) Sanity Checks
```bash
ros2 topic list | grep '^/alpha/' || true
ros2 topic echo -n1 /alpha/health/adapter_alive || true
# If upstream camera topics exist, verify both names are present:
ros2 topic list | grep -E '^/alpha/(camera/front/image|cam/front/image_color)$' || true
ros2 topic list | grep -E '^/alpha/(camera/front/camera_info|cam/front/camera_info)$' || true
```

## Notes & Guardrails
- Netplan changes: avoid `netplan apply` during remote sessions. Prefer `netplan try --timeout 10` when changing `eno1` config. Current wired IP `192.168.1.10/24` is already set.
- Chrony: configured as a server; safe to `systemctl restart chrony`. Cabin config allows RFC1918 ranges.
- Discovery server: ensure it’s running before launching ROS nodes when `ROS_DISCOVERY_SERVER` is exported.
- DEPLOY env: longer‑term, prefer `/etc/alpha/env/ros.env` per `docs/DEPLOY_ENV.md` instead of `~/.bashrc`.
- Docs hygiene: consider adding `alpha_ws/src/alpha_platforms/leo_rover/AGENTS.md` and re‑run docs tooling.

## Open Items / Next Steps
- Wire the adapter into `alpha_bringup` behind a flag (Leo Rover platform toggle).
- Expand mappings as actual Leo Rover topics come online (odom/camera). Confirm QoS choices.
- Add `AGENTS.md` for the platform adapter and run `scripts/agents_validate.py` and `scripts/agents_index.py`.
- Optionally daemonize Fast DDS discovery as a systemd unit.

---

## Architect Instructions (append below this line)
# Paste authoritative next steps here so future Codex sessions can follow them.

```bash
# JETSON ONE-PROMPT: Platform LAN bring-up + discovery + adapter build/launch
# Mode: interactive with pauses (set ALPHA_AUTO=1 to auto-proceed)
set -Eeuo pipefail

SESSION_ID="jetson-$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="$HOME/alpha_rover/docs/AGENTS"
LOG_FILE="$LOG_DIR/SESSION_JETSON_${SESSION_ID}.md"
mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

log(){ echo "[$(date -Is)] $*" | tee -a "$LOG_FILE"; }
pause(){ 
  if [ "${ALPHA_AUTO:-0}" = "1" ]; then return; fi
  echo ""
  read -r -p ">>> $1  (press ENTER to continue) " _
}

trap 'log "ERROR: line $LINENO failed."; exit 1' ERR

log "=== Jetson session start: $SESSION_ID ==="

# 0) Preflight: env + ROS key hygiene
source /opt/ros/humble/setup.bash || true
if ! apt-get update -y 2>&1 | tee /tmp/apt_update.log | grep -qi 'all packages are up to date'; then
  if grep -qiE 'EXPKEYSIG|NO_PUBKEY' /tmp/apt_update.log; then
    log "Refreshing ROS GPG key (apt complained)."
    sudo rm -f /usr/share/keyrings/ros-archive-keyring.gpg
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
      | sudo tee /usr/share/keyrings/ros-archive-keyring.gpg >/dev/null
    sudo chmod 644 /usr/share/keyrings/ros-archive-keyring.gpg
    sudo apt-get update -y
  fi
fi

# 1) Identify interfaces/IPs (wifi + wired)
WIFI_IF="$(iw dev 2>/dev/null | awk '/Interface/{print $2; exit}')"
if [ -z "${WIFI_IF:-}" ]; then WIFI_IF="$(ip -4 route get 1.1.1.1 | awk '{print $5}')" || true; fi
WIFI_IP="$(ip -4 addr show dev "$WIFI_IF" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)"
WIRED_IF="$(ip -br addr | awk '$1 ~ /^(en|eth)/ && $2 ~ /UP/ {print $1; exit}')"
WIRED_IP="$(ip -4 addr show dev "$WIRED_IF" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)"

log "Detected: WIFI_IF=$WIFI_IF WIFI_IP=${WIFI_IP:-none}  WIRED_IF=$WIRED_IF WIRED_IP=${WIRED_IP:-none}"

# 2) Packages: discovery server, chrony, build tooling
sudo apt-get install -y fastdds-tools chrony avahi-daemon python3-colcon-common-extensions \
  ros-humble-robot-state-publisher ros-humble-xacro ros-humble-tf2-tools python3-yaml jq git

# 3) DDS discovery server as systemd (always-on)
if [ ! -f /etc/systemd/system/fastdds-discovery.service ]; then
  log "Installing fastdds-discovery.service"
  sudo bash -lc 'cat >/etc/systemd/system/fastdds-discovery.service <<EOF
[Unit]
Description=Fast DDS Discovery Server
After=network-online.target
Wants=network-online.target
[Service]
ExecStart=/usr/bin/fastdds discovery --server-id 0 --port 11811
Restart=always
[Install]
wantedBy=multi-user.target
EOF'
  sudo systemctl daemon-reload
  sudo systemctl enable --now fastdds-discovery
else
  sudo systemctl enable --now fastdds-discovery
fi
sudo systemctl --no-pager status fastdds-discovery | sed -n '1,12p' | tee -a "$LOG_FILE"

# 4) Chrony: Jetson as time server (allow Cabin + Platform nets)
sudo bash -lc "cat >/etc/chrony/chrony.conf <<'EOF'
pool ntp.ubuntu.com iburst maxsources 4
allow 192.168.50.0/24
allow 192.168.0.0/16
allow 10.0.0.0/8
allow 172.16.0.0/12
local stratum 10
makestep 1.0 3
rtcsync
EOF"
sudo systemctl restart chrony
chronyc tracking | tee -a "$LOG_FILE" || true

# 5) ROS env (local nodes always use localhost discovery)
grep -q "ROS_DOMAIN_ID" ~/.bashrc || echo "export ROS_DOMAIN_ID=42" >> ~/.bashrc
grep -q "RMW_IMPLEMENTATION" ~/.bashrc || echo "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp" >> ~/.bashrc
grep -q "ROS_LOCALHOST_ONLY" ~/.bashrc || echo "export ROS_LOCALHOST_ONLY=0" >> ~/.bashrc
sed -i '/ROS_DISCOVERY_SERVER=/d' ~/.bashrc
echo "export ROS_DISCOVERY_SERVER=127.0.0.1:11811" >> ~/.bashrc
export ROS_DOMAIN_ID=42 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_LOCALHOST_ONLY=0 ROS_DISCOVERY_SERVER=127.0.0.1:11811
log "ROS env pinned (DOMAIN=42, RMW=FastDDS, discovery=127.0.0.1:11811)"

# 6) **PAUSE-J1** — Confirm RPi will/has moved platform LAN to 192.168.50.1/24
pause "PAUSE-J1: Confirm the RPi bridge br0 is/will be 192.168.50.1/24. Then we will readdress Jetson wired to 192.168.50.10."

# 7) Readdress Jetson wired to 192.168.50.10/24 (safe with local console)
if [ -n "${WIRED_IF:-}" ]; then
  if ! ip -4 addr show dev "$WIRED_IF" | grep -q '192.168.50.10/24'; then
    log "Setting $WIRED_IF to 192.168.50.10/24 via netplan"
    sudo bash -lc "cat >/etc/netplan/70-alpha-wired.yaml <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    ${WIRED_IF}:
      dhcp4: no
      addresses: [192.168.50.10/24]
EOF"
    sudo netplan apply
    sleep 2
  fi
  ip -4 addr show dev "$WIRED_IF" | tee -a "$LOG_FILE"
else
  log "WARNING: No wired interface detected."
fi

# 8) Build adapter (create if missing), auto-generate mapping, add camera aliases if present
REPO_DIR="$HOME/alpha_rover"
WS="$REPO_DIR/alpha_ws"
PKG_DIR="$WS/src/alpha_platforms/leo_rover"
mkdir -p "$WS/src"
if [ ! -d "$REPO_DIR/.git" ]; then git clone https://github.com/alpharover/alpha_rover "$REPO_DIR" || true; else (cd "$REPO_DIR" && git pull --ff-only || true); fi
if [ ! -d "$PKG_DIR" ]; then
  log "Scaffolding adapter package"
  mkdir -p "$PKG_DIR"/{src/alpha_platforms/leo_rover,launch,config,resource,urdf,tests}
  # package.xml
  cat > "$PKG_DIR/package.xml" <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>alpha_platforms_leo_rover</name>
  <version>0.1.0</version>
  <description>ALPHA adapter for Leo Rover v1.7: mappings + TF.</description>
  <maintainer email="alpha@alpharover.org">ALPHA</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_python</buildtool_depend>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>launch</exec_depend>
  <exec_depend>launch_ros</exec_depend>
  <exec_depend>ament_index_python</exec_depend>
  <exec_depend>sensor_msgs</exec_depend>
  <exec_depend>nav_msgs</exec_depend>
  <exec_depend>geometry_msgs</exec_depend>
  <exec_depend>std_msgs</exec_depend>
  <exec_depend>tf2_ros</exec_depend>
  <exec_depend>tf2_msgs</exec_depend>
  <exec_depend>robot_state_publisher</exec_depend>
  <exec_depend>xacro</exec_depend>
  <exec_depend>python3-yaml</exec_depend>
</package>
EOF
  # setup.py
  cat > "$PKG_DIR/setup.py" <<'EOF'
from setuptools import setup, find_packages
from pathlib import Path
package_name = 'alpha_platforms_leo_rover'
def files_in(d): 
    base = Path('share')/package_name/d
    return [(str(base), [str(p) for p in Path(d).glob('**/*') if p.is_file()])]
data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
]
data_files += files_in('launch'); data_files += files_in('config'); data_files += files_in('urdf')
setup(name=package_name, version='0.1.0', packages=find_packages(where='src'), package_dir={'': 'src'},
      data_files=data_files, install_requires=['setuptools','PyYAML'], zip_safe=True,
      maintainer='ALPHA', maintainer_email='alpha@alpharover.org',
      description='ALPHA adapter for Leo Rover v1.7', license='Apache-2.0',
      entry_points={'console_scripts':['leorover_adapter_node=alpha_platforms.leo_rover.adapter_node:main']})
EOF
  printf "%s" "" > "$PKG_DIR/resource/alpha_platforms_leo_rover"
  # adapter
  cat > "$PKG_DIR/src/alpha_platforms/leo_rover/__init__.py" <<'EOF'
# init
EOF
  cat > "$PKG_DIR/src/alpha_platforms/leo_rover/adapter_node.py" <<'EOF'
import importlib, yaml
from copy import deepcopy
from typing import Any, Dict
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Bool
from ament_index_python.packages import get_package_share_directory
from pathlib import Path
def _import_msg(type_str: str):
    mod, _, cls = type_str.rpartition('/')
    mod = mod.replace('/', '.')
    return getattr(importlib.import_module(mod), cls)
def _qos(x: Any) -> QoSProfile:
    if isinstance(x, dict):
        return QoSProfile(depth=int(x.get('depth',5)),
            reliability=(ReliabilityPolicy.RELIABLE if x.get('reliability','').lower()=='reliable' else ReliabilityPolicy.BEST_EFFORT),
            durability=(DurabilityPolicy.TRANSIENT_LOCAL if x.get('durability','').lower()=='transient_local' else DurabilityPolicy.VOLATILE),
            history=HistoryPolicy.KEEP_LAST)
    name=str(x).upper()
    if name in ('SENSOR_DATA','SENSOR_DATA_QOS'):
        return QoSProfile(depth=5,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE,history=HistoryPolicy.KEEP_LAST)
    if name in ('RELIABLE_TRANSIENT_LOCAL','LATCHED'):
        return QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL,history=HistoryPolicy.KEEP_LAST)
    if name in ('RELIABLE',):
        return QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE,history=HistoryPolicy.KEEP_LAST)
    return QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE,history=HistoryPolicy.KEEP_LAST)
class Bridge:
    def __init__(self, node: Node, cfg: Dict[str,Any]):
        self.node=node; self.cfg=cfg
        self.type_str=cfg['type']; self.Msg=_import_msg(self.type_str)
        self.in_topic=cfg['in']; self.out_topic=cfg['out']
        self.in_qos=_qos(cfg.get('in_qos','RELIABLE')); self.out_qos=_qos(cfg.get('out_qos','RELIABLE'))
        self.frame_override=cfg.get('frame_id_override'); self.child_frame_override=cfg.get('child_frame_id_override')
        self.stamp=cfg.get('stamp','passthrough')
        self.pub=node.create_publisher(self.Msg, self.out_topic, self.out_qos)
        def cb(msg):
            out=msg
            try: out=deepcopy(msg)
            except Exception: pass
            h=getattr(out,'header',None)
            if h is not None:
                if self.frame_override: h.frame_id=self.frame_override
                if self.stamp=='now': h.stamp=node.get_clock().now().to_msg()
            if self.child_frame_override and hasattr(out,'child_frame_id'):
                out.child_frame_id=self.child_frame_override
            self.pub.publish(out)
        self.sub=node.create_subscription(self.Msg, self.in_topic, cb, self.in_qos)
        node.get_logger().info(f"[bridge] {self.type_str}: {self.in_topic} -> {self.out_topic}")
class LeoAdapter(Node):
    def __init__(self):
        super().__init__('leorover_adapter')
        from pathlib import Path
        pkg_share=Path(get_package_share_directory('alpha_platforms_leo_rover'))
        cfg_path=Path(self.declare_parameter('mapping_config', str(pkg_share/'config'/'leo_rover.yaml')).value)
        cfg=yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}
        self.bridges=[Bridge(self,m) for m in cfg.get('mappings',[])]
        self.hb=self.create_publisher(Bool,'/alpha/health/adapter_alive',1)
        self.create_timer(1.0, lambda: self.hb.publish(Bool(data=True)))
def main():
    rclpy.init(); n=LeoAdapter(); ex=MultiThreadedExecutor(); ex.add_node(n)
    try: ex.spin()
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()
EOF
  # launch
  cat > "$PKG_DIR/launch/leorover_adapter.launch.py" <<'EOF'
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
def generate_launch_description():
    cfg = DeclareLaunchArgument('mapping_config',
        default_value=PathJoinSubstitution([FindPackageShare('alpha_platforms_leo_rover'),'config','leo_rover.yaml']))
    urdf = PathJoinSubstitution([FindPackageShare('alpha_platforms_leo_rover'),'urdf','leo_rover_min.urdf.xacro'])
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               name='robot_state_publisher', parameters=[{'robot_description': Command(['xacro ', urdf])}], output='screen')
    adapter = Node(package='alpha_platforms_leo_rover', executable='leorover_adapter_node',
                   name='leorover_adapter', output='screen', parameters=[{'mapping_config': LaunchConfiguration('mapping_config')}],
                   namespace='alpha')
    return LaunchDescription([cfg, rsp, adapter])
EOF
  # urdf
  cat > "$PKG_DIR/urdf/leo_rover_min.urdf.xacro" <<'EOF'
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="leo_rover_min">
  <link name="base_link"/>
  <link name="camera_link"/>
  <joint name="camera_joint" type="fixed"><origin xyz="0.15 0 0.18" rpy="0 0 0"/><parent link="base_link"/><child link="camera_link"/></joint>
  <link name="camera_optical_frame"/>
  <joint name="camera_optical_joint" type="fixed"><origin xyz="0 0 0" rpy="-1.57079632679 0 -1.57079632679"/><parent link="camera_link"/><child link="camera_optical_frame"/></joint>
</robot>
EOF
  # cfg
  cat > "$PKG_DIR/config/leo_rover.yaml" <<'EOF'
mappings:
  - type: geometry_msgs/msg/Twist
    in:  /alpha/cmd_vel
    out: /cmd_vel
    in_qos: RELIABLE
    out_qos: RELIABLE
EOF
fi

cd "$WS"; source /opt/ros/humble/setup.bash
colcon build --packages-select alpha_platforms_leo_rover --symlink-install
source install/setup.bash

# 9) Auto-generate mapping from live graph; add camera aliases if found
ros2 topic list -t > /tmp/topics.txt || true
ODOM=$(grep -E 'nav_msgs/msg/Odometry' /tmp/topics.txt | awk '{print $1}' | head -n1 || true)
IMG=$(grep -E 'sensor_msgs/msg/Image'   /tmp/topics.txt | awk '{print $1}' | head -n1 || true)
CAM=$(grep -E 'sensor_msgs/msg/CameraInfo' /tmp/topics.txt | awk '{print $1}' | head -n1 || true)
CFG="$PKG_DIR/config/leo_rover.yaml"
{
  echo "mappings:"
  echo "  - type: geometry_msgs/msg/Twist"; echo "    in:  /alpha/cmd_vel"; echo "    out: /cmd_vel"; echo "    in_qos: RELIABLE"; echo "    out_qos: RELIABLE"
  if [ -n "${ODOM:-}" ]; then
    echo "  - type: nav_msgs/msg/Odometry"; echo "    in:  ${ODOM}"; echo "    out: /alpha/odom"; echo "    in_qos: RELIABLE"; echo "    out_qos: RELIABLE"
  fi
  if [ -n "${IMG:-}" ]; then
    echo "  - type: sensor_msgs/msg/Image"; echo "    in:  ${IMG}"; echo "    out: /alpha/camera/front/image"; echo "    in_qos: SENSOR_DATA"; echo "    out_qos: SENSOR_DATA"
    echo "  - type: sensor_msgs/msg/Image"; echo "    in:  ${IMG}"; echo "    out: /alpha/cam/front/image_color"; echo "    in_qos: SENSOR_DATA"; echo "    out_qos: SENSOR_DATA"
  fi
  if [ -n "${CAM:-}" ]; then
    echo "  - type: sensor_msgs/msg/CameraInfo"; echo "    in:  ${CAM}"; echo "    out: /alpha/camera/front/camera_info"; echo "    in_qos: RELIABLE"; echo "    out_qos: RELIABLE"
    echo "  - type: sensor_msgs/msg/CameraInfo"; echo "    in:  ${CAM}"; echo "    out: /alpha/cam/front/camera_info"; echo "    in_qos: RELIABLE"; echo "    out_qos: RELIABLE"
  fi
} > "$CFG"
log "Generated mapping at $CFG:"
cat "$CFG" | tee -a "$LOG_FILE"

# 10) Launch adapter (background)
pkill -f leorover_adapter || true
ros2 launch alpha_platforms_leo_rover leorover_adapter.launch.py mapping_config:=$CFG >/tmp/adapter.log 2>&1 &
sleep 2

# 11) Sanity
log "=== Sanity checks ==="
ros2 topic list | grep '^/alpha/' | tee -a "$LOG_FILE" || true
ros2 topic echo -n1 /alpha/health/adapter_alive 2>/dev/null | tee -a "$LOG_FILE" || true

log "=== Jetson ready. Wired should be 192.168.50.10. Discovery server active on 127.0.0.1:11811. ==="
echo "NEXT: Tell the RPi to switch discovery/chrony to 192.168.50.10 and validate cross-host ROS."
```
