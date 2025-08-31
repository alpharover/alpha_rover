# ROS Environment Domains (Dev/Field/Sim)

Use a small env file sourced by systemd units and shell wrappers to prevent cross‑talk between machines in shared networks.

- Dev domain: `ROS_DOMAIN_ID=42`
- Field domain: `ROS_DOMAIN_ID=43`
- Sim domain: `ROS_DOMAIN_ID=99`
- Optional (dev‑only) localhost isolation: `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`

Recommended location: `/etc/alpha/env/ros.env` (readable by service users).

Example `/etc/alpha/env/ros.env`:

```
ROS_DOMAIN_ID=42
# Dev-only override; do not set on field/sim units
# ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

Service unit snippet (systemd):

```
[Service]
EnvironmentFile=/etc/alpha/env/ros.env
execStart=/usr/bin/bash -lc 'source /opt/ros/humble/setup.bash && exec /usr/bin/ros2 ...'
```

Keep these values out of global dotfiles to avoid confusion in multi‑user environments.
