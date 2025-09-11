# Architect Update — Rover Bring‑up (2025‑09‑11)

## Executive Summary
- We restored a clean, single bringup on the RPi, fixed Foxglove visibility, and validated the CSI camera pipeline end‑to‑end. Teleop topics are visible in Foxglove, but the base still does not move because there is no active subscriber on `/cmd_vel`.
- Root cause for prior Foxglove issues: discovery server pointed to an unreachable Jetson IP. We switched the RPi to multicast discovery on Domain 42 pending your decision on the final discovery model.

## What’s Working
- Camera (RPi CSI): v4l2_camera + image_proc (debayer, rectify) in a component container; live image in Foxglove.
- Foxglove endpoints: RPi `foxglove_bridge` on 8765 and rosbridge on 9090; Jetson proxies available if needed.
- Teleop topics: `/alpha/cmd_vel` and `/cmd_vel` are present; RPi relay from `/alpha/cmd_vel` → `/cmd_vel` is running.
- Micro‑ROS agent: active; XRCE sessions observed (publishers/readers created), confirming MCU connectivity to agent.

## Current Topology
- Discovery: RPi is now multicast (Domain 42). Jetson currently can run either DS or multicast; decision pending.
- Services (RPi):
  - `alpha-leo-bringup.service` (single owner of camera, rosbridge, firmware bridges)
  - `alpha-foxglove-bridge.service` (8765)
  - `uros-agent.service` (micro‑ROS serial agent)
  - `alpha-teleop-relay.service` (/alpha/cmd_vel → /cmd_vel)
  - `alpha-teleop-beacon.service` (ultra‑low‑rate /alpha/cmd_vel publisher to keep the topic visible)
- Services (Jetson):
  - `alpha-adapter.service` (Leo adapter bridges)
  - `alpha-foxglove-bridge.service` (optional aggregator; currently not required while RPi bridge serves UI)

## Issues / Gaps
1) Base motion: No subscriber on `/cmd_vel` — Teleop commands do not reach the motor controller.
   - Hypotheses: firmware subscribes on a different topic; firmware node not fully initialized; or parameter gate not applied.
2) Discovery consistency: We need a firm call on multicast vs discovery server to remove lingering ambiguity and proxies.
3) Transient duplicate `/firmware*` nodes appear during XRCE reconnects; likely benign once discovery is consistent and services are restarted in a quiet window.

## Options & Recommendation
Discovery model (pick one):
- A) Multicast (recommended for current single‑LAN setup):
  - Keep both Jetson and RPi on Domain 42 with multicast; disable DS everywhere.
  - Run one Foxglove Bridge (prefer Jetson as aggregator if we want a single endpoint; otherwise keep RPi).
- B) Discovery Server on Jetson:
  - Bind DS to a reachable Jetson IP for the RPi (e.g., 192.168.1.10:11811); set both hosts’ `ROS_DISCOVERY_SERVER` to that value.
  - Use Jetson Foxglove Bridge as the single operator endpoint.

Teleop path:
- Confirm the firmware velocity topic (expected `/cmd_vel`). If different, retarget the RPi relay immediately.
- If still `/cmd_vel`, enable/verify the firmware subscriber (via firmware launch/params) and remove relay once confirmed.

## Decision Requests
1) Discovery: Choose A) Multicast on Domain 42 or B) Discovery Server on 192.168.1.10:11811.
2) Foxglove endpoint: Jetson aggregator vs RPi bridge (we can support both; recommend a single, Jetson‑hosted endpoint long‑term).
3) Teleop contract: Confirm base consumes `/cmd_vel` or specify the exact topic to use. We’ll wire relay → final topic within minutes.

## Next Steps (after decisions)
1) Apply discovery choice to both hosts; restart ROS services; remove temporary proxies.
2) Finalize Teleop: retarget relay if needed; validate motion with safe speed limits; remove beacon thereafter.
3) Documentation: freeze the service states and endpoint URLs in NETWORKING.md; add a Foxglove quickstart.
4) Optional: Move Jetson Foxglove Bridge to be the single UI endpoint and decommission Jetson↔RPi WebSocket proxies.

## Appendix — Today’s Changes (RPi)
- Disabled legacy user bringup and standalone rosbridge.
- Added system services:
  - `alpha-teleop-relay.service` (relay /alpha/cmd_vel → /cmd_vel)
  - `alpha-teleop-beacon.service` (ultra‑low‑rate publisher to keep the topic visible)
- Switched bringup to multicast (commented out DS variables; removed DS env from bringup unit).

