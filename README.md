# Agents Doc Kit (v1)

This kit helps you maintain a chain of `AGENTS.md` files across the project so a new agent (human or LLM) can get up to speed fast.

## Contents
- `docs/AGENTS_TEMPLATE.md` — copy this per component.
- `docs/agents.schema.json` — front-matter schema (minimal).
- `docs/AGENTS_STYLE.md` — writing guidelines.
- `scripts/agents_validate.py` — validates front matter without external deps.
- `scripts/agents_index.py` — generates `docs/AGENTS_INDEX.md` listing all agents.
- `examples/` — sample AGENTS.md files for root, `alpha_lidar_airy`, `alpha_bringup`, `alpha_configs`.
- `.pre-commit-config.yaml` and `Makefile` — optional automation.

## Quick start
1. Copy `examples/AGENTS.md` to your repo root and edit fields.
2. For each package/config, copy the template to `AGENTS.md`, fill fields.
3. Run validation and index:
   ```bash
   make agents-validate
   make agents-index
   ```
4. Commit and push. Add pre-commit if you want auto-checks.

_Last updated: 2025-08-30_
