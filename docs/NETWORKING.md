# Networking Modes

## Platform Mode (default)
- Subnet: 192.168.50.0/24
- Jetson wired: 192.168.50.10 — runs Fast DDS discovery (11811) and chrony server.
- RPi bridge: 192.168.50.1 — AP typically off in Cabin, on for field ops.
- ROS: DOMAIN=42, RMW=Fast DDS, discovery=192.168.50.10:11811.
- Time: Clients sync to Jetson via chrony.

## Cabin Mode (temporary)
- Devices may share external Wi‑Fi. If needed, point discovery to Jetson’s Wi‑Fi IP.
- Keep rover AP off to avoid radio conflicts.

## Optional Internet Path
- NAT Wi‑Fi → wired on Jetson so RPi/clients have Internet during bring‑up.
