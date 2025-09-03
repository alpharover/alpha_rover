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

