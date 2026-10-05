#!/usr/bin/env bash
set -euo pipefail

repo=graystone-john/daedalus-sandbox
workspace=/home/daedalus/graystone/daedalus-sandbox
baseline=234a729f5a2ef05ecd6448c20acec2889ea5179f

cd "$workspace"
test "$(git remote get-url origin)" = "git@github.com:$repo.git"
test "$(gh api user --jq .login)" = "graystone-daedalus"

git fetch origin
remote_tag="$(git ls-remote origin 'refs/tags/demo-baseline^{}' | awk '{print $1}')"
if [ "$remote_tag" != "$baseline" ]; then
    echo "Baseline tag does not resolve to the expected starter commit." >&2
    exit 1
fi

if git diff --quiet "$baseline" origin/main -- index.html TASK.md; then
    echo "Main already contains baseline index.html and TASK.md."
    exit 0
fi

branch=daedalus/reset-demo-baseline
existing_pr="$(gh pr list --repo "$repo" --head "$branch" --base main     --state open --json url --jq '.[0].url // empty')"
if [ -n "$existing_pr" ]; then
    echo "Existing reset PR: $existing_pr"
    exit 0
fi

if git show-ref --verify --quiet "refs/heads/$branch" ||
   [ -n "$(git ls-remote --heads origin "$branch")" ]; then
    echo "Reset branch already exists without an open PR; inspect it before continuing." >&2
    exit 1
fi

temp_root="$(mktemp -d /home/daedalus/graystone/demo-reset.XXXXXXXX)"
worktree="$temp_root/worktree"
git worktree add -b "$branch" "$worktree" origin/main

cd "$worktree"
git restore --source="$baseline" --staged --worktree -- index.html TASK.md
git diff --cached --check
git diff --cached --stat
git -c user.name=Daedalus -c user.email=daedalus@graystone.systems     commit -m "Reset demo page and task to Cycle 0 baseline"
git push -u origin "$branch"

cat > "$temp_root/pr-body.md" <<'BODY'
Restore index.html and TASK.md from the demo-baseline starter commit.

This returns the page to Cycle 0 while preserving project instructions,
CODEOWNERS, workflows, and Git history.

The running demo checkout is unchanged. After human approval and merge,
update that checkout to main or restore it through demo provisioning.
BODY

url="$(gh pr create --repo "$repo" --base main --head "$branch"     --title "Reset demo to Cycle 0 baseline"     --body-file "$temp_root/pr-body.md" --reviewer graystone-john)"
echo "RESET_PR_CREATED=$url"

cd "$workspace"
git worktree remove "$worktree"
rm "$temp_root/pr-body.md"
rmdir "$temp_root"
