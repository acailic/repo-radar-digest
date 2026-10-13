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
- Digest markdown is consumed, never edited here; fixes to format belong in
  the radar repo. The parser in build.py targets the digest's section
  structure (`## N. [name](#anchor)` + scorecard table rows License /
  Stack fit).

## Content rules

Translations and commentary are the radar's original output; facts are public
repo data. Digest footer credits Thysrael/Horizon (MIT) — keep that
attribution when restyling.
