"""Publish the digest as feeds other clients can subscribe to.

    python3 reader/feeds.py --out _site --base-url https://ynr.github.io/uxr-digest/

Every article becomes one feed item carrying the digest's own summary. The same
items are written two ways, because clients differ:

  * RSS 2.0 (`.xml`) for feed readers. The summary is the item description,
    and the focus area and source are `<category>` elements with a `domain`
    saying which is which, so a reader can group or filter on either.
  * JSON Feed 1.1 (`.json`) for anything that would rather not parse XML. Same
    items, plus a `_uxr` object with the structured fields (focus area, source
    and its `sources.json` id and homepage, author, publication date, digest
    date) so nothing has to be scraped back out of tags.

The stream is organised three ways, each as its own feed:

  feed.xml / feed.json                    everything, newest first
  topics/<slug>.xml|json                  one per focus area
  sources/<slug>.xml|json                 one per publication
  months/<YYYY-MM>.xml|json               the archive, one per digest month

plus `index.json` (a catalogue of every feed), `feeds.opml` (import all of them
into a reader at once) and `digest.json` (the full parse, for scripts).

An item's date is the day it entered the digest, not the day the article was
published. That is the date the dedup rule keys on, every item has one, and it
keeps the stream in the order it was curated. The article's own publication
date, where the digest gives one, travels in `_uxr.published`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from digest_parser import default_posts_dir, load_digest  # noqa: E402
from search import matches_filters  # noqa: E402

FEED_TITLE = "UX Research Digest"
FEED_DESCRIPTION = ("Curated UX research news in three focus areas: AI in the research "
                    "practice, research for AI-powered products, and the UXR job market.")
HOME_URL = "https://github.com/YnR/uxr-digest"
TOPIC_DOMAIN = "https://github.com/YnR/uxr-digest#focus-area"
SOURCE_DOMAIN = "https://github.com/YnR/uxr-digest#source"
JSON_FEED_VERSION = "https://jsonfeed.org/version/1.1"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "untitled"


def _digest_datetime(day: str) -> datetime:
    # The digest is a daily post with no time of day; noon UTC keeps the
    # calendar date the same in every timezone a reader is likely to use.
    return datetime.strptime(day, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)


def stream(articles: list[dict], *, focus_area: str | None = None,
           source: str | None = None, since: str | None = None,
           until: str | None = None, month: str | None = None) -> list[dict]:
    """Articles in curation order, newest first, with the reader's own filters.

    `since`/`until` mean what they mean in the reader (publication date, falling
    back to the digest date). `month` is the digest month the archive keys on.
    Source is matched exactly here: a feed per publication should not pick up a
    neighbour whose name merely contains it.
    """
    rows = [a for a in articles
            if matches_filters(a, focus_area, None, since, until)
            and (not source or a["source"].lower() == source.lower())
            and (not month or a["first_seen"].startswith(month))]
    rows.sort(key=lambda a: (a["first_seen"], a.get("published_iso") or ""), reverse=True)
    return rows


def _body_text(article: dict) -> str:
    parts = [article["summary"]]
    if article.get("note"):
        parts.append(f"({article['note']})")
    return "\n\n".join(p for p in parts if p)


def _body_html(article: dict) -> str:
    paragraphs = [f"<p>{escape(p)}</p>" for p in _body_text(article).split("\n\n")]
    if article.get("url"):
        paragraphs.append(f'<p><a href={quoteattr(article["url"])}>'
                          f'Read the article on {escape(article["source"])}</a></p>')
    return "".join(paragraphs)


def _feed_meta(title: str, description: str, base_url: str, path: str,
               home: str | None = None) -> dict:
    return {"title": title, "description": description,
            "url": base_url + path, "home": home or HOME_URL}


def to_rss(articles: list[dict], meta: dict, built: datetime) -> str:
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        "<channel>",
        f"<title>{escape(meta['title'])}</title>",
        f"<link>{escape(meta['home'])}</link>",
        f"<description>{escape(meta['description'])}</description>",
        "<language>en</language>",
        f"<lastBuildDate>{format_datetime(built)}</lastBuildDate>",
        f'<atom:link href={quoteattr(meta["url"] + ".xml")} rel="self" type="application/rss+xml"/>',
    ]
    for a in articles:
        out.append("<item>")
        out.append(f"<title>{escape(a['title'])}</title>")
        if a.get("url"):
            out.append(f"<link>{escape(a['url'])}</link>")
        out.append(f'<guid isPermaLink="false">uxr-digest:{a["id"]}</guid>')
        out.append(f"<pubDate>{format_datetime(_digest_datetime(a['first_seen']))}</pubDate>")
        out.append(f"<description>{escape(_body_text(a))}</description>")
        out.append(f"<content:encoded><![CDATA[{_body_html(a).replace(']]>', ']]&gt;')}]]></content:encoded>")
        if a.get("author"):
            out.append(f"<dc:creator>{escape(a['author'])}</dc:creator>")
        out.append(f"<category domain={quoteattr(TOPIC_DOMAIN)}>{escape(a['focus_area'])}</category>")
        out.append(f"<category domain={quoteattr(SOURCE_DOMAIN)}>{escape(a['source'])}</category>")
        out.append("</item>")
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)


def to_json_feed(articles: list[dict], meta: dict) -> dict:
    items = []
    for a in articles:
        item = {
            "id": f"uxr-digest:{a['id']}",
            "title": a["title"],
            "summary": a["summary"],
            "content_text": _body_text(a),
            "content_html": _body_html(a),
            "date_published": _digest_datetime(a["first_seen"]).isoformat(),
            "tags": [a["focus_area"], a["source"]],
            "authors": [{"name": a["author"]} if a.get("author")
                        else {k: v for k, v in (("name", a["source"]),
                                                ("url", a.get("source_url"))) if v}],
            "_uxr": {
                "focus_area": a["focus_area"],
                "source": a["source"],
                "source_id": a.get("source_id"),
                "source_url": a.get("source_url"),
                "author": a.get("author"),
                "published": a.get("published_iso"),
                "published_raw": a.get("published_raw"),
                "digest_date": a["first_seen"],
                "digest_file": a["first_seen_file"],
                "note": a.get("note"),
            },
        }
        if a.get("url"):
            item["url"] = item["external_url"] = a["url"]
        items.append(item)
    return {
        "version": JSON_FEED_VERSION,
        "title": meta["title"],
        "description": meta["description"],
        "home_page_url": meta["home"],
        "feed_url": meta["url"] + ".json",
        "language": "en",
        "items": items,
    }


def feed_plan(data: dict) -> list[dict]:
    """Every feed to build: its path (without extension), title and filter."""
    articles = data["articles"]
    plan = [{"path": "feed", "kind": "all", "title": FEED_TITLE,
             "description": FEED_DESCRIPTION, "filter": {}}]
    for area in data["focus_areas"]:
        plan.append({"path": f"topics/{slugify(area)}", "kind": "topic", "name": area,
                     "title": f"{FEED_TITLE}: {area}",
                     "description": f"Digest entries in the focus area “{area}”.",
                     "filter": {"focus_area": area}})
    homepages = {a["source"]: a.get("source_url") for a in articles if a.get("source_url")}
    for source in data["sources"]:
        plan.append({"path": f"sources/{slugify(source)}", "kind": "source", "name": source,
                     "home": homepages.get(source),
                     "title": f"{FEED_TITLE}: {source}",
                     "description": f"Digest entries from {source}.",
                     "filter": {"source": source}})
    for month in sorted({a["first_seen"][:7] for a in articles}, reverse=True):
        plan.append({"path": f"months/{month}", "kind": "month", "name": month,
                     "title": f"{FEED_TITLE}: {month}",
                     "description": f"Digest entries curated in {month}.",
                     "filter": {"month": month}})
    return plan


def to_opml(plan: list[dict], base_url: str) -> str:
    groups = {"all": "Everything", "topic": "By focus area", "source": "By source",
              "month": "By month"}
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<opml version="2.0">',
           f"<head><title>{escape(FEED_TITLE)}</title></head>", "<body>"]
    for kind, label in groups.items():
        out.append(f"<outline text={quoteattr(label)}>")
        for feed in (f for f in plan if f["kind"] == kind):
            out.append(f'<outline type="rss" text={quoteattr(feed["title"])} '
                       f'xmlUrl={quoteattr(base_url + feed["path"] + ".xml")} '
                       f'htmlUrl={quoteattr(feed.get("home") or HOME_URL)}/>')
        out.append("</outline>")
    out += ["</body>", "</opml>", ""]
    return "\n".join(out)


def build(posts_dir: str, out_dir: str, base_url: str,
          built: datetime | None = None) -> dict:
    """Write every feed under `out_dir` and return the catalogue."""
    base_url = base_url.rstrip("/") + "/" if base_url else ""
    built = built or datetime.now(timezone.utc).replace(microsecond=0)
    data = load_digest(posts_dir)
    plan = feed_plan(data)

    def write(rel: str, text: str) -> None:
        full = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(text)

    catalogue = []
    for feed in plan:
        rows = stream(data["articles"], **feed["filter"])
        meta = _feed_meta(feed["title"], feed["description"], base_url, feed["path"],
                          feed.get("home"))
        write(feed["path"] + ".xml", to_rss(rows, meta, built))
        write(feed["path"] + ".json",
              json.dumps(to_json_feed(rows, meta), ensure_ascii=False, indent=1))
        catalogue.append({"kind": feed["kind"], "name": feed.get("name"),
                          "title": feed["title"], "items": len(rows),
                          "rss": base_url + feed["path"] + ".xml",
                          "json": base_url + feed["path"] + ".json"})

    index = {"title": FEED_TITLE, "built": built.isoformat(), "stats": data["stats"],
             "feeds": catalogue}
    write("index.json", json.dumps(index, ensure_ascii=False, indent=1))
    write("feeds.opml", to_opml(plan, base_url))
    write("digest.json", json.dumps(data, ensure_ascii=False))
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RSS and JSON feeds from the digest.")
    parser.add_argument("--posts", default=default_posts_dir())
    parser.add_argument("--out", default="_site")
    parser.add_argument("--base-url", default="",
                        help="where the feeds will be served, e.g. https://ynr.github.io/uxr-digest/")
    args = parser.parse_args()
    index = build(os.path.abspath(args.posts), args.out, args.base_url)
    print(f"Wrote {len(index['feeds'])} feeds ({index['stats']['articles']} articles) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
