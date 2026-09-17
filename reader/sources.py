"""Fetching an article's own page, on demand.

The repo stores the digest's summaries and nothing else, by design. A summary
is one paragraph of the digest author's framing, so questions about specifics
— a sample size, a method, what the article actually recommends — cannot be
answered from it. This module fetches one article's page when a question needs
it, caches the text outside version control, and hands it to the answering
layer as grounding.

Deliberate limits:
  * one article at a time, never a sweep of the whole collection;
  * robots.txt is honoured;
  * fetched text is cached under .cache/ and is never written into posts/ or
    committed, so the repo stays summaries-only.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from urllib import robotparser

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.environ.get("UXR_CACHE_DIR",
                           os.path.join(REPO_ROOT, ".cache", "source-pages"))
USER_AGENT = ("uxr-digest-reader/0.1 (personal local reader; "
              "+https://github.com/YnR/uxr-digest)")
TIMEOUT = 20
MAX_BYTES = 2_000_000
CACHE_TTL = 30 * 24 * 3600      # a published article does not change; refresh monthly
FAILURE_TTL = 10 * 60           # a failure is often transient — do not sit on it for a month
MIN_USABLE_CHARS = 600          # below this it is a paywall, a consent wall or a JS shell

_DROP = re.compile(
    r"(?is)<(script|style|noscript|nav|footer|header|aside|form|svg|iframe)[^>]*>.*?</\1>")
_MAIN = re.compile(r"(?is)<(article|main)[^>]*>(?P<body>.*?)</\1>")
_TITLE = re.compile(r"(?is)<title[^>]*>(?P<t>.*?)</title>")
_TAG = re.compile(r"(?s)<[^>]+>")
_BLOCK_END = re.compile(r"(?i)</(p|div|li|h[1-6]|tr|section)>")


@dataclass
class Source:
    url: str
    ok: bool
    text: str = ""
    title: str = ""
    error: str = ""
    fetched_at: float = 0.0
    from_cache: bool = False

    @property
    def usable(self) -> bool:
        return self.ok and len(self.text) >= MIN_USABLE_CHARS

    def as_dict(self) -> dict:
        return {"url": self.url, "ok": self.ok, "usable": self.usable,
                "chars": len(self.text), "title": self.title,
                "error": self.error, "from_cache": self.from_cache}


def _cache_path(article_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{article_id}.json")


def cached(article: dict) -> Source | None:
    path = _cache_path(article["id"])
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            row = json.load(fh)
    except (ValueError, OSError):
        return None
    age = time.time() - row.get("fetched_at", 0)
    if age > (CACHE_TTL if row.get("ok") else FAILURE_TTL):
        return None
    return Source(from_cache=True, **row)


def _store(article: dict, source: Source) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    row = {"url": source.url, "ok": source.ok, "text": source.text,
           "title": source.title, "error": source.error,
           "fetched_at": source.fetched_at}
    tmp = _cache_path(article["id"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(row, fh)
    os.replace(tmp, _cache_path(article["id"]))


def html_to_text(raw: str) -> tuple[str, str]:
    """Readable text and the page title. Good enough for grounding, not a reader view."""
    title_match = _TITLE.search(raw)
    title = (html.unescape(_TAG.sub("", title_match.group("t"))).strip()
             if title_match else "")
    body = _DROP.sub(" ", raw)
    main = _MAIN.search(body)
    if main:
        body = main.group("body")
    body = _BLOCK_END.sub("\n", body)
    text = html.unescape(_TAG.sub(" ", body))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n\s*", "\n\n", text)
    return text.strip(), title


def robots_allows(url: str) -> bool:
    """Best effort. A robots.txt that cannot be read is not treated as a refusal."""
    try:
        parts = urllib.parse.urlsplit(url)
        parser = robotparser.RobotFileParser()
        parser.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
        parser.read()
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def fetch(article: dict, *, force: bool = False, respect_robots: bool = True) -> Source:
    """Fetch one article's page. Always for a named article, never in bulk."""
    url = article.get("url")
    if not url:
        return Source(url="", ok=False, error="this entry has no source URL")

    if not force:
        hit = cached(article)
        if hit is not None:
            return hit

    if respect_robots and not robots_allows(url):
        source = Source(url=url, ok=False, fetched_at=time.time(),
                        error="robots.txt asks us not to fetch this page")
        _store(article, source)
        return source

    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(MAX_BYTES).decode(charset, errors="replace")
        text, title = html_to_text(raw)
        source = Source(url=url, ok=True, text=text, title=title, fetched_at=time.time())
    except urllib.error.HTTPError as exc:
        source = Source(url=url, ok=False, fetched_at=time.time(),
                        error=f"the site returned HTTP {exc.code}")
    except Exception as exc:                 # network, TLS, redirect loops, decoding
        source = Source(url=url, ok=False, fetched_at=time.time(),
                        error=f"{type(exc).__name__}: {exc}")
    _store(article, source)
    return source
