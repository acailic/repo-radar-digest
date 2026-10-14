#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Funkcionalni guard test publish.sh-a (unittest, bez spoljnih zavisnosti).

Zamka dokumentovana uz PR #4: publish.sh-ov `git add` je stajlovao stranicu
nedelje i indeks ali NE i feed.xml — objava bi ostavila regenerisan feed
nekomitovan, pa bi CI archive-guard pao tek na PR-u. Ovaj test odigra pravu
objavu kroz publish.sh u svežem klonu repozitorijuma i tvrdi da je publish
komit atomičan: stranica nedelje, index.html I feed.xml ulaze u isti komit,
komitovani feed sadrži novu nedelju, a radno drvo ostaje čisto (ništa
regenerisano ne ostaje po strani).

Pokretanje: python3 tests/test_publish.py
(deo CI lanca — .github/workflows/ci.yml, zajedno sa build.py --check)
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Minimalan digest u formatu privatnog radara: ono što parse_digest u
# build.py-u cilja (## N. [name](#anchor) — title + scorecard redovi), sa
# fiksnim "Generated" časom da izlaz bude determinističkan.
DIGEST = """# 🌏 Foreign Repo Radar — {week}

> Scanned **1** repo, kept **1** candidate, featured **1** below. Generated 2099-01-01 00:00 UTC by `repo-radar` (test fixture).

---

**Featured repos**

1. [example/test-repo](#example-test-repo) ⭐️ 9/10 · 🆕

---

## 1. [example/test-repo](#example-test-repo) — example/test-repo

[github.com/example/test-repo](https://github.com/example/test-repo) · ⭐ 1 total · Language: Python · 🆕 new this week

**Radar scorecard**

| Dimension | Assessment |
|---|---|
| License | MIT — permissive ✅ |
| Data confidence | **high** — all signals sampled |
| Stack fit (captain) | **strong** |

---

*Digest by the private repo-radar (built on Thysrael/Horizon, MIT).*
"""


def git(repo, *args, env=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, env=env, check=True,
    ).stdout


class PublishAtomicityTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="publish-guard-")
        self.clone = Path(self.tmp.name) / "clone"
        subprocess.run(
            ["git", "clone", "-q", str(ROOT), str(self.clone)],
            capture_output=True, text=True, check=True,
        )
        # Nedelja posle poslednje objavljene — publish.sh odbija prepisivanje.
        latest = max(p.stem for p in (self.clone / "issues").glob("*.md"))
        m = re.match(r"(\d{4})-W(\d{2})$", latest)
        year, wk = int(m.group(1)), int(m.group(2)) + 1
        if wk > 52:
            year, wk = year + 1, 1
        self.week = "%04d-W%02d" % (year, wk)
        self.digest = Path(self.tmp.name) / ("%s.md" % self.week)
        self.digest.write_text(DIGEST.format(week=self.week), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def env(self):
        # CI nema git identitet; publish.sh poziva običan `git commit`.
        e = os.environ.copy()
        e.update({
            "GIT_AUTHOR_NAME": "publish-guard",
            "GIT_AUTHOR_EMAIL": "publish-guard@example.invalid",
            "GIT_COMMITTER_NAME": "publish-guard",
            "GIT_COMMITTER_EMAIL": "publish-guard@example.invalid",
        })
        return e

    def test_publish_commits_page_index_and_feed_atomically(self):
        """publish <week> komit mora obuhvatiti stranicu, indeks i feed.xml.

        Ovo je tačno zamka iz PR #4: nova stranica živa a feed star. Pada i na
        prljavom radnom drvetu posle objave (regenerisano, a nestajlovano).
        """
        run = subprocess.run(
            ["bash", str(self.clone / "publish.sh"), str(self.digest)],
            cwd=self.tmp.name, capture_output=True, text=True, env=self.env(),
        )
        self.assertEqual(
            run.returncode, 0,
            "publish.sh nije uspeo za %s:\nstdout:\n%s\nstderr:\n%s"
            % (self.week, run.stdout, run.stderr))

        committed = set(git(self.clone, "diff-tree", "--no-commit-id",
                            "--name-only", "-r", "HEAD", env=self.env()).split())
        for path in ("issues/%s.md" % self.week, "%s.html" % self.week,
                     "index.html", "feed.xml"):
            self.assertIn(
                path, committed,
                "publish komit ne sadrži %s — objava nije atomična "
                "(git add u publish.sh): %s" % (path, sorted(committed)))

        committed_feed = git(self.clone, "show", "HEAD:feed.xml", env=self.env())
        self.assertIn(
            "%s.html" % self.week, committed_feed,
            "komitovani feed.xml ne sadrži stavku za %s — publish je ostavio "
            "feed koji zaostaje za stranicom" % self.week)

        dirty = git(self.clone, "status", "--porcelain", env=self.env())
        self.assertEqual(
            dirty, "",
            "radno drvo posle publish komita nije čisto — nešto regenerisano "
            "je ostalo nestajlovano:\n%s" % dirty)


if __name__ == "__main__":
    unittest.main(verbosity=2)
