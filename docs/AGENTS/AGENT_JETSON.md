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
