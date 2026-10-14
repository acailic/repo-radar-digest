#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard testovi arhive sajta (unittest, bez spoljnih zavisnosti).

Enumeriše objavljene nedelje iz arhivnog indeksa (index.html) i tvrdi za
svaku: postoji stranica nedelje <YYYY-Www>.html i stavka u feed.xml.
Tri izvora nedelja — issues/ (izvor istine), arhivni indeks i feed —
mora se poklapati: nema nedelje bez unosa, nema siročića u feedu.

Mutation provera: kad se objavi nedelja (issues/<week>.md + regeneracija)
a feed.xml ne uđe u komit — tačno zamka publish.sh-a, čiji `git add`
navodi issues/<week>.md, index.html i *.html ali NE i feed.xml — test
pada pre nego što nezavršena nedelja stigne na sajt.

The tests assert the contract of what we publish (stranica + feed stavka
po nedelji), not third-party behavior (da li čitaoci feeda klikću).

Pokretanje: python3 tests/test_archive.py
(deo CI lanca — .github/workflows/ci.yml, zajedno sa build.py --check)
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://acailic.github.io/repo-radar-digest"
WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")


def weeks_from_issues():
    """Nedelje objavljene u izvoru: issues/*.md sa ISO-week imenom."""
    issues = ROOT / "issues"
    return {p.stem for p in issues.glob("*.md") if WEEK_RE.match(p.stem)}


def weeks_from_index():
    """Nedelje koje arhivni indeks index.html navodi (ul.archive → a.week)."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    arch = re.search(r'<ul class="archive">(.*?)</ul>', html, re.S)
    if not arch:
        return set()
    return set(re.findall(r'<a class="week" href="(\d{4}-W\d{2})\.html">', arch.group(1)))


def weeks_from_feed():
    """Nedelje sa stavkom u feed.xml (Atom <id> je URL stranice nedelje)."""
    xml = (ROOT / "feed.xml").read_text(encoding="utf-8")
    pat = r"<id>%s/(\d{4}-W\d{2})\.html</id>" % re.escape(SITE_URL)
    return set(re.findall(pat, xml))


class ArchiveCoverageTests(unittest.TestCase):
    maxDiff = None

    def test_issues_index_and_feed_list_the_same_weeks(self):
        """Sva tri izvora nedelja moraju biti identičan skup.

        Pada kad se doda nedelja bez unosa (issues/ izvan indeksa/feeda —
        zaboravljena regeneracija; indeks/feed van issues/ — siroče) ili
        kad feed zaostane za objavom (publish.sh ne stajluje feed.xml).
        """
        issues = weeks_from_issues()
        index = weeks_from_index()
        feed = weeks_from_feed()

        self.assertTrue(issues, "issues/ nema nijedan ISO-week .md — test ne zna šta je objavljeno")

        if issues != index:
            missing = sorted(issues - index)
            extra = sorted(index - issues)
            self.fail(
                "arhivni indeks (index.html) ne pokriva objavljene nedelje.\n"
                "  nedostaje u indeksu: %s\n  viška u indeksu: %s\n"
                "Regeneriši i komituj: python3 build.py" % (missing or "—", extra or "—"))

        if issues != feed:
            missing = sorted(issues - feed)
            extra = sorted(feed - issues)
            self.fail(
                "feed.xml nema stavku za svaku objavljenu nedelju.\n"
                "  nedostaje u feedu: %s\n  viška u feedu: %s\n"
                "Regeneriši i KOMITUJ i feed.xml: python3 build.py && git add feed.xml "
                "(publish.sh ga ne stajluje!)" % (missing or "—", extra or "—"))

    def test_every_published_week_has_a_page(self):
        """Za svaku nedelju iz indeksa postoji stranica nedelje sa ispravnim canonical URL-om."""
        for week in sorted(weeks_from_index()):
            with self.subTest(week=week):
                path = ROOT / (week + ".html")
                self.assertTrue(
                    path.is_file(),
                    "nedostaje stranica nedelje %s.html — regeneriši: python3 build.py" % week)
                page = path.read_text(encoding="utf-8")
                self.assertIn(
                    '<link rel="canonical" href="%s/%s.html">' % (SITE_URL, week),
                    page,
                    "%s.html: canonical URL nije stranica te nedelje" % week)

    def test_every_published_week_has_a_feed_entry(self):
        """Za svaku nedelju iz indeksa feed.xml ima <entry> sa id i linkom na tu stranicu."""
        xml = (ROOT / "feed.xml").read_text(encoding="utf-8")
        for week in sorted(weeks_from_index()):
            with self.subTest(week=week):
                entry_re = (
                    r"<entry>(?:(?!</entry>).)*?"
                    r'<link href="%s/%s\.html" rel="alternate"/>'
                    r"(?:(?!</entry>).)*?"
                    r"<id>%s/%s\.html</id>"
                    r"(?:(?!</entry>).)*?</entry>"
                ) % (re.escape(SITE_URL), week, re.escape(SITE_URL), week)
                self.assertRegex(
                    xml, re.compile(entry_re, re.S),
                    "feed.xml nema stavku za %s (id/link na %s.html)" % (week, week))


if __name__ == "__main__":
    unittest.main(verbosity=2)
