"""Checks the evals resources page, its parser and the feeds built from it."""

import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "reader"))

from evals_resources import (  # noqa: E402
    DEFAULT_SOURCE, build, feed_order, heading_anchor, inline_html, parse_resources,
    plain_text)

BASE = "https://example.test/uxr/evals/"
BUILT = datetime(2026, 11, 9, tzinfo=timezone.utc)
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"

SAMPLE = """# Resources

## 1. First piece

- **Link:** <https://example.test/first>
- **Author:** Ada Example
- **Company at publication:** Acme
- **Find them:** [Blog](https://ada.example) ·
  [LinkedIn](https://www.linkedin.com/in/ada/)
- **Format:** Article (blog)
- **Published:** 2025-01-02

**What it adds.** The first *real* point, with a [link](https://example.test/x).

- **A list item.** Still part of what it adds.

### 1a. Related take: Second piece

- **Link:** <https://example.test/second>
- **Speakers:** Bo Example and Cy Example
- **Format:** Presentation (talk)
- **Published:** 2025. A recap dated 2025-06-01 mentions it.

**Why it sits under the first.** Same idea.

**How it differs.** It goes further.

---

## Adding a resource

Not an entry.
"""


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.entries = parse_resources(SAMPLE)

    def test_entries_and_grouping(self):
        self.assertEqual([e["id"] for e in self.entries], ["1", "1a"])
        self.assertIsNone(self.entries[0]["related_to"])
        self.assertEqual(self.entries[1]["related_to"], "1")
        self.assertEqual(self.entries[1]["title"], "Second piece")

    def test_fields(self):
        first, second = self.entries
        self.assertEqual(first["url"], "https://example.test/first")
        self.assertEqual(first["authors"], "Ada Example")
        self.assertEqual(first["company"], "Acme")
        self.assertEqual(first["kind"], "Article")
        self.assertEqual(first["published_iso"], "2025-01-02")
        self.assertEqual([p["label"] for p in first["profiles"]], ["Blog", "LinkedIn"])
        self.assertEqual(second["authors"], "Bo Example and Cy Example")
        self.assertEqual(second["kind"], "Presentation")

    def test_only_a_leading_date_counts(self):
        self.assertIsNone(self.entries[1]["published_iso"])
        self.assertTrue(self.entries[1]["published"].startswith("2025."))

    def test_sections_and_summary(self):
        first, second = self.entries
        self.assertEqual([s["label"] for s in first["sections"]], ["What it adds"])
        self.assertIn("Still part of what it adds", first["summary"])
        self.assertEqual([s["label"] for s in second["sections"]],
                         ["Why it sits under the first", "How it differs"])
        self.assertEqual(second["summary"], "It goes further.")

    def test_closing_section_is_not_an_entry(self):
        self.assertNotIn("Not an entry", json.dumps(self.entries))

    def test_feed_order(self):
        self.assertEqual([e["id"] for e in feed_order(self.entries)], ["1", "1a"])


class InlineTest(unittest.TestCase):
    def test_markup(self):
        html = inline_html("A **bold** and *em* <https://a.test/?x=1&y=2> [t](https://b.test) `c` <b>")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>em</em>", html)
        self.assertIn('<a href="https://a.test/?x=1&amp;y=2">', html)
        self.assertIn('<a href="https://b.test">t</a>', html)
        self.assertIn("<code>c</code>", html)
        self.assertIn("&lt;b&gt;", html)

    def test_related_takes_are_nested(self):
        from evals_resources import markdown_html
        html = markdown_html(SAMPLE + "\n| # | R |\n|---|---|\n| 1 | a |\n| 1a | ↳ b |\n")
        self.assertEqual(html.count('<section class="related">'), 1)
        self.assertEqual(html.count("</section>"), 1)
        self.assertLess(html.index('<section class="related">'), html.index('id="1a-related-take-second-piece"'))
        self.assertLess(html.index("It goes further"), html.index("</section>"))
        self.assertLess(html.index("</section>"), html.index("<hr>"))
        self.assertIn('<tr class="sub"><td>1a</td><td>b</td>', html)

    def test_plain_text_and_anchor(self):
        self.assertEqual(plain_text("See [the post](https://x.test) *now*"), "See the post now")
        self.assertEqual(heading_anchor("1a. Related take: What's *new*?"),
                         "1a-related-take-whats-new")


class RealPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.out = cls._dir.name
        cls.entries = build(DEFAULT_SOURCE, cls.out, BASE, built=BUILT)

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def test_every_entry_is_complete(self):
        self.assertGreaterEqual(len(self.entries), 8)
        ids = {e["id"] for e in self.entries}
        for e in self.entries:
            with self.subTest(e["id"]):
                self.assertTrue(e["url"] and e["url"].startswith("https://"))
                self.assertTrue(e["format"])
                self.assertTrue(e["summary"])
                if e["related_to"]:
                    self.assertIn(e["related_to"], ids)

    def test_rss(self):
        channel = ET.parse(os.path.join(self.out, "feed.xml")).getroot().find("channel")
        items = channel.findall("item")
        self.assertEqual(len(items), len(self.entries))
        self.assertEqual(len({i.findtext("guid") for i in items}), len(items))
        for item in items:
            self.assertTrue(item.findtext("description"))
            self.assertIn("<h4>", item.findtext(CONTENT))

    def test_json_feed_and_list(self):
        with open(os.path.join(self.out, "feed.json"), encoding="utf-8") as handle:
            feed = json.load(handle)
        self.assertEqual(feed["feed_url"], BASE + "feed.json")
        self.assertEqual(len(feed["items"]), len(self.entries))
        self.assertTrue(all(i["external_url"].startswith(BASE + "#") for i in feed["items"]))
        with open(os.path.join(self.out, "resources.json"), encoding="utf-8") as handle:
            listing = json.load(handle)
        self.assertEqual([r["id"] for r in listing["resources"]], [e["id"] for e in self.entries])

    def test_html_anchors_match_the_table(self):
        with open(os.path.join(self.out, "index.html"), encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn('href="' + BASE + 'feed.xml"', html)
        for e in self.entries:
            with self.subTest(e["id"]):
                self.assertIn(f'id="{e["anchor"]}"', html)
                self.assertIn(f'href="#{e["anchor"]}"', html)


if __name__ == "__main__":
    unittest.main()
