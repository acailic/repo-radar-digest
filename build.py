#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render issues/*.md digests into self-contained static HTML pages.

Usage:
    python build.py            # build index.html + one page per issue + feed.xml
    python build.py --check    # exit 1 if committed HTML is stale (CI guard)

Zero dependencies: Python 3.9+ stdlib only, following the how-to-live-better
single-file pattern. Output is fully self-contained (inline CSS, no JS,
no external assets), dark/light via prefers-color-scheme with no toggle.

GitHub Pages serves this repo from main/root, so generated pages live next
to the sources: index.html plus <YYYY-Www>.html per issue and feed.xml (Atom,
one entry per issue, newest first).
"""

import argparse
import html
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ISSUES = HERE / "issues"
SITE_URL = "https://acailic.github.io/repo-radar-digest"
SITE_TITLE = "Foreign Repo Radar"
SITE_TAGLINE = "Weekly digest of trending CJK GitHub &amp; Gitee repos the West misses — translated, licensed, scored."
SITE_TAGLINE_PLAIN = "Weekly digest of trending CJK GitHub & Gitee repos the West misses — translated, licensed, scored."

WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
GENERATED_RE = re.compile(r"Generated (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) UTC")


# --------------------------------------------------------------- markdown

INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def esc(text):
    return html.escape(text, quote=False)


def inline(text):
    """Escape then apply inline markdown: links, bold, italic, code."""
    out = []
    pos = 0
    for m in INLINE_LINK_RE.finditer(text):
        out.append(_inline_no_links(text[pos:m.start()]))
        title, url = m.group(1), m.group(2)
        if url.startswith("#"):
            out.append('<a href="%s">%s</a>' % (esc_attr(url), _inline_no_links(title)))
        else:
            out.append('<a href="%s" rel="noopener">%s</a>' % (esc_attr(url), _inline_no_links(title)))
        pos = m.end()
    out.append(_inline_no_links(text[pos:]))
    return "".join(out)


def esc_attr(text):
    return html.escape(text, quote=True)


def _inline_no_links(text):
    """Bold, italic, code — applied after escaping."""
    text = esc(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", text)
    return text


def slugify(text):
    """GitHub-style heading slug (best effort; matches digest's own anchors)."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # keep link text
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", text).strip("-")


def md_to_html(md):
    """Small markdown renderer covering exactly what radar digests use:
    h1-h3, hr, blockquote, ul/ol, pipe tables, fenced code, paragraphs."""
    lines = md.splitlines()
    out, i, first_h1 = [], 0, True
    in_para = []

    def flush_para():
        if in_para:
            out.append("<p>%s</p>" % inline(" ".join(in_para)))
            in_para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush_para()
            i += 1
            continue
        if s.startswith("```"):
            flush_para()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(block)))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush_para()
            level = len(m.group(1))
            body = m.group(2)
            # Pull a hand-written anchor out of the first link, if any, so the
            # digest's own (#anchor) links keep working in our pages.
            am = INLINE_LINK_RE.search(body)
            ids = ""
            if am and am.group(2).startswith("#"):
                ids = ' id="%s"' % esc_attr(am.group(2)[1:])
                # strip the redundant self-link markup from the heading text
                body = body.replace(am.group(0), am.group(1), 1)
            else:
                ids = ' id="%s"' % esc_attr(slugify(body))
            tag = "h1" if level == 1 and first_h1 else "h%d" % min(level, 4)
            first_h1 = False
            out.append("<%s%s>%s</%s>" % (tag, ids, inline(body), tag))
            i += 1
            continue
        if re.match(r"^-{3,}$|^\*{3,}$", s):
            flush_para()
            out.append("<hr>")
            i += 1
            continue
        if s.startswith(">"):
            flush_para()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote><p>%s</p></blockquote>" % inline(" ".join(q.strip() for q in quote if q.strip())))
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            flush_para()
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ["<table><thead><tr>"]
            t.extend("<th>%s</th>" % inline(c) for c in header)
            t.append("</tr></thead><tbody>")
            for row in rows:
                t.append("<tr>")
                t.extend("<td>%s</td>" % inline(c) for c in row)
                t.append("</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        if re.match(r"^[-*+]\s+", s):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*+]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>")
            out.extend("<li>%s</li>" % inline(it) for it in items)
            out.append("</ul>")
            continue
        om = re.match(r"^(\d+)[.)]\s+(.*)$", s)
        if om:
            flush_para()
            items = []
            while i < len(lines):
                m2 = re.match(r"^(\d+)[.)]\s+(.*)$", lines[i].strip())
                if not m2:
                    break
                items.append(m2.group(2))
                i += 1
            out.append("<ol>")
            out.extend("<li>%s</li>" % inline(it) for it in items)
            out.append("</ol>")
            continue
        in_para.append(s)
        i += 1
    flush_para()
    return "\n".join(out)


# ------------------------------------------------------------ digest parse

class Repo:
    __slots__ = ("rank", "name", "url", "score", "what", "license", "fit", "title", "anchor")


def parse_digest(md):
    """Extract issue metadata and the per-repo top-list facts."""
    meta = {"title": "", "stats": "", "pulse": ""}
    repos = []

    h1 = re.search(r"^# (.+)$", md, re.M)
    if h1:
        meta["title"] = re.sub(r"\s*—\s*", " — ", h1.group(1).strip())
        meta["week"] = re.search(r"\d{4}-W\d{2}", meta["title"])
        meta["week"] = meta["week"].group(0) if meta["week"] else ""

    bq = re.search(r"^> (.+)$", md, re.M)
    if bq:
        meta["stats"] = bq.group(1).strip()

    pulse = re.search(r"\*\*This week's pulse:\*\*(.+?)(?:\n\n|\n---)", md, re.S)
    if pulse:
        meta["pulse"] = re.sub(r"\s+", " ", pulse.group(1)).strip()

    # Full per-repo sections: ## N. [name](#anchor) — title
    sections = re.split(r"^## (?=\d+\.)", md, flags=re.M)[1:]
    by_name = {}
    for sec in sections:
        head = re.match(r"(\d+)\.\s+\[([^\]]+)\]\(#([^)]+)\)\s*[—-]\s*(.*)$", sec.splitlines()[0])
        if not head:
            continue
        r = Repo()
        r.rank = int(head.group(1))
        r.name = head.group(2)
        r.anchor = head.group(3)
        r.url = "https://github.com/" + r.name
        r.title = head.group(4).strip().rstrip("…").strip()
        sm = re.search(r"\[github\.com/[^\]]+\]\((https://github\.com/[^)]+)\)", sec)
        if sm:
            r.url = sm.group(1)
        wm = re.search(r">\s*\*\*What it is:\*\*\s*(.+)", sec)
        r.what = re.sub(r"\s+", " ", wm.group(1)).strip() if wm else r.title
        lm = re.search(r"^\|\s*License\s*\|\s*(.+?)\s*\|", sec, re.M)
        r.license = lm.group(1) if lm else ""
        r.license = re.split(r"[—–-]\s", r.license, 1)[0].strip().rstrip(", ✅🔴").strip()
        fm = re.search(r"^\|\s*Stack fit \(captain\)\s*\|\s*\*\*(\w+)\*\*", sec, re.M)
        r.fit = fm.group(1).lower() if fm else ""
        scm = re.search(r"⭐️?\s*\*?\*?([\d.]+)/10", sec)
        r.score = scm.group(1) if scm else ""
        by_name[r.name.lower()] = r
        repos.append(r)
    repos.sort(key=lambda r: r.rank)
    meta["repos"] = repos
    return meta


# ----------------------------------------------------------------- layout

CSS = """
:root{--bg:#faf9f7;--fg:#1f2328;--muted:#5f6672;--accent:#8a2f2b;--card:#ffffff;
--border:#e4e1db;--code:#f3f1ec;--th:#f0eee9;--a:#8a2f2b;--quote:#6b7280}
@media (prefers-color-scheme: dark){:root{--bg:#141518;--fg:#d6d7da;--muted:#9a9da5;
--accent:#e2a29e;--card:#1c1e22;--border:#2c2f35;--code:#23262b;--th:#23262b;
--a:#e2a29e;--quote:#a6a9b1}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif}
main{max-width:46rem;margin:0 auto;padding:1.2rem 1.1rem 4rem}
header.site{border-bottom:1px solid var(--border);margin-bottom:2rem;padding-bottom:1rem}
header.site h1{font-size:1.35rem;margin:0 0 .2rem}
header.site h1 a{color:inherit;text-decoration:none}
header.site p{margin:0;color:var(--muted);font-size:.95rem}
h1,h2,h3,h4{line-height:1.3;font-weight:650}
h1{font-size:1.7rem;margin:1.6rem 0 .8rem}
h2{font-size:1.25rem;margin:2.2rem 0 .8rem;padding-top:.6rem;border-top:1px solid var(--border)}
h3{font-size:1.05rem;margin:1.4rem 0 .5rem}
a{color:var(--a)}
hr{border:0;border-top:1px solid var(--border);margin:2rem 0}
blockquote{margin:1rem 0;padding:.6rem 1rem;border-left:3px solid var(--accent);background:var(--card);border-radius:0 .4rem .4rem 0;color:var(--quote)}
blockquote p{margin:.2rem 0}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.92rem}
th,td{border:1px solid var(--border);padding:.45rem .6rem;text-align:left;vertical-align:top}
th{background:var(--th)}
code{background:var(--code);border-radius:.25rem;padding:.08rem .3rem;font-size:.88em;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre{background:var(--code);padding:.8rem;border-radius:.4rem;overflow-x:auto}
pre code{background:none;padding:0}
.toplist{list-style:none;margin:1rem 0;padding:0}
.toplist li{background:var(--card);border:1px solid var(--border);border-radius:.5rem;padding:.7rem .9rem;margin:.5rem 0}
.toplist .repo{font-weight:650}
.toplist .facts{color:var(--muted);font-size:.9rem;margin-top:.15rem}
.badge{display:inline-block;font-size:.78rem;border:1px solid var(--border);border-radius:1rem;padding:.02rem .55rem;margin-left:.35rem;color:var(--muted);white-space:nowrap}
.score{color:var(--accent);font-weight:650}
.archive{list-style:none;padding:0}
.archive li{border:1px solid var(--border);border-radius:.5rem;background:var(--card);padding:.8rem 1rem;margin:.5rem 0}
.archive a.week{font-weight:650;font-size:1.05rem}
.meta{color:var(--muted);font-size:.9rem}
footer.site{border-top:1px solid var(--border);margin-top:3rem;padding-top:1rem;color:var(--muted);font-size:.85rem}
"""


def shell(title, desc, url, body, extra_head=""):
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#faf9f7">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#141518">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
%s<link rel="alternate" type="application/atom+xml" title="%s — weekly issues" href="feed.xml">
<style>%s</style>
</head>
<body>
<main>
<header class="site"><h1><a href="index.html">🌏 %s</a></h1><p>%s · <a href="feed.xml">Atom feed</a></p></header>
%s
<footer class="site">Digest by the private <a href="https://github.com/Thysrael/Horizon" rel="noopener">repo-radar</a> (built on Thysrael/Horizon, MIT). Scores are LLM-assisted editorial judgment, not investment advice. Facts are public repo data; commentary and translations are original.</footer>
</main>
</body>
</html>""" % (
        esc(title), esc_attr(desc), esc_attr(url),
        esc_attr(title), esc_attr(desc), esc_attr(url),
        extra_head, SITE_TITLE, CSS,
        SITE_TITLE, SITE_TAGLINE, body,
    )


def week_span(week):
    """'2026-W41' -> 'Oct 5 – Oct 11, 2026' (Mon–Sun, ISO week)."""
    m = re.match(r"(\d{4})-W(\d{2})$", week or "")
    if not m:
        return ""
    year, wk = int(m.group(1)), int(m.group(2))
    try:
        monday = date.fromisocalendar(year, wk, 1)
    except ValueError:
        return ""
    sunday = date.fromisocalendar(year, wk, 7)
    fmt = lambda d: d.strftime("%b %-d") if hasattr(d, "strftime") and sys.platform != "win32" else d.strftime("%b %d")
    return "%s – %s, %d" % (fmt(monday), fmt(sunday), year)


def toplist_html(meta, page=""):
    items = []
    for r in meta.get("repos", []):
        facts = []
        if r.license:
            facts.append("license: %s" % esc(r.license))
        if r.fit:
            facts.append("stack fit: %s" % esc(r.fit))
        fact_html = ' · '.join(facts)
        score = '<span class="score">⭐ %s/10</span> ' % esc(r.score) if r.score else ""
        what = esc(r.what)
        if len(what) > 220:
            what = what[:217].rsplit(" ", 1)[0] + "…"
        items.append(
            '<li><span class="repo"><a href="%s" rel="noopener">%s</a></span> '
            '<span class="badge">#%d</span>%s<br><span class="facts">%s%s</span> '
            '<a class="facts" href="%s#%s">details ↓</a></li>' % (
                esc_attr(r.url), esc(r.name), r.rank, score, what + (" · " if fact_html else ""), fact_html,
                esc_attr(page), esc_attr(r.anchor or slugify_name(r.name)),
            )
        )
    return '<h2 id="top">Top of the week</h2><ol class="toplist">%s</ol>' % "".join(items)


def slugify_name(name):
    return re.sub(r"[^\w-]", "", name.lower().replace("/", "-"))


def issue_updated(week, md):
    """RFC 3339 timestamp for an issue: digest 'Generated …' line if present,
    else the ISO-week Monday 00:00Z."""
    m = GENERATED_RE.search(md)
    if m:
        return "%sT%s:00Z" % (m.group(1), m.group(2))
    w = re.match(r"(\d{4})-W(\d{2})$", week or "")
    if w:
        try:
            return date.fromisocalendar(int(w.group(1)), int(w.group(2)), 1).strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            pass
    return "1970-01-01T00:00:00Z"


def feed_page(issues):
    """Atom 1.0 feed, one entry per issue, newest first.
    issues: list of (week, meta, md) as produced by build()."""
    entries = []
    for week, meta, md in issues:
        url = "%s/%s.html" % (SITE_URL, week)
        title = meta.get("title") or ("%s — %s" % (week, SITE_TITLE))
        summary = meta.get("pulse") or meta.get("stats") or SITE_TAGLINE_PLAIN
        summary = re.sub(r"`([^`]+)`", r"\1", summary)
        summary = strip_md_links_keep_text(re.sub(r"\*\*([^*]+)\*\*", r"\1", summary))
        entries.append(
            "  <entry>\n"
            "    <title>%s</title>\n"
            '    <link href="%s" rel="alternate"/>\n'
            "    <id>%s</id>\n"
            "    <updated>%s</updated>\n"
            '    <summary type="text">%s</summary>\n'
            "  </entry>" % (
                esc_attr(title), esc_attr(url), esc_attr(url), issue_updated(week, md), esc_attr(summary),
            )
        )
    feed_updated = max(issue_updated(w, md) for w, _m, md in issues) if issues else "1970-01-01T00:00:00Z"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        "  <title>%s</title>\n"
        "  <subtitle>%s</subtitle>\n"
        "  <id>%s/</id>\n"
        '  <link href="%s/" rel="alternate" type="text/html"/>\n'
        '  <link href="%s/feed.xml" rel="self" type="application/atom+xml"/>\n'
        "  <updated>%s</updated>\n"
        "%s\n"
        "</feed>\n"
    ) % (esc_attr(SITE_TITLE), esc_attr(SITE_TAGLINE_PLAIN), esc_attr(SITE_URL),
         esc_attr(SITE_URL), esc_attr(SITE_URL), feed_updated, "\n".join(entries))


# ------------------------------------------------------------------ pages

def issue_page(md, week):
    meta = parse_digest(md)
    span = week_span(week)
    title = "%s — %s" % (week, SITE_TITLE) if week else meta.get("title", SITE_TITLE)
    desc = meta.get("pulse") or meta.get("stats") or SITE_TAGLINE
    if len(desc) > 300:
        desc = desc[:297].rsplit(" ", 1)[0] + "…"

    head = ["<h1>%s</h1>" % esc(meta.get("title", title))]
    if span:
        head.append('<p class="meta">Week of %s · <a href="%s.html">Permalink</a></p>' % (esc(span), esc_attr(week)))
    if meta.get("stats"):
        head.append("<blockquote><p>%s</p></blockquote>" % inline(strip_md_links_keep_text(meta["stats"])))
    if meta.get("pulse"):
        head.append("<h2>This week&rsquo;s pulse</h2><p>%s</p>" % inline(meta["pulse"]))

    # Replace the digest's own truncated "Featured repos" summary block and
    # every head-extracted element (title, stats, pulse) with our head + top
    # list, then render the remaining body after it. The strip must stop at
    # the radar's *Week over week* diff block (radar PRs #6/#7) which sits
    # between the featured list and the --- separator, so it stays on the page.
    wow_stop = r"\n\*\*(?:Week over week|Nedelja prema nedelji)\*\*"
    body_md = re.sub(r"\*\*Featured repos\*\*.*?(?=\n---|" + wow_stop + ")", "", md, count=1, flags=re.S)
    body_md = re.sub(r"^# .+\n?", "", body_md, count=1, flags=re.M)
    if meta.get("stats"):
        body_md = re.sub(r"^> .+\n?", "", body_md, count=1, flags=re.M)
    if meta.get("pulse"):
        body_md = re.sub(r"\*\*This week's pulse:\*\*.*?(?=\n\n|\n---)", "", body_md, count=1, flags=re.S)
    body_html = md_to_html(body_md)
    body = "\n".join(head) + toplist_html(meta) + body_html
    url = "%s/%s.html" % (SITE_URL, week) if week else SITE_URL
    return shell(title, desc, url, body), meta


def strip_md_links_keep_text(text):
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)


def index_page(issues):
    """issues: list of (week, meta, md) sorted newest first."""
    latest_week, latest_meta, _ = issues[0]
    parts = []
    parts.append("<h1>The weekly digest of repos the West misses</h1>")
    parts.append("<p>Trending Chinese/Japanese/Korean GitHub &amp; Gitee repositories, "
                 "translated and scored: what it is, why it matters, license, stack fit. "
                 "Fresh every week; read the <a href=\"%s.html\">latest issue</a>.</p>" % esc_attr(latest_week))
    span = week_span(latest_week)
    parts.append("<h2>Latest — <a href=\"%s.html\">%s</a>%s</h2>" % (
        esc_attr(latest_week), esc(latest_week), (" <span class=\"meta\">(%s)</span>" % esc(span)) if span else ""))
    if latest_meta.get("pulse"):
        parts.append("<p>%s</p>" % inline(latest_meta["pulse"]))
    parts.append(toplist_html(latest_meta, page=latest_week + ".html").replace('id="top"', 'id="latest-top"'))
    parts.append('<p><a href="%s.html">Read the full %s issue →</a></p>' % (esc_attr(latest_week), esc(latest_week)))
    parts.append("<h2>Archive</h2><ul class=\"archive\">")
    for week, meta, _ in issues:
        repos = meta.get("repos", [])
        n = len(repos)
        span = week_span(week)
        parts.append('<li><a class="week" href="%s.html">%s</a> %s<span class="meta"> · %d repo%s featured</span></li>' % (
            esc_attr(week), esc(week),
            ('<span class="meta">(%s)</span>' % esc(span)) if span else "",
            n, "" if n == 1 else "s"))
    parts.append("</ul>")
    parts.append('<p class="meta">New issues land weekly — follow along via the <a href="feed.xml">Atom feed</a>.</p>')
    return shell(SITE_TITLE, SITE_TAGLINE.replace("&amp;", "&"), SITE_URL, "\n".join(parts))


def collect_issues():
    found = []
    for path in sorted(ISSUES.glob("*.md")):
        if not WEEK_RE.match(path.stem):
            print("skipping non-issue file: %s" % path.name, file=sys.stderr)
            continue
        found.append((path.stem, path.read_text(encoding="utf-8")))
    found.sort(key=lambda t: t[0], reverse=True)
    return found


def build(check=False):
    raw = collect_issues()
    if not raw:
        print("no issues found under issues/", file=sys.stderr)
        return 1
    outputs = {}
    metas = []
    for week, md in raw:
        page, meta = issue_page(md, week)
        outputs[week + ".html"] = page
        metas.append((week, meta, md))
    outputs["index.html"] = index_page(metas)
    outputs["feed.xml"] = feed_page(metas)

    stale = []
    for name, content in sorted(outputs.items()):
        target = HERE / name
        if check:
            current = target.read_text(encoding="utf-8") if target.exists() else ""
            if current != content:
                stale.append(name)
        else:
            target.write_text(content, encoding="utf-8")
            print("wrote %s (%d bytes)" % (name, len(content.encode("utf-8"))))
    if check:
        if stale:
            print("stale generated files: %s — run: python build.py" % ", ".join(stale), file=sys.stderr)
            return 1
        print("all %d generated pages up to date" % len(outputs))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify committed HTML matches sources; exit 1 if stale")
    args = ap.parse_args()
    sys.exit(build(check=args.check))


if __name__ == "__main__":
    main()
