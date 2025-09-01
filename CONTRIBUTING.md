# Contributing to ALPHA Rover

First: thank you. This project controls real hardware, so contributions must keep **safety**, **determinism**, and **observability** front and center.

## Code of Conduct
Participation is governed by our [Code of Conduct](./CODE_OF_CONDUCT.md). By contributing, you agree to follow it.

## How to contribute
- **Discuss first.** Open an issue describing the problem and proposed change.
- **Small PRs.** Keep changes focused; large PRs are hard to review safely.
- **Keep docs in sync.** If you change interfaces/configs, update the relevant `AGENTS.md` and the [Roadmap](./ALPHA_Software_Roadmap_v2.3.md).

## Development setup
- OS: Ubuntu 22.04 (Jetson Orin) / Dev container
- ROS 2: Humble
- Containers: Docker Engine + Compose

```bash
# build
cd alpha_ws && colcon build --symlink-install && cd ..

# run (dev)
ros2 launch alpha_bringup startup.launch.py
```

## Tests & checks
- **Test policy (CI v1.0):**
  - Mark every test with `@pytest.mark.unit` or `@pytest.mark.integration`.
  - Core CI gates on unit tests only: `pytest -m unit`.
  - Integration tests run non‑gating on changes/nightly: `pytest -m integration`.
  - Mapping package (`alpha_mapping`) builds in a separate non‑gating job; logs are uploaded.
  - Promotion rule: after 7 consecutive green mapping+integration runs (or 1 week), they may be moved back into gating.
- **Local quick checks:**
  - `python3 -m pytest -m unit -q`
  - `python3 scripts/validate_configs.py` (schema check)
- **Docs validation:** run the AGENTS tooling.
```bash
python3 scripts/agents_validate.py .
AGENTS_INDEX_NO_DATE=1 python3 scripts/agents_index.py . docs/AGENTS_INDEX.md
```

## CI guardrails
- Sensors workflow enforces “packages‑first” `colcon build` usage; avoid `--cmake-args` before `--packages-select`.
- CI uses apt retries, rosdep metadata caching, and ccache; see `.github/workflows/` for details.

## Commit & PR style
- Use clear, descriptive titles.
- Reference issues like `Fixes #123` where appropriate.
- Prefer Conventional Commits (`feat:`, `fix:`, `docs:`) if natural; not mandatory.

## Licensing
By contributing, you agree that your contributions are licensed under the **Apache License 2.0** (see [`LICENSE`](./LICENSE)).

## Security
Please avoid discussing vulnerabilities in public issues. Until a private channel is published, open a minimal issue stating that a security concern exists; a maintainer will reach out for details.

## Safety
- Always test motion in a safe environment with an e‑stop within reach.
- Do not merge changes that break acceptance tests in the roadmap.
