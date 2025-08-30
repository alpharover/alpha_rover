Documentation plan (for Codex to implement, step‑by‑step)

1) File layout (where AGENTS.md live)
	•	Root: /AGENTS.md — project overview + links to major components.
	•	Per component: place an AGENTS.md in each relevant folder:
	•	alpha_ws/src/<package>/AGENTS.md
	•	alpha_configs/AGENTS.md
	•	deploy/AGENTS.md
	•	docs/AGENTS.md (if you have doc tooling)
	•	Generator output: docs/AGENTS_INDEX.md — auto‑generated table linking all of them.

2) Mandatory structure (machine‑parseable)
	•	YAML front‑matter at the top of every AGENTS.md with these required keys:
	•	agent, component_type, status, version, updated, owner
	•	links (must include roadmap)
	•	dependencies (internal/external)
	•	provides (topics/services/actions)
	•	configs
	•	runbooks (start/stop/healthcheck)
	•	Body sections (human‑readable):
	1.	Mission & Context
	2.	Responsibilities & Boundaries
	3.	Interfaces (tables for topics/services/params)
	4.	Runbooks (copy‑paste commands)
	5.	Observability (SLOs/metrics/logs)
	6.	Failure Modes & Recovery
	7.	Security
	8.	Tests (acceptance + CI jobs)
	9.	Change & Decision Log (point to ADRs/PRs)

The template and schema are in the kit (docs/AGENTS_TEMPLATE.md, docs/agents.schema.json).

3) Cross‑linking requirements
	•	Every AGENTS.md must link the roadmap: links.roadmap: ../ALPHA_Software_Roadmap_v2.3.md.
	•	Interface tables must list topic names + message types + rates and service names + types.
	•	Configs must reference concrete files in alpha_configs/ (e.g., lidar_airy.yaml).
	•	For vendor quirks (e.g., AIRY vertical‑angle table), include the path and hash location.

4) Automation (DocOps)
	•	Validate: run python3 scripts/agents_validate.py . in CI and pre‑commit.
	•	Index: run python3 scripts/agents_index.py . docs/AGENTS_INDEX.md to build the clickable map.
	•	Optional: wire those via the included Makefile or .pre-commit-config.yaml.

5) Acceptance and drift control
	•	A PR is not mergable if:
	•	Any AGENTS.md is missing required front‑matter keys.
	•	The roadmap references or interfaces change without updating the relevant AGENTS.md.
	•	CI should run the new tests tied to the roadmap (e.g., row‑reorder, startup delay) and publish links in the component’s AGENTS.md.

6) Onboarding flow for a new agent
	1.	Open root AGENTS.md → click docs/AGENTS_INDEX.md.
	2.	Skim alpha_bringup/AGENTS.md (startup sequence) and alpha_lidar_airy/AGENTS.md (reorder + op‑mode).
	3.	Follow runbooks to stand up a sim or HIL slice.
	4.	Use the Observability section to check SLOs and health.

7) Minimal content rules (to avoid junk docs)
	•	Write short, specific sentences. No fluff.
	•	Every command must be runnable as‑is on a fresh system.
	•	If a section doesn’t apply, keep it and set to None (so the parser doesn’t guess).
	•	Update the updated: date on any substantive change.

⸻

What’s already filled in for you (examples you can copy/paste)
	•	Root AGENTS.md: links to the v2.3 roadmap, points at alpha_ws/src/, alpha_configs/, and documents top‑level SLOs.
	•	alpha_lidar_airy/AGENTS.md: includes the 96×900 row‑reorder, OpM 0/1 service, angle_table_hash metric, runbooks, and acceptance tests.
	•	alpha_bringup/AGENTS.md: captures the RUN → wait 10s → start NVBlox startup sequence and publishes the startup status topic.
	•	alpha_configs/AGENTS.md: lists your config keys and a healthcheck command that queries the config service.

You can drop these into your repo as scaffolding, then fill in owners and exact paths.

Quick start (what Codex should do immediately)

# 1) Add the kit to the repo
unzip agents_doc_kit_v1.zip -d .
cp -r agents_doc_kit_v1/* .

# 2) Seed AGENTS.md files (copy examples to proper locations and edit)
mkdir -p alpha_ws/src/alpha_lidar_airy alpha_ws/src/alpha_bringup alpha_configs docs
cp examples/alpha_lidar_airy_AGENTS.md alpha_ws/src/alpha_lidar_airy/AGENTS.md
cp examples/alpha_bringup_AGENTS.md     alpha_ws/src/alpha_bringup/AGENTS.md
cp examples/alpha_configs_AGENTS.md     alpha_configs/AGENTS.md
cp examples/AGENTS.md                   AGENTS.md

# 3) Generate the index and validate
python3 scripts/agents_index.py . docs/AGENTS_INDEX.md
python3 scripts/agents_validate.py .

If you later add a new package, copy docs/AGENTS_TEMPLATE.md to that folder as AGENTS.md, fill the header, and re‑run the two scripts. The index stays fresh, and CI blocks drift.

⸻

Why this works
	•	The front‑matter schema gives Codex a clean machine interface to harvest context.
	•	The tables + runbooks give humans (and LLMs) fast, copy‑paste execution.
	•	The index prevents orphan components and makes status obvious at a glance.
	•	The plan matches your v2.3 roadmap’s concrete interfaces, so “docs lie” is less likely.

