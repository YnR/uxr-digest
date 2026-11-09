"""Publish the AI evals resources page as HTML plus feeds.

    python3 reader/evals_resources.py --out _site/evals --base-url https://ynr.github.io/uxr-digest/evals/

The Markdown page at `docs/evals-resources/README.md` stays the one place
resources are edited. This script reads it and writes:

  index.html       the page itself, rendered for GitHub Pages
  feed.xml         RSS 2.0, one item per resource, newest publication first
  feed.json        JSON Feed 1.1, same items, plus a `_evals` object with the
                   structured fields (authors, affiliations as `company`, format, dates, profile
                   links, the entry it is grouped under)
  resources.json   every resource in page order, for scripts

Each entry on the page is a `## N. Title` heading (or `### Na. Related take:
Title` for a piece grouped under an older one), a list of `- **Field:** value`
lines, then sections that open with a bold lead-in such as `**What it adds.**`.
The parser keys on exactly that shape, so keep new entries to it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape as html_escape
from xml.sax.saxutils import escape, quoteattr

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join(REPO_ROOT, "docs", "evals-resources", "README.md")
SOURCE_URL = "https://github.com/YnR/uxr-digest/blob/main/docs/evals-resources/README.md"
FEED_TITLE = "AI Evals Resources"
FEED_DESCRIPTION = ("Curated writing, talks and videos on evaluating AI systems, with what "
                    "each one adds to the conversation about evals.")
JSON_FEED_VERSION = "https://jsonfeed.org/version/1.1"
FORMAT_DOMAIN = "https://github.com/YnR/uxr-digest/tree/main/docs/evals-resources#format"
COMPANY_DOMAIN = "https://github.com/YnR/uxr-digest/tree/main/docs/evals-resources#company"

ENTRY_HEADING = re.compile(r"^(##|###) (\d+[a-z]?)\. (.+)$")
FIELD_LINE = re.compile(r"^- \*\*([^*]+?):\*\*\s*(.*)$")
SECTION_LEAD = re.compile(r"^\*\*([^*]+?)\.\*\*\s*(.*)$", re.S)
# Only a date the Published line leads with counts; a later date is context.
ISO_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
FIELD_KEYS = {
    "link": "url", "author": "authors", "authors": "authors", "speaker": "authors",
    "speakers": "authors", "affiliation(s)": "company", "affiliations": "company",
    "affiliation": "company", "company at publication": "company",
    "find them": "find_them", "format": "format", "published": "published",
}


# --- Markdown (the subset the page uses) ----------------------------------

_INLINE = re.compile(
    r"<(?P<auto>https?://[^>\s]+)>"
    r"|\[(?P<ltext>[^\]]+)\]\((?P<lurl>[^)\s]+)\)"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|(?<![\w*])\*(?P<em>[^*\s][^*]*?)\*(?![\w*])"
    r"|`(?P<code>[^`]+)`",
    re.S,
)


def inline_html(text: str) -> str:
    out, pos = [], 0
    for m in _INLINE.finditer(text):
        out.append(html_escape(text[pos:m.start()], quote=False))
        if m.group("auto"):
            url = m.group("auto")
            out.append(f'<a href="{html_escape(url)}">{html_escape(url, quote=False)}</a>')
        elif m.group("ltext"):
            out.append(f'<a href="{html_escape(m.group("lurl"))}">{inline_html(m.group("ltext"))}</a>')
        elif m.group("bold"):
            out.append(f"<strong>{inline_html(m.group('bold'))}</strong>")
        elif m.group("em"):
            out.append(f"<em>{inline_html(m.group('em'))}</em>")
        else:
            out.append(f"<code>{html_escape(m.group('code'), quote=False)}</code>")
        pos = m.end()
    out.append(html_escape(text[pos:], quote=False))
    return "".join(out)


def plain_text(text: str) -> str:
    def repl(m: re.Match) -> str:
        if m.group("auto"):
            return m.group("auto")
        if m.group("ltext"):
            return plain_text(m.group("ltext"))
        return plain_text(m.group("bold") or m.group("em") or m.group("code") or "")
    return re.sub(r"\s+", " ", _INLINE.sub(repl, text)).strip()


def links_in(text: str) -> list[dict]:
    return [{"label": plain_text(m.group("ltext")), "url": m.group("lurl")}
            for m in _INLINE.finditer(text) if m.group("ltext")]


def heading_anchor(text: str) -> str:
    """The id GitHub gives a heading, so the page's own #links keep working."""
    return re.sub(r"[^\w\- ]", "", plain_text(text).lower()).replace(" ", "-")


def _blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split Markdown lines into (kind, lines) blocks."""
    blocks: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            blocks.append(("heading", [line]))
            i += 1
        elif line.strip() == "---":
            blocks.append(("rule", [line]))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            blocks.append(("table", rows))
        elif re.match(r"^(- |\d+\. )", line):
            items: list[str] = []
            ordered = not line.startswith("- ")
            while i < len(lines) and (re.match(r"^(- |\d+\. )", lines[i])
                                      or (lines[i].startswith("  ") and items)):
                if re.match(r"^(- |\d+\. )", lines[i]):
                    items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            blocks.append(("ol" if ordered else "ul", items))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(
                    r"^(#|\||- |\d+\. |---\s*$)", lines[i]):
                para.append(lines[i].strip())
                i += 1
            blocks.append(("p", [" ".join(para)]))
    return blocks


def _meta_html(items: list[str]) -> str:
    """An entry's `- **Field:** value` list as a metadata card: the link becomes
    a button naming its site, the rest a label/value grid."""
    link, rows = "", []
    for item in items:
        m = FIELD_LINE.match("- " + item)
        label, value = m.group(1), m.group(2).strip()
        url = re.search(r"<(https?://[^>]+)>", value)
        if label.lower() == "link" and url:
            host = urlparse(url.group(1)).netloc.removeprefix("www.")
            link = (f'<a class="open" href="{html_escape(url.group(1))}">'
                    f'Open on {html_escape(host)} <span aria-hidden="true">↗</span></a>')
            continue
        rows.append(f"<dt>{html_escape(label)}</dt><dd>{inline_html(value)}</dd>")
    return f'<div class="meta"><dl>{"".join(rows)}</dl>{link}</div>'


SUB_ID = re.compile(r"^\d+[a-z]$")


def markdown_html(text: str) -> str:
    """Render the page. A related take (`### Na.`) and everything under it, up to
    the next heading or rule, is wrapped in `<section class="related">` so it
    reads as nested under its canonical entry."""
    out = []
    in_related = False

    def close_related() -> None:
        nonlocal in_related
        if in_related:
            out.append("</section>")
            in_related = False

    for kind, lines in _blocks(text.splitlines()):
        if kind == "heading":
            level = len(lines[0]) - len(lines[0].lstrip("#"))
            title = lines[0][level:].strip()
            close_related()
            heading = f'<h{level} id="{heading_anchor(title)}">{inline_html(title)}</h{level}>'
            if level == 3 and ENTRY_HEADING.match(lines[0]):
                m = re.match(r"^(\d+[a-z]?)\. (?:Related take:\s*)?(.+)$", title)
                heading = (f'<h3 id="{heading_anchor(title)}"><span class="label">Related take '
                           f'{html_escape(m.group(1))}</span>{inline_html(m.group(2))}</h3>')
                out.append('<section class="related">')
                in_related = True
            out.append(heading)
        elif kind == "rule":
            close_related()
            out.append("<hr>")
        elif kind == "table":
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in lines]
            body = [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            head = "".join(f"<th>{inline_html(c)}</th>" for c in rows[0])
            trs = "".join(
                ('<tr class="sub">' if r and SUB_ID.match(r[0]) else "<tr>")
                + "".join(f"<td>{inline_html(c.replace('↳', '').strip())}</td>" for c in r)
                + "</tr>" for r in body)
            out.append(f'<div class="table"><table><thead><tr>{head}</tr></thead>'
                       f"<tbody>{trs}</tbody></table></div>")
        elif kind == "ul" and lines and all(FIELD_LINE.match("- " + item) for item in lines):
            out.append(_meta_html(lines))
        elif kind in ("ul", "ol"):
            items = "".join(f"<li>{inline_html(item)}</li>" for item in lines)
            out.append(f"<{kind}>{items}</{kind}>")
        else:
            out.append(f"<p>{inline_html(lines[0])}</p>")
    close_related()
    return "\n".join(out)


# --- Entries ---------------------------------------------------------------

def parse_resources(markdown: str) -> list[dict]:
    """Every resource on the page, in page order."""
    lines = markdown.splitlines()
    starts = [i for i, line in enumerate(lines) if ENTRY_HEADING.match(line)]
    entries = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        body = lines[start + 1:end]
        # An entry stops at the rule before the next entry or the closing section.
        for j, line in enumerate(body):
            if line.strip() == "---" or (line.startswith("## ") and not ENTRY_HEADING.match(line)):
                body = body[:j]
                break
        level, number, title = ENTRY_HEADING.match(lines[start]).groups()
        related_to = None
        if level == "###":
            title = re.sub(r"^Related take:\s*", "", title)
            related_to = re.match(r"\d+", number).group(0)
        entries.append(_entry(number, title, lines[start], related_to, body))
    return entries


def _entry(number: str, title: str, heading: str, related_to: str | None,
           body: list[str]) -> dict:
    fields: dict[str, str] = {}
    sections: list[dict] = []
    for kind, block in _blocks(body):
        if kind == "ul" and not sections:
            for item in block:
                m = FIELD_LINE.match("- " + item)
                if m and m.group(1).lower() in FIELD_KEYS:
                    fields[FIELD_KEYS[m.group(1).lower()]] = m.group(2).strip()
            continue
        if kind == "p":
            lead = SECTION_LEAD.match(block[0])
            if lead:
                sections.append({"label": lead.group(1), "markdown": [lead.group(2)]})
                continue
        if sections:
            if kind == "p":
                sections[-1]["markdown"].append(block[0])
            elif kind in ("ul", "ol"):
                marker = "- " if kind == "ul" else "1. "
                sections[-1]["markdown"].append("\n".join(marker + item for item in block))

    url = fields.get("url", "")
    auto = re.search(r"<(https?://[^>]+)>", url) or re.search(r"\((https?://[^)]+)\)", url)
    published = fields.get("published", "")
    date = ISO_DATE.match(plain_text(published))
    for s in sections:
        s["markdown"] = "\n\n".join(s["markdown"])
        s["text"] = plain_text(s["markdown"])
        s["html"] = markdown_html(s["markdown"])
    adds = next((s for s in sections if s["label"].lower() == "what it adds"), None)
    differs = next((s for s in sections if s["label"].lower() == "how it differs"), None)
    summary = adds or differs or (sections[0] if sections else None)
    return {
        "id": number,
        "title": plain_text(title),
        "anchor": heading_anchor(heading.lstrip("#").strip()),
        "url": auto.group(1) if auto else None,
        "related_to": related_to,
        "authors": plain_text(fields.get("authors", "")) or None,
        "company": plain_text(fields.get("company", "")) or None,
        "format": plain_text(fields.get("format", "")) or None,
        "kind": (re.match(r"\w+", plain_text(fields.get("format", ""))) or [None])[0],
        "published": plain_text(published) or None,
        "published_iso": date.group(1) if date else None,
        "profiles": links_in(fields.get("find_them", "")),
        "summary": summary["text"] if summary else "",
        "sections": [{"label": s["label"], "text": s["text"], "html": s["html"]}
                     for s in sections],
    }


def feed_order(entries: list[dict]) -> list[dict]:
    """Newest publication first; undated pieces after dated ones, in page order."""
    dated = sorted((e for e in entries if e["published_iso"]),
                   key=lambda e: e["published_iso"], reverse=True)
    return dated + [e for e in entries if not e["published_iso"]]


def _published_datetime(day: str) -> datetime:
    # Noon UTC keeps the calendar date the same wherever the reader is.
    return datetime.strptime(day, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)


def _item_html(e: dict, by_id: dict) -> str:
    parts = []
    facts = [("By", e["authors"]), ("Affiliation(s)", e["company"]),
             ("Format", e["format"]), ("Published", e["published"])]
    if e["related_to"] and e["related_to"] in by_id:
        facts.append(("Grouped under", by_id[e["related_to"]]["title"]))
    parts.append("<ul>" + "".join(f"<li><strong>{html_escape(k)}:</strong> {html_escape(v)}</li>"
                                  for k, v in facts if v) + "</ul>")
    if e["profiles"]:
        parts.append("<p><strong>Find them:</strong> " + " · ".join(
            f'<a href="{html_escape(p["url"])}">{html_escape(p["label"])}</a>'
            for p in e["profiles"]) + "</p>")
    for s in e["sections"]:
        parts.append(f"<h4>{html_escape(s['label'])}</h4>{s['html']}")
    return "".join(parts)


def to_rss(entries: list[dict], base_url: str, built: datetime) -> str:
    by_id = {e["id"]: e for e in entries}
    home = base_url or SOURCE_URL
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(home)}</link>",
        f"<description>{escape(FEED_DESCRIPTION)}</description>",
        "<language>en</language>",
        f"<lastBuildDate>{format_datetime(built)}</lastBuildDate>",
        f'<atom:link href={quoteattr(base_url + "feed.xml")} rel="self" type="application/rss+xml"/>',
    ]
    for e in feed_order(entries):
        out.append("<item>")
        out.append(f"<title>{escape(e['title'])}</title>")
        if e["url"]:
            out.append(f"<link>{escape(e['url'])}</link>")
        out.append(f'<guid isPermaLink="false">uxr-evals:{escape(e["url"] or e["id"])}</guid>')
        if e["published_iso"]:
            out.append(f"<pubDate>{format_datetime(_published_datetime(e['published_iso']))}</pubDate>")
        out.append(f"<description>{escape(e['summary'])}</description>")
        html = _item_html(e, by_id).replace("]]>", "]]&gt;")
        out.append(f"<content:encoded><![CDATA[{html}]]></content:encoded>")
        if e["authors"]:
            out.append(f"<dc:creator>{escape(e['authors'])}</dc:creator>")
        if e["kind"]:
            out.append(f"<category domain={quoteattr(FORMAT_DOMAIN)}>{escape(e['kind'])}</category>")
        if e["company"]:
            out.append(f"<category domain={quoteattr(COMPANY_DOMAIN)}>{escape(e['company'])}</category>")
        out.append("</item>")
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)


def _structured(e: dict) -> dict:
    return {k: e[k] for k in ("id", "related_to", "authors", "company", "format", "kind",
                              "published", "published_iso", "profiles")} | {
        "sections": [{"label": s["label"], "text": s["text"]} for s in e["sections"]]}


def to_json_feed(entries: list[dict], base_url: str) -> dict:
    by_id = {e["id"]: e for e in entries}
    items = []
    for e in feed_order(entries):
        item = {
            "id": f"uxr-evals:{e['url'] or e['id']}",
            "url": e["url"],
            "title": e["title"],
            "summary": e["summary"],
            "content_text": "\n\n".join(f"{s['label']}. {s['text']}" for s in e["sections"]),
            "content_html": _item_html(e, by_id),
            "_evals": _structured(e),
        }
        if base_url:
            item["external_url"] = base_url + "#" + e["anchor"]
        if e["published_iso"]:
            item["date_published"] = _published_datetime(e["published_iso"]).isoformat()
        if e["authors"]:
            item["authors"] = [{"name": e["authors"]}]
        tags = [t for t in (e["kind"], e["company"]) if t]
        if tags:
            item["tags"] = tags
        items.append(item)
    feed = {"version": JSON_FEED_VERSION, "title": FEED_TITLE,
            "description": FEED_DESCRIPTION, "home_page_url": base_url or SOURCE_URL,
            "language": "en", "items": items}
    if base_url:
        feed["feed_url"] = base_url + "feed.json"
    return feed


def to_html(markdown: str, base_url: str) -> str:
    body = markdown_html(markdown)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{FEED_TITLE}</title>
<meta name="description" content="{html_escape(FEED_DESCRIPTION)}">
<link rel="alternate" type="application/rss+xml" title="{FEED_TITLE} (RSS)" href="{base_url}feed.xml">
<link rel="alternate" type="application/feed+json" title="{FEED_TITLE} (JSON Feed)" href="{base_url}feed.json">
<style>
:root {{ --bg:#fbfaf7; --fg:#1f2328; --muted:#5b6370; --line:#e3e0d8; --accent:#2f5bd3; --card:#ffffff; --sub:#f1f4fb; }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{ --bg:#15171a; --fg:#e6e8eb; --muted:#9aa3ae; --line:#2c3036; --accent:#8fb0ff; --card:#1c1f23; --sub:#1d2433; }}
}}
:root[data-theme="dark"] {{ --bg:#15171a; --fg:#e6e8eb; --muted:#9aa3ae; --line:#2c3036; --accent:#8fb0ff; --card:#1c1f23; --sub:#1d2433; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:46rem; margin:0 auto; padding:2rem 16px 4rem; }}
h1 {{ font-size:2rem; line-height:1.2; margin:0 0 .5rem; }}
h2 {{ font-size:1.35rem; line-height:1.3; margin:2.5rem 0 .75rem; }}
h3 {{ font-size:1.1rem; line-height:1.3; margin:2rem 0 .75rem; padding-left:.75rem; border-left:3px solid var(--line); }}
a {{ color:var(--accent); overflow-wrap:anywhere; }}
hr {{ border:0; border-top:1px solid var(--line); margin:2.5rem 0; }}
ul, ol {{ padding-left:1.25rem; }}
li {{ margin:.25rem 0; }}
code {{ font-size:.9em; background:var(--card); border:1px solid var(--line); border-radius:4px; padding:0 .25rem; }}
.subscribe {{ color:var(--muted); font-size:.95rem; border:1px solid var(--line); background:var(--card); border-radius:8px; padding:.6rem .9rem; }}
.table {{ overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:var(--card); }}
table {{ border-collapse:collapse; width:100%; min-width:40rem; font-size:.9rem; }}
th, td {{ text-align:left; vertical-align:top; padding:.5rem .6rem; border-bottom:1px solid var(--line); }}
tr:last-child td {{ border-bottom:0; }}
tr.sub td {{ background:var(--sub); font-size:.85rem; color:var(--muted); }}
tr.sub td:first-child {{ box-shadow:inset 3px 0 0 var(--accent); padding-left:1rem; }}
tr.sub td:nth-child(2) {{ padding-left:1.5rem; position:relative; }}
tr.sub td:nth-child(2)::before {{ content:"↳"; position:absolute; left:.5rem; color:var(--accent); }}
tr.sub a {{ color:var(--accent); }}
section.related {{ margin:2rem 0 0 .25rem; padding:.25rem 1.1rem 1rem; border-left:3px solid var(--accent); background:var(--sub); border-radius:0 8px 8px 0; }}
section.related h3 {{ margin-top:1rem; padding-left:0; border-left:0; }}
section.related + section.related {{ margin-top:1.25rem; }}
.meta {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem; margin:1rem 0 1.25rem; }}
.meta dl {{ display:grid; grid-template-columns:max-content 1fr; gap:.45rem 1rem; margin:0; }}
.meta dt {{ font-size:.72rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); padding-top:.2rem; }}
.meta dd {{ margin:0; }}
.meta .open {{ display:inline-block; margin-top:.9rem; padding:.4rem .8rem; border:1px solid var(--accent); border-radius:999px; text-decoration:none; font-size:.9rem; font-weight:600; }}
.meta .open:hover {{ background:var(--accent); color:var(--card); }}
section.related .meta {{ background:var(--bg); }}
@media (max-width: 520px) {{ .meta dl {{ grid-template-columns:1fr; gap:.1rem; }} .meta dd {{ margin-bottom:.5rem; }} }}
h3 .label {{ display:block; font-size:.75rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); margin-bottom:.2rem; }}
</style>
</head>
<body>
<main>
<p class="subscribe">Get this list programmatically: <a href="{base_url}feed.xml">RSS</a> · <a href="{base_url}feed.json">JSON Feed</a> · <a href="{base_url}resources.json">resources.json</a> · <a href="{SOURCE_URL}">edit on GitHub</a></p>
{body}
</main>
</body>
</html>
"""


def build(source: str, out_dir: str, base_url: str, built: datetime | None = None) -> list[dict]:
    base_url = base_url.rstrip("/") + "/" if base_url else ""
    built = built or datetime.now(timezone.utc).replace(microsecond=0)
    with open(source, encoding="utf-8") as handle:
        markdown = handle.read()
    entries = parse_resources(markdown)
    os.makedirs(out_dir, exist_ok=True)

    def write(name: str, text: str) -> None:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    write("index.html", to_html(markdown, base_url))
    write("feed.xml", to_rss(entries, base_url, built))
    write("feed.json", json.dumps(to_json_feed(entries, base_url), ensure_ascii=False, indent=1))
    write("resources.json", json.dumps(
        {"title": FEED_TITLE, "built": built.isoformat(), "source": SOURCE_URL,
         "resources": [_structured(e) | {"title": e["title"], "url": e["url"],
                                         "summary": e["summary"]} for e in entries]},
        ensure_ascii=False, indent=1))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the AI evals resources page and feeds.")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--out", default="_site/evals")
    parser.add_argument("--base-url", default="",
                        help="where the page will be served, e.g. https://ynr.github.io/uxr-digest/evals/")
    args = parser.parse_args()
    entries = build(args.source, args.out, args.base_url)
    print(f"Wrote the evals page and feeds ({len(entries)} resources) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
