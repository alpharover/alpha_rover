# AGENTS.md Style Guide (v1)

- Keep the YAML front matter minimal, machine-parseable, and **accurate**.
- Write short, specific sentences. Avoid hype; note assumptions.
- Prefer tables for interfaces (topics/services). Include message types and rates.
- Every runbook command must be **copy/paste runnable** on a fresh system.
- Link to source files and configs using **relative paths**.
- If a section doesn't apply, include it and write `None` rather than omitting it.
- Update the `updated:` field on every substantive change.
- When adding a new component, add its `AGENTS.md` and re-run:
  - `python3 scripts/agents_validate.py .`
  - `python3 scripts/agents_index.py . docs/AGENTS_INDEX.md`
