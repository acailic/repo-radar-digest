#!/usr/bin/env bash
# publish.sh — install a radar digest as a new public issue and commit it.
#
# Usage (from anywhere, e.g. as a hook called by the private repo-radar):
#   ./publish.sh /path/to/digests/2026-W43.md [--push]
#
# What it does:
#   1. validates the file name matches YYYY-Www.md (ISO week)
#   2. copies it into issues/
#   3. rebuilds the site (python3 build.py — must succeed)
#   4. commits issues/<week>.md + regenerated HTML + feed.xml in one atomic
#      "publish <week>" commit — the new page must never be live while
#      feed.xml still describes the old archive (the PR #4 trap)
#   5. fails if any regenerated file was left out of that commit
#
# --push additionally pushes the current branch to origin (GitHub Pages serves
# main/root, so pushing main is what makes the new issue live). Without it the
# script only commits locally, leaving the push decision to you.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEEK_RE='^[0-9]{4}-W[0-9]{2}\.md$'

PUSH=0
if [[ "${2:-}" == "--push" || "${3:-}" == "--push" ]]; then PUSH=1; fi

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <digest.md> [--push]" >&2; exit 2
fi
SRC="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"

if ! [[ "$(basename "$SRC")" =~ $WEEK_RE ]]; then
  echo "publish: '$(basename "$SRC")' does not match YYYY-Www.md (ISO week)" >&2; exit 2
fi
WEEK="$(basename "$SRC" .md)"

if [[ -e "$REPO_ROOT/issues/$WEEK.md" ]]; then
  echo "publish: issue $WEEK already exists — refusing to overwrite (delete it first to republish)" >&2; exit 1
fi

cd "$REPO_ROOT"
cp "$SRC" "issues/$WEEK.md"
# On any failure before the commit lands, roll back to pre-publish state:
# drop the copied digest and restore what build.py regenerated.
trap 'rm -f "issues/$WEEK.md" "$WEEK.html"; git checkout -- index.html feed.xml 2>/dev/null || true' ERR
python3 build.py

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "main" ]] || echo "publish: note — committing on branch '$BRANCH', not main" >&2
# Atomic publish: week page, archive index AND feed land in the same commit.
git add "issues/$WEEK.md" index.html *.html feed.xml
git commit -m "publish $WEEK"

# Tripwire: if build.py regenerated anything the commit above did not stage,
# the publish is incomplete — fail loudly instead of shipping a stale feed.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "publish: publish commit for $WEEK is incomplete — regenerated files left uncommitted:" >&2
  git status --porcelain >&2
  echo "  fix with: git add <files above> && git commit --amend --no-edit" >&2
  exit 1
fi
trap - ERR

if [[ $PUSH -eq 1 ]]; then
  git push origin "$BRANCH"
  echo "publish: $WEEK pushed — live at https://acailic.github.io/repo-radar-digest/$WEEK.html"
else
  echo "publish: $WEEK committed. Push when ready:"
  echo "  git push origin $BRANCH"
fi
