# repo-radar-digest — project notes

Public weekly digest of the private repo-radar's CJK GitHub/Gitee output.
Site: https://acailic.github.io/repo-radar-digest (GitHub Pages, main/root —
generated HTML lives at repo root because Pages serves root, not /docs).

## How it works

- `issues/YYYY-Www.md` — radar digests as written by the private radar
  (source of truth; ISO-week filename is the contract).
- `python3 build.py` — renders issues → `index.html` + one `<week>.html` per
  issue at repo root. Python 3.9+ stdlib only, no JS, no external assets;
  dark/light via `prefers-color-scheme`, no toggle.
  `build.py --check` fails if committed HTML is stale — regenerate with
  `python3 build.py` whenever an issue markdown changes.
- `publish.sh <digest.md> [--push]` — the weekly intake: validates ISO-week
  name, copies into `issues/`, rebuilds, commits `publish <week>`. The private
  radar calls it after each weekly run.

## Decisions worth remembering

- First public issue is 2026-W41; 2026-W42 was never generated (radar had no
  fresh scan data) so regular cadence starts at W43. Do not "backfill" W42.
- Digest markdown is consumed, never edited here; fixes to format belong in
  the radar repo. The parser in build.py targets the digest's section
  structure (`## N. [name](#anchor)` + scorecard table rows License /
  Stack fit).

## Content rules

Translations and commentary are the radar's original output; facts are public
repo data. Digest footer credits Thysrael/Horizon (MIT) — keep that
attribution when restyling.
