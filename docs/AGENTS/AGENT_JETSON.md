## 2025-09-03T06:26:35Z — Platform bring-up
- Wired: 192.168.50.10/24
- Discovery: fastdds-discovery active (11811), ROS_DISCOVERY_SERVER=127.0.0.1:11811
- Chrony: serving to /50
- Adapter: alpha_platforms_leo_rover running (tmux: adapter)
- /alpha/: heartbeat present; Odom/Camera bridged if available

## 2025-09-03T07:01:25Z — Platform bring-up (stabilization)
- Discovery: UDP/11811 active; env set (server=127.0.0.1:11811)
- ROS 2 daemon: restarted for CLI discovery
- Adapter: relaunched in tmux (adapter); heartbeat checked
- Cross-host: talker started; RPi echo attempted
## 2025-09-03T07:24:56Z — Discovery + Adapter check
- UDP 11811: 0.0.0.0:*
- tmux: adapter: 1 windows (created Wed Sep  3 02:09:06 2025)
- adapter log: 19:: Node NS=/alpha name=leorover_adapter — heartbeat topic=/alpha/health/adapter_a 21:[leorover_adapter_node-2] [INFO] [1756883348.485443931] [alpha.leorover_adapter] 22:: Loaded config: /home/alpha_orin/alpha_rover/alpha_ws/src/alpha_platforms/leo_r
- nodes: /alpha/leorover_adapter /robot_state_publisher /talker
- topics: /parameter_events /rosout
- node info (/alpha/leorover_adapter): /alpha/leorover_adapter   Subscribers:    Publishers:    Service Servers:    Service Clients:    Action Servers:    Action Clients:
- heartbeat: MISSING — WARNING: topic [/alpha/health/adapter_alive] does not appear to be published yet
- cross-host: failed — pi@192.168.50.1: Permission denied (publickey,password).

## 2025-09-03T09:02:15Z — NAT restore for RPi via Jetson
- Enabled ip_forward=1; added MASQUERADE from 192.168.50.0/24 -> wlP1p1s0; FORWARD rules eno1<->wlP1p1s0
## 2025-09-03T04:13:44-05:00 — Session summary
- Wired: eno1=192.168.50.10/24 (persistent via NetworkManager)
- Discovery: service present; standardized on /usr/bin/fastdds discovery (verify UDP/11811 next session); earlier fast-discovery-server instance confirmed on UDP/11811
- ROS env: persisted in ~/.bashrc (DOMAIN_ID=42, RMW=rmw_fastrtps_cpp, LOCALHOST_ONLY=0, DISCOVERY_SERVER=127.0.0.1:11811); use --no-daemon for CLI due to daemon env quirk
- Adapter: running in tmux (adapter); config loaded; heartbeat topic created; multicast A/B test showed /alpha/health/adapter_alive and echo worked
- Cross-host: server-mode echo pending; multicast echo on RPi initially blocked by PATH but NAT/DNS fixed; will re-run with explicit ROS setup
- NAT: restored Jetson Internet sharing to Pi (ip_forward=1, MASQUERADE 192.168.50.0/24->wlP1p1s0, FORWARD rules); persisted; Pi DNS set via resolvectl (1.1.1.1, 8.8.8.8)
- Next: re-verify UDP/11811 with new unit, relaunch adapter + ros2 daemon under server-mode, run talker→RPi echo with --no-daemon
## 2025-09-03T19:02:47Z — Post-upgrade check + ROS key
- Pi: Ubuntu 22.04.5; kernel 5.15.0-1085-raspi; hostname=leo
- Pi network: br0=192.168.50.1/24; default via 192.168.50.10
- Pi DNS: systemd-resolved active; dnsmasq listening; br0 DNS 1.1.1.1, 8.8.8.8; resolv.conf->127.0.0.1 OK
- Internet: Pi can resolve and ping google.com (IPv4); IPv6 ping not routed (expected)
- APT: ROS 2 repo key refreshed (/usr/share/keyrings/ros-archive-keyring.gpg); apt update clean
- Jetson NAT: ip_forward=1; MASQUERADE 192.168.50.0/24->wlP1p1s0; FORWARD eno1<->wlP1p1s0; persisted via netfilter-persistent
- Notes: No reboot required on Pi after upgrades; next verify ROS graph across hosts
## 2025-09-03T19:15:02Z — Day 2 kickoff preflight
- Hostname: ubuntu
- NICs:
  - lo: 127.0.0.1/8
  - wlP1p1s0: 192.168.1.175/24
  - eno1: 192.168.50.10/24
  - docker0: 172.17.0.1/16
- Routes:
  - default via 192.168.1.254 dev wlP1p1s0 proto dhcp metric 600 
  - 169.254.0.0/16 dev docker0 scope link metric 1000 linkdown 
  - 172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown 
  - 192.168.1.0/24 dev wlP1p1s0 proto kernel scope link src 192.168.1.175 metric 600 
  - 192.168.50.0/24 dev eno1 proto kernel scope link src 192.168.50.10 metric 100 

## 2025-09-03T19:24:35Z — Day 2 bring-up (authority node)
- Discovery: Fast DDS server via systemd on UDP/11811 (fast-discovery-server), LD paths set in unit; listening on 0.0.0.0:11811.
- Env: CLI deterministic — ROS2CLI_NO_DAEMON=1; server-mode env exported (ROS_DISCOVERY_SERVER=127.0.0.1:11811, ROS_DOMAIN_ID=42, RMW=rmw_fastrtps_cpp, LOCALHOST_ONLY=0) and persisted in ~/.bashrc.
- Adapter: launched in tmux session `adapter`; heartbeat topic is /alpha/health/adapter_alive (visible in multicast A/B); bridges configured from leo_rover.yaml.
- A/B: Multicast shows full graph; server-mode works for local pub/sub (talker<->listener). `ros2 topic list --no-daemon` may not enumerate under server-mode (CLI quirk), but data flow is OK.
- Cross-host: smoke passed using multicast (Jetson talker → Pi echo); server-mode cross-host pending CLI introspection alignment on Pi.
- Next: keep server enabled; retest Pi echo with server-mode after ensuring SSH key auth and matching server env; then exercise talker/echo both directions.
## Day-3 (server-mode smoke)
2025-09-03T16:04:06-05:00
- UDP/11811:   UNCONN 0      0                          0.0.0.0:11811      0.0.0.0:*                                              
- Heartbeat one-shot: attempted
- Remote /chatter echo from RPi: attempted
- Camera bridge: probed (if present)

## 2025-09-03T21:24:00Z — Heartbeat proven (server-mode)
- Invariants enforced: `ROS_DOMAIN_ID=42`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_LOCALHOST_ONLY=0`, `ROS2CLI_NO_DAEMON=1`.
- Discovery server kept as‑is on UDP/11811 (`ROS_DISCOVERY_SERVER=127.0.0.1:11811` on Jetson; Pi uses `192.168.50.10:11811`).
- Adapter env: tmux `adapter` inherits env; `/alpha/leorover_adapter` running.
- Local proof: `ros2 topic echo --once /alpha/health/adapter_alive std_msgs/msg/Bool` → `data: true`.
- Cross‑host proof: announced 15–45s “HEARTBEAT WINDOW” intervals; Pi echoed once using:
  `ROS_DOMAIN_ID=42 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_LOCALHOST_ONLY=0 ROS2CLI_NO_DAEMON=1 ROS_DISCOVERY_SERVER=192.168.50.10:11811 ros2 topic echo --once /alpha/health/adapter_alive std_msgs/msg/Bool`.
- Result: pass. No binary swaps; explicit type on echo used for reliability.

## 2025-09-03T22:10:00Z — Coordinator + Clean Sweep
- Control topics (RELIABLE + TRANSIENT_LOCAL): `/alpha/test/announce`, `/alpha/test/ready`, `/alpha/test/go`, `/alpha/test/done` (std_msgs/String, JSON: id/name/status).
- Coordinator: `alpha_rover/scripts/jetson_coordinator.py` announces → waits for ready → sends go → runs producer → publishes done.
- Dupes cleanup: killed stray demo `talker`s; renamed adapter’s `robot_state_publisher` to `robot_state_publisher_jetson` in `alpha_platforms_leo_rover/launch/leorover_adapter.launch.py` to avoid cross‑host duplicate names.
- smoke_chatter: producer `demo_nodes_cpp/talker` remapped to `/alpha/test/chatter`, node name `talker_jetson`; Pi captured and reported done=pass.
- heartbeat: verified local echo (`std_msgs/msg/Bool`) and Pi reported done=pass.
- Node list shows no duplicate‑name warnings on Jetson.

## 2025-09-04T00:00:00Z — SCO (single-controller) tests
- smoke_chatter: pass — armed Pi via SSH on `/alpha/test/chatter` (std_msgs/msg/String, RELIABLE), started `talker_jetson` for ~12 s; Pi printed first message and `::RPI_READY::`.
- heartbeat: pass — armed Pi via SSH on `/alpha/health/adapter_alive` (std_msgs/msg/Bool, BEST_EFFORT); adapter under Domain 42/server-mode; Pi printed `data: true` and `::RPI_READY::`.

## 2025-09-04T05:20:00Z — Camera bridge + services + compile
- Camera bridge: Added explicit mappings in `alpha_platforms_leo_rover/config/leo_rover.yaml`:
  - `/camera/image_raw` → `/alpha/camera/front/image` (sensor_msgs/Image, SENSOR_DATA/BEST_EFFORT).
  - `/camera/camera_info` → `/alpha/camera/front/camera_info` (sensor_msgs/CameraInfo, RELIABLE).
- Validation: Pi remote listeners (BEST_EFFORT for Image, RELIABLE for CameraInfo) each captured one message via the `/alpha/camera/front/*` aliases.
- Services: Installed `alpha-adapter.service` (systemd) with env file `/etc/alpha/ros.env` (Domain 42 + discovery server). Unit starts after `fastdds-discovery.service` and `network-online` and publishes heartbeat.
- Compile: Built `alpha_platforms_leo_rover` on Jetson from workspace to validate host build path (no Pi-only packages to rescue; NFS shows same set on Pi/Jetson).

## 2025-09-04T05:25:00Z — Session wrap-up (status)
- Invariants: Domain 42; Fast DDS discovery server at `127.0.0.1:11811` (Jetson) and `192.168.50.10:11811` (Pi); `ROS2CLI_NO_DAEMON=1` for checks.
- Services: `fastdds-discovery.service` enabled; `alpha-adapter.service` enabled (Restart=on-failure). Heartbeat `/alpha/health/adapter_alive` one‑shot echo works.
- Camera bridge: `/camera/image_raw` → `/alpha/camera/front/image` (BEST_EFFORT); `/camera/camera_info` → `/alpha/camera/front/camera_info` (RELIABLE). Pi confirmed one Image and one CameraInfo via aliases.
- Handshake tests: Coordinator + Pi remote listener pattern active (subscribe first → publish). `smoke_chatter` and `heartbeat` pass.
- NFSv4: Pi export mounted at `/mnt/pi/alpha_rover` (rw). UID/GID aligned (1000:1000). Create/delete verified cross‑host.
- Backups: Snapshot seeded under `~/alpha_rover/backups/pi-YYYYMMDD/` with SHA256 manifest; nightly sync timer `pi-backup.timer` armed (03:15).
- Compile: Jetson builds adapter package from workspace; ready to extend to rescued packages if needed.
