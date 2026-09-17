"""Local web server for the UX research digest reader.

    python3 reader/server.py           # http://127.0.0.1:8765
    python3 reader/server.py --port 9000 --no-browser
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ask import USE_SOURCE_CHOICES, answer  # noqa: E402
from digest_parser import default_posts_dir, load_digest  # noqa: E402
from search import SearchIndex  # noqa: E402
from sources import fetch as fetch_source  # noqa: E402

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_BODY_BYTES = 64 * 1024


class DigestStore:
    """Parses on demand and re-parses when a post file changes on disk."""

    def __init__(self, posts_dir: str):
        self.posts_dir = posts_dir
        self._lock = threading.Lock()
        self._data: dict | None = None
        self._index: SearchIndex | None = None
        self._fingerprint: tuple | None = None

    def _current_fingerprint(self) -> tuple:
        entries = []
        for name in sorted(os.listdir(self.posts_dir)):
            if name.endswith(".md"):
                entries.append((name, os.path.getmtime(os.path.join(self.posts_dir, name))))
        return tuple(entries)

    def get(self) -> dict:
        with self._lock:
            fingerprint = self._current_fingerprint()
            if self._data is None or fingerprint != self._fingerprint:
                self._data = load_digest(self.posts_dir)
                self._index = SearchIndex(self._data["articles"])
                self._fingerprint = fingerprint
            return self._data

    def index(self) -> SearchIndex:
        self.get()          # rebuilds both when a post changed on disk
        return self._index


class Handler(BaseHTTPRequestHandler):
    store: DigestStore

    def log_message(self, fmt, *args):  # quieter than the default one-line-per-asset
        if self.path.startswith("/api/"):
            sys.stderr.write("%s %s\n" % (self.command, self.path))

    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200):
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):  # noqa: N802
        parts = urllib.parse.urlsplit(self.path)
        path = parts.path
        if path == "/api/digest":
            self._send_json(self.store.get())
            return
        if path == "/api/search":
            self._handle_search(urllib.parse.parse_qs(parts.query))
            return
        if path in ("/", "/index.html"):
            path = "/index.html"
        self._serve_static(path)

    def _handle_search(self, query: dict):
        first = lambda key: (query.get(key) or [""])[0].strip() or None
        try:
            limit = int((query.get("limit") or ["20"])[0])
        except ValueError:
            limit = 20
        filters = {"focus_area": first("focus_area"), "source": first("source"),
                   "since": first("since"), "until": first("until"),
                   "limit": max(1, min(limit, 500))}
        index = self.store.index()
        text = first("q")
        if not text:
            rows = index.browse(**filters)
            self._send_json({"query": "", "results": [
                {"article": a, "score": None, "matched": [],
                 "snippet": a.get("summary", "")} for a in rows]})
            return
        self._send_json({"query": text, "results": [
            {"article": hit.article, "score": round(hit.score, 3),
             "matched": hit.matched, "snippet": hit.snippet}
            for hit in index.search(text, **filters)]})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path not in ("/api/ask", "/api/fetch"):
            self._send_json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            self._send_json({"error": "request too large"}, 413)
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, 400)
            return

        if path == "/api/fetch":
            self._handle_fetch(payload)
            return

        question = (payload.get("question") or "").strip()
        if not question:
            self._send_json({"error": "question is required"}, 400)
            return
        use_source = payload.get("use_source") or "cached"
        if use_source not in USE_SOURCE_CHOICES:
            self._send_json(
                {"error": f"use_source must be one of {', '.join(USE_SOURCE_CHOICES)}"}, 400)
            return

        data = self.store.get()
        articles = data["articles"]
        scope = payload.get("article_ids")
        if scope:
            wanted = set(scope)
            articles = [a for a in articles if a["id"] in wanted] or articles
        self._send_json(answer(question, articles, use_source=use_source))

    def _handle_fetch(self, payload: dict):
        """Fetch and cache one article's source page, on an explicit request."""
        article_id = (payload.get("article_id") or "").strip()
        article = self.store.index().by_id.get(article_id)
        if not article:
            self._send_json({"error": "no such article"}, 404)
            return
        source = fetch_source(article, force=bool(payload.get("force")))
        self._send_json({"article_id": article_id, **source.as_dict()})

    def _serve_static(self, path: str):
        relative = path.lstrip("/")
        full = os.path.normpath(os.path.join(STATIC_DIR, relative))
        if not full.startswith(STATIC_DIR) or not os.path.isfile(full):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        content_type = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        with open(full, "rb") as handle:
            self._send(200, handle.read(), content_type)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read the UX research digest locally.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--posts", default=default_posts_dir(), help="directory holding the digest markdown")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    posts_dir = os.path.abspath(args.posts)
    if not os.path.isdir(posts_dir):
        print(f"No posts directory at {posts_dir}", file=sys.stderr)
        return 1

    Handler.store = DigestStore(posts_dir)
    stats = Handler.store.get()["stats"]
    url = f"http://{args.host}:{args.port}/"
    print(f"Digest reader on {url}")
    print(
        f"  {stats['articles']} articles from {stats['digests']} digests "
        f"({stats['first_digest']} to {stats['last_digest']}), "
        f"{stats['duplicates_folded']} repeats folded"
    )

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
