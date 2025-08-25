#!/usr/bin/env bash
set -euo pipefail

# Avoid interactive username/password prompts
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes}"

BASE_DIR="$HOME/alpha_ops"
SCAN_ROOTS_FILE="$BASE_DIR/repo_roots.txt"
LOG_PREFIX="[repos]"

if ! command -v git >/dev/null 2>&1; then
  echo "$LOG_PREFIX git not installed"; exit 2; fi

echo "$LOG_PREFIX scanning for repos under roots from $SCAN_ROOTS_FILE"
mapfile -t ROOTS < <(sed '/^\s*#/d;/^\s*$/d' "$SCAN_ROOTS_FILE" 2>/dev/null || printf %s "")
if [ ${#ROOTS[@]} -eq 0 ]; then
  ROOTS=("$HOME/ros2_ws" "$HOME/isaac_ros_common" "$HOME")
fi

REPOS=()
for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  while IFS= read -r path; do REPOS+=("${path%/.git}"); done < <(find "$root" -maxdepth 3 -type d -name .git -not -path "*/.cache/*" 2>/dev/null)
done

unique() { awk '!x[$0]++'; }
mapfile -t REPOS < <(printf '%s\n' "${REPOS[@]}" | unique)

echo "$LOG_PREFIX found ${#REPOS[@]} repositories"

for repo in "${REPOS[@]}"; do
  echo "$LOG_PREFIX -- $repo"
  if [ ! -d "$repo/.git" ]; then echo "$LOG_PREFIX skipping (not a git repo)"; continue; fi
  git -C "$repo" status -s || true
  # Only push if an origin exists
  if git -C "$repo" remote >/dev/null 2>&1; then
    url=$(git -C "$repo" remote get-url --push origin 2>/dev/null || git -C "$repo" remote get-url origin 2>/dev/null || echo "")
    [ -n "$url" ] && echo "$LOG_PREFIX origin=$url" || echo "$LOG_PREFIX origin=(none)"

    # Extract GitHub owner/repo if applicable
    gh_owner=""; gh_repo=""
    if echo "$url" | grep -q "github.com"; then
      path="$url"
      if echo "$url" | grep -qE '^https?://'; then
        path=$(echo "$url" | sed -E 's#https?://[^/]+/##')
      elif echo "$url" | grep -q '^ssh://'; then
        path=$(echo "$url" | sed -E 's#^ssh://[^/]+/##')
      else
        # scp-style git@github.com:owner/repo.git
        path=$(echo "$url" | sed -E 's#^[^:]+:##')
      fi
      gh_owner=$(echo "$path" | cut -d/ -f1)
      gh_repo=$(echo "$path" | cut -d/ -f2 | sed 's/\.git$//')
    fi

    # If GitHub remote is HTTPS and owned by our user, auto-switch to SSH
    if echo "$url" | grep -qE '^https://github.com/' && [ "$gh_owner" = "alpharover" ] && [ -n "$gh_repo" ]; then
      newurl="git@github.com:${gh_owner}/${gh_repo}.git"
      echo "$LOG_PREFIX switching origin to SSH: $newurl"
      git -C "$repo" remote set-url origin "$newurl" || true
      url="$newurl"
    fi

    # Build list of remotes to push: prefer 'backup', then 'origin' if present
    push_remotes=()
    git -C "$repo" remote | grep -qx backup && push_remotes+=(backup)
    git -C "$repo" remote | grep -qx origin && push_remotes+=(origin)

    # Skip origin if it's HTTPS GitHub to avoid prompts
    if [ "${#push_remotes[@]}" -gt 0 ]; then
      git -C "$repo" -c credential.interactive=never fetch -p || true
      for rname in "${push_remotes[@]}"; do
        rurl=$(git -C "$repo" remote get-url "$rname" 2>/dev/null || echo "")
        if [ "$rname" = origin ] && echo "$rurl" | grep -qE '^https://github.com/'; then
          echo "$LOG_PREFIX [skip] origin over HTTPS; convert to SSH to push"
          continue
        fi
        echo "$LOG_PREFIX pushing to $rname"
        git -C "$repo" -c credential.interactive=never push "$rname" --all || true
        git -C "$repo" -c credential.interactive=never push "$rname" --tags || true
      done
    else
      echo "$LOG_PREFIX [info] no remotes to push"
    fi
  else
    echo "$LOG_PREFIX [info] no origin remote; skipping push"
  fi
done

echo "$LOG_PREFIX complete"
