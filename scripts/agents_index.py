#!/usr/bin/env python3
import os, sys, re, datetime

RE_FRONT = re.compile(r"^---\s*$")

def parse_front_matter(text):
  lines = text.splitlines()
  if not lines or not RE_FRONT.match(lines[0] if lines else ""):
    return {}, text
  fm_lines = []
  for i in range(1, len(lines)):
    if RE_FRONT.match(lines[i]):
      body = "\n".join(lines[i+1:])
      fm = "\n".join(lines[1:i])
      break
    else:
      fm_lines.append(lines[i])
  else:
    return {}, text
  # extremely naive key: value parser for specific keys
  meta = {}
  for raw in fm.splitlines():
    if ":" not in raw:
      continue
    k, v = raw.strip().split(":", 1)
    k = k.strip()
    v = v.strip().strip('"')
    if k in ("agent","component_type","status","version","updated","owner"):
      meta[k] = v.strip('"')
  return meta, body

def main():
  base = sys.argv[1] if len(sys.argv) > 1 else "."
  out = sys.argv[2] if len(sys.argv) > 2 else "AGENTS_INDEX.md"
  rows = []
  for dirpath, _, filenames in os.walk(base):
    for fn in filenames:
      if fn == "AGENTS.md":
        p = os.path.join(dirpath, fn)
        with open(p, "r", encoding="utf-8") as f:
          txt = f.read()
        meta, _ = parse_front_matter(txt)
        rel = os.path.relpath(p, base)
        rows.append((meta.get("agent", rel), meta.get("component_type","?"), meta.get("status","?"), meta.get("version","?"), meta.get("updated","?"), meta.get("owner","?"), rel))
  rows.sort(key=lambda x: (x[1], x[0]))
  with open(out, "w", encoding="utf-8") as f:
    f.write("# AGENTS Index\n\n")
    # Avoid CI churn: allow suppressing date line via env var
    if not os.environ.get("AGENTS_INDEX_NO_DATE"):
      f.write(f"_Generated: {datetime.date.today().isoformat()}_\n\n")
    f.write("| Agent | Type | Status | Version | Updated | Owner | Path |\n")
    f.write("|---|---|---|---|---|---|---|\n")
    for r in rows:
      agent, typ, status, ver, upd, owner, rel = r
      f.write(f"| {agent} | {typ} | {status} | {ver} | {upd} | {owner} | [{rel}]({rel}) |\n")
  print("Wrote", out)

if __name__ == "__main__":
  main()
