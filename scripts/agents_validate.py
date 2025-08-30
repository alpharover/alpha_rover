#!/usr/bin/env python3
import os, sys, re, json, pathlib

RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_FRONT = re.compile(r"^---\s*$")

REQUIRED = ["agent","component_type","status","version","updated","owner","links","dependencies","provides","configs","runbooks"]
ENUMS = {
  "component_type": {"ros2_package","config","deploy","docs","tooling"},
  "status": {"draft","alpha","beta","stable","deprecated"}
}

def parse_front_matter(text):
  lines = text.splitlines()
  if not lines or not RE_FRONT.match(lines[0] if lines else ""):
    return None, text
  # collect until next ---
  fm_lines = []
  for i in range(1, len(lines)):
    if RE_FRONT.match(lines[i]):
      body = "\n".join(lines[i+1:])
      fm = "\n".join(lines[1:i])
      return fm, body
    else:
      fm_lines.append(lines[i])
  return None, text

def yaml_to_json(yaml_str):
  # naive YAML front-matter parser: supports only key: value, nested via indentation of two spaces, lists with - item
  # Good enough for our narrow template. Avoids external deps.
  import json
  indent_stack = [(-1, {})]  # (indent_level, current_obj)
  last_key_stack = []
  current = indent_stack[-1][1]
  last_list = None
  for raw in yaml_str.splitlines():
    if not raw.strip() or raw.strip().startswith("#"):
      continue
    indent = len(raw) - len(raw.lstrip(" "))
    while indent_stack and indent_stack[-1][0] >= indent:
      indent_stack.pop()
    if ":" in raw:
      key, val = raw.lstrip().split(":", 1)
      key = key.strip()
      val = val.strip()
      parent = indent_stack[-1][1]
      if val == "":
        # start new dict
        parent[key] = {}
        indent_stack.append((indent, parent[key]))
      else:
        # parse scalars rudimentarily (numbers, booleans, strings)
        if val.startswith("|"):
          # multiline literal block: consume subsequent indented lines
          # gather until indentation decreases
          # For simplicity, treat as empty here; caller shouldn't rely on content for validation keys
          parent[key] = "<block>"
        else:
          if val.lower() in ("true","false"):
            parent[key] = val.lower() == "true"
          else:
            try:
              if "." in val:
                parent[key] = float(val)
              else:
                parent[key] = int(val)
            except ValueError:
              # strip quotes if present
              if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                parent[key] = val[1:-1]
              else:
                parent[key] = val
        last_key_stack = [key]
        last_list = None
    elif raw.lstrip().startswith("- "):
      item = raw.lstrip()[2:]
      parent = indent_stack[-1][1]
      # find a list to append to: if parent is a dict with last_key, create list if missing
      if isinstance(parent, dict):
        # find most recent key at this level; fallback to "_list"
        # Simplify: ensure last inserted key at this indent has list type
        # We'll accumulate into a special "__list__" if no key
        if not last_key_stack:
          if "__list__" not in parent:
            parent["__list__"] = []
          target = parent["__list__"]
        else:
          lk = last_key_stack[-1]
          if lk not in parent or not isinstance(parent[lk], list):
            parent[lk] = []
          target = parent[lk]
      else:
        target = parent
      # naive parse of item
      if item.startswith("{") and item.endswith("}"):
        # simple inline object
        try:
          # convert to JSON-compatible by quoting keys if necessary is hard; assume valid JSON-like
          target.append(json.loads(item.replace("'", '"')))
        except Exception:
          target.append(item)
      else:
        target.append(item.strip())
  return indent_stack[0][1]

def validate_front(front, path):
  errs = []
  for k in REQUIRED:
    if k not in front:
      errs.append(f"missing required key: {k}")
  if "component_type" in front and front["component_type"] not in ENUMS["component_type"]:
    errs.append(f"invalid component_type: {front['component_type']}")
  if "status" in front and front["status"] not in ENUMS["status"]:
    errs.append(f"invalid status: {front['status']}")
  if "updated" in front and not RE_DATE.match(str(front["updated"])):
    errs.append(f"invalid updated date (YYYY-MM-DD): {front['updated']}")
  # minimal link presence
  if "links" in front and "roadmap" not in front["links"]:
    errs.append("links.roadmap is required")
  return errs

def main():
  base = sys.argv[1] if len(sys.argv) > 1 else "."
  failed = False
  found = 0
  for dirpath, _, filenames in os.walk(base):
    for fn in filenames:
      if fn == "AGENTS.md":
        found += 1
        p = os.path.join(dirpath, fn)
        with open(p, "r", encoding="utf-8") as f:
          txt = f.read()
        fm_txt, body = parse_front_matter(txt)
        if fm_txt is None:
          print(f"[ERROR] {p}: missing YAML front matter")
          failed = True
          continue
        front = yaml_to_json(fm_txt)
        errs = validate_front(front, p)
        if errs:
          failed = True
          print(f"[ERROR] {p}:")
          for e in errs:
            print(f"  - {e}")
        else:
          print(f"[OK] {p}")
  if found == 0:
    print("[WARN] no AGENTS.md files found under", base)
  sys.exit(1 if failed else 0)

if __name__ == "__main__":
  main()
