# repo-radar-digest — project notes

Public weekly digest of the private repo-radar's CJK GitHub/Gitee output.
Site: https://acailic.github.io/repo-radar-digest (GitHub Pages, main/root —
generated HTML lives at repo root because Pages serves root, not /docs).

## How it works

- `issues/YYYY-Www.md` — radar digests as written by the private radar
  (source of truth; ISO-week filename is the contract).
- `python3 build.py` — renders issues → `index.html` + one `<week>.html` per
  issue + `feed.xml` (Atom, one entry per issue, newest first) at repo root.
  The feed is linked from the site header on every page and auto-discovered
  via `<link rel="alternate" type="application/atom+xml">`.
  Python 3.9+ stdlib only, no JS, no external assets;
  dark/light via `prefers-color-scheme`, no toggle.
  `build.py --check` fails if committed HTML is stale — regenerate with
  `python3 build.py` whenever an issue markdown changes.
- `publish.sh <digest.md> [--push]` — the weekly intake: validates ISO-week
  name, copies into `issues/`, rebuilds, commits `publish <week>`. The private
  radar calls it after each weekly run.

## Decisions worth remembering

- First public issue is 2026-W41. 2026-W42 was initially skipped (radar had
  no fresh scan data), but a W42 digest was generated from the 2026-10-12
  scan and published 2026-10-13 on the captain's call — the archive is now
  contiguous from W41; regular weekly cadence continues from W43.
- 2026-W42 permanently carries no *Week over week* (novo/nestalo/držanje)
  block, and that is not a bug to fix here. The block is powered by the
  radar's seen-memory `history`, which starts at 2026-W42: W41's run
  (2026-10-05) predates radar PR #6 (merged 2026-10-11 23:09 UTC) and W42's
  run (2026-10-12 06:41 UTC) found no `history["2026-W41"]`, so
  `render_week_diff` omitted it. It cannot be backfilled without fabricating
  radar data — the radar CLI only live-scans (no re-render path) and W42's
  editorial content came from the 2026-10-12 scan, which is not stored.
  Verified 2026-10-14; W43 onward carries the block (history accumulates
  from W42). build.py preserves the block when present (en + sr titles)
  instead of stripping it with the Featured-repos summary.
- Digest markdown is consumed, never edited here; fixes to format belong in
  the radar repo. The parser in build.py targets the digest's section
  structure (`## N. [name](#anchor)` + scorecard table rows License /
  Stack fit).

## Content rules

Translations and commentary are the radar's original output; facts are public
repo data. Digest footer credits Thysrael/Horizon (MIT) — keep that
attribution when restyling.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
