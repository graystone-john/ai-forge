#!/usr/bin/env bash
set -euo pipefail

repo=graystone-john/daedalus-sandbox
workspace=/home/daedalus/graystone/daedalus-sandbox
baseline=234a729f5a2ef05ecd6448c20acec2889ea5179f
mode="${1:-prepare}"

fail() { echo "$*" >&2; exit 1; }

cd "$workspace"
test "$(git remote get-url origin)" = "git@github.com:$repo.git"
test "$(gh api user --jq .login)" = graystone-daedalus

# Prevent two reset script invocations from changing Git concurrently.
exec 9>"$workspace/.git/demo-reset.lock"
flock -n 9 || fail "Another reset operation is running."

if [ "$mode" = apply ]; then
    pr="${2:?Missing PR URL or none}"
    if [ "$pr" != none ]; then
        state="$(gh pr view "$pr" --repo "$repo" --json state --jq .state)"
        case "$state" in
            OPEN) echo "Waiting for approval and merge: $pr"; exit 75 ;;
            MERGED) ;;
            *) fail "Reset PR was closed without merging: $pr" ;;
        esac
    fi

    git fetch origin
    git diff --quiet "$baseline" origin/main -- index.html TASK.md ||
        fail "Origin/main does not match the demo baseline; checkout preserved."

    test -z "$(git status --porcelain)" ||
        fail "Workspace has local changes; checkout preserved."

    test "$(git rev-list --count HEAD --not --remotes=origin)" -eq 0 ||
        fail "Current checkout has unpushed commits; checkout preserved."

    if git show-ref --verify --quiet refs/heads/main; then
        git merge-base --is-ancestor main origin/main ||
            fail "Local main cannot fast-forward; checkout preserved."
    fi

    before="$(git rev-parse HEAD)"
    git switch main
    git merge --ff-only origin/main

    python3 - <<'PY'
from pathlib import Path
from urllib.request import urlopen

expected = Path("index.html").read_bytes()
with urlopen("http://127.0.0.1:8095/", timeout=10) as response:
    actual = response.read()
if actual != expected:
    raise SystemExit("Served page differs from the checked-out index.html.")
print("Verified: running HTTP page matches baseline index.html.")
PY

    if [ "$before" != "$(git rev-parse HEAD)" ]; then
        echo "RESET_CHECKOUT_UPDATED"
    fi
    echo "RESET_COMPLETE=$(git rev-parse HEAD)"
    exit 0
fi

test "$mode" = prepare || fail "Usage: $0 prepare | apply <PR URL|none>"
git fetch origin

remote_tag="$(git ls-remote origin 'refs/tags/demo-baseline^{}' | awk '{print $1}')"
test "$remote_tag" = "$baseline" ||
    fail "Baseline tag does not resolve to the expected starter commit."

if git diff --quiet "$baseline" origin/main -- index.html TASK.md; then
    echo "Main already contains the baseline."
    echo "RESET_PR=none"
    exit 0
fi

existing_pr="$(gh pr list --repo "$repo" --base main --state open \
    --author graystone-daedalus --limit 100 \
    --json headRefName,url \
    --jq '[.[] | select(.headRefName | startswith("daedalus/reset-demo-baseline"))] | .[0].url // empty')"

if [ -n "$existing_pr" ]; then
    echo "Reusing existing reset PR."
    echo "RESET_PR=$existing_pr"
    exit 0
fi

temp_root="$(mktemp -d /home/daedalus/graystone/demo-reset.XXXXXXXX)"
worktree="$temp_root/worktree"
branch="daedalus/reset-demo-baseline-$(date -u +%Y%m%dT%H%M%SZ)-${temp_root##*.}"

git worktree add -b "$branch" "$worktree" origin/main
cd "$worktree"
git restore --source="$baseline" --staged --worktree -- index.html TASK.md
git diff --cached --check
git -c user.name=Daedalus -c user.email=daedalus@graystone.systems \
    commit -m "Reset demo page and task to Cycle 0 baseline"
git push -u origin "$branch"

cat > "$temp_root/pr-body.md" <<'BODY'
Restore index.html and TASK.md from demo-baseline.

Preserves project instructions, CODEOWNERS, workflows, and Git history.
After human approval and merge, the reset flow updates the running
checkout only if local work is clean and preserved remotely.
BODY

url="$(gh pr create --repo "$repo" --base main --head "$branch" \
    --title "Reset demo to Cycle 0 baseline" \
    --body-file "$temp_root/pr-body.md")"

if ! gh pr edit "$url" --repo "$repo" --add-reviewer graystone-john; then
    echo "WARNING: PR created, but reviewer assignment failed; review manually: $url" >&2
fi

echo "RESET_PR_CREATED=$url"
echo "RESET_PR=$url"

cd "$workspace"
git worktree remove "$worktree"
rm "$temp_root/pr-body.md"
rmdir "$temp_root"
