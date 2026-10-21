"""Checks the RSS and JSON feeds built from the real posts in `posts/`."""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "reader"))

import server  # noqa: E402
from digest_parser import load_digest, split_byline  # noqa: E402
from feeds import SOURCE_DOMAIN, TOPIC_DOMAIN, build, stream  # noqa: E402

POSTS = os.path.join(ROOT, "posts")
BASE = "https://example.test/uxr/"
BUILT = datetime(2026, 10, 21, tzinfo=timezone.utc)


class FeedBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.out = cls._dir.name
        cls.index = build(POSTS, cls.out, BASE, built=BUILT)
        cls.data = load_digest(POSTS)

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def _rss(self, rel):
        return ET.parse(os.path.join(self.out, rel)).getroot()

    def _json(self, rel):
        with open(os.path.join(self.out, rel), encoding="utf-8") as handle:
            return json.load(handle)

    def test_main_feed_carries_every_article_once_with_its_summary(self):
        items = self._rss("feed.xml").findall("./channel/item")
        self.assertEqual(len(items), self.data["stats"]["articles"])
        guids = [i.findtext("guid") for i in items]
        self.assertEqual(len(guids), len(set(guids)))
        summaries = {a["summary"] for a in self.data["articles"]}
        for item in items:
            self.assertTrue(item.findtext("link").startswith("http"))
            self.assertTrue(any(item.findtext("description").startswith(s) for s in summaries))

    def test_items_are_tagged_with_topic_and_source(self):
        for item in self._rss("feed.xml").findall("./channel/item"):
            domains = {c.get("domain"): c.text for c in item.findall("category")}
            self.assertIn(domains[TOPIC_DOMAIN], self.data["focus_areas"])
            self.assertIn(domains[SOURCE_DOMAIN], self.data["sources"])

    def test_json_feed_matches_rss(self):
        feed = self._json("feed.json")
        self.assertEqual(feed["version"], "https://jsonfeed.org/version/1.1")
        self.assertEqual(feed["feed_url"], BASE + "feed.json")
        rss_ids = [i.findtext("guid") for i in self._rss("feed.xml").findall("./channel/item")]
        self.assertEqual([i["id"] for i in feed["items"]], rss_ids)
        for item in feed["items"]:
            self.assertTrue(item["summary"])
            self.assertEqual(item["_uxr"]["digest_date"], item["date_published"][:10])

    def test_newest_curated_first(self):
        dates = [i["_uxr"]["digest_date"] for i in self._json("feed.json")["items"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_split_feeds_partition_the_stream(self):
        total = self.data["stats"]["articles"]
        for kind in ("topic", "source", "month"):
            feeds = [f for f in self.index["feeds"] if f["kind"] == kind]
            self.assertTrue(feeds, kind)
            self.assertEqual(sum(f["items"] for f in feeds), total, kind)
            for f in feeds:
                rel = f["rss"][len(BASE):]
                self.assertEqual(len(self._rss(rel).findall("./channel/item")), f["items"])

    def test_opml_lists_every_rss_feed(self):
        urls = {o.get("xmlUrl") for o in ET.parse(os.path.join(self.out, "feeds.opml")).iter("outline")
                if o.get("xmlUrl")}
        self.assertEqual(urls, {f["rss"] for f in self.index["feeds"]})

    def test_source_filter_is_exact(self):
        rows = stream(self.data["articles"], source="UX Collective")
        self.assertTrue(rows)
        self.assertTrue(all(a["source"] == "UX Collective" for a in rows))


class BylineTest(unittest.TestCase):
    def test_author_is_split_from_a_known_publication(self):
        self.assertEqual(split_byline("Tanner Kohler, Nielsen Norman Group"),
                         ("Nielsen Norman Group", "Tanner Kohler"))
        self.assertEqual(split_byline("Will Schiavone, Eva Sundberg & Jeff Sauro, MeasuringU"),
                         ("MeasuringU", "Will Schiavone, Eva Sundberg & Jeff Sauro"))

    def test_unknown_tail_is_left_whole(self):
        self.assertEqual(split_byline("Philip Burgess"), ("Philip Burgess", None))
        self.assertEqual(split_byline("NN/g"), ("Nielsen Norman Group", None))

    def test_bylines_no_longer_fragment_sources(self):
        sources = load_digest(POSTS)["sources"]
        self.assertFalse([s for s in sources if "," in s], sources)


class FeedEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.Handler.store = server.DigestStore(POSTS)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def _get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.headers.get_content_type(), response.read()

    def test_rss_endpoint_filters_by_topic(self):
        kind, body = self._get("/feed.xml?topic=UX+Research+Job+Market")
        self.assertEqual(kind, "application/rss+xml")
        items = ET.fromstring(body).findall("./channel/item")
        self.assertTrue(items)
        for item in items:
            topics = [c.text for c in item.findall("category") if c.get("domain") == TOPIC_DOMAIN]
            self.assertEqual(topics, ["UX Research Job Market"])

    def test_json_endpoint_filters_by_source_and_date(self):
        kind, body = self._get("/feed.json?source=Nielsen+Norman+Group&month=2026-10")
        self.assertEqual(kind, "application/feed+json")
        items = json.loads(body)["items"]
        self.assertTrue(items)
        for item in items:
            self.assertEqual(item["_uxr"]["source"], "Nielsen Norman Group")
            self.assertTrue(item["_uxr"]["digest_date"].startswith("2026-10"))


if __name__ == "__main__":
    unittest.main()
