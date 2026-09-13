#!/usr/bin/env bash
set -euo pipefail

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git remote add upstream https://github.com/razvanzeces/flowstation.git
git fetch --no-tags upstream main
changed=false
if git merge-base --is-ancestor upstream/main HEAD; then
  age=$(( ($(date -u +%s) - $(git log -1 --format=%ct)) / 86400 ))
  if (( age >= 25 )); then
    date -u +%FT%TZ > .github/HEARTBEAT
    git add .github/HEARTBEAT
    git commit -m 'chore: keep scheduled upstream tracking active'
    git push origin HEAD:refs/heads/main
  fi
else
  # Always create a merge commit so fork automation can be restored before commit.
  merge_status=0
  git merge --no-commit --no-ff upstream/main || merge_status=$?
  git rev-parse --verify MERGE_HEAD >/dev/null
  git restore --source=HEAD --staged --worktree -- .github
  if [[ -n "$(git diff --name-only --diff-filter=U)" ]]; then
    git diff --name-only --diff-filter=U
    git merge --abort
    echo '::error::Upstream conflicts require a manual merge; main was not pushed.'
    exit 1
  fi
  # A merge returning 1 is acceptable only when all conflicts were in .github.
  if (( merge_status > 1 )); then git merge --abort; exit "$merge_status"; fi
  git commit --no-edit
  git push origin HEAD:refs/heads/main
  changed=true
fi
echo "changed=$changed" >> "$GITHUB_OUTPUT"
echo "sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"
echo "Upstream razvanzeces/flowstation main: changed=$changed" >> "$GITHUB_STEP_SUMMARY"
