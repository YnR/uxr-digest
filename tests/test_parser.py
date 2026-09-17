"""Checks the parser against the real posts in `posts/`."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "reader"))

from ask import rank_articles  # noqa: E402
from digest_parser import _parse_date, _split_source_date, load_digest  # noqa: E402

POSTS = os.path.join(ROOT, "posts")


class ParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_digest(POSTS)
        cls.by_title = {a["title"]: a for a in cls.data["articles"]}

    def test_every_bold_entry_is_parsed(self):
        raw = 0
        for name in os.listdir(POSTS):
            if name.endswith(".md"):
                with open(os.path.join(POSTS, name), encoding="utf-8") as handle:
                    raw += sum(1 for line in handle if line.startswith("**"))
        folded = self.data["stats"]["duplicates_folded"]
        self.assertEqual(len(self.data["articles"]) + folded, raw)

    def test_every_article_has_a_url_and_summary(self):
        for article in self.data["articles"]:
            self.assertTrue(article["url"], f"no url: {article['title']}")
            self.assertTrue(article["url"].startswith("http"), article["url"])
            self.assertTrue(article["summary"], f"no summary: {article['title']}")

    def test_format_a_entry(self):
        article = self.by_title["Streamlined Measurement of the UX of AI"]
        self.assertEqual(article["parse_format"], "A")
        self.assertEqual(article["source"], "MeasuringU")
        self.assertEqual(article["published_iso"], "2026-08-18")
        self.assertEqual(article["focus_area"], "Research for AI-Powered Products")
        self.assertIn("measuringu.com", article["url"])

    def test_format_b_entry(self):
        article = self.by_title["When Research Output Becomes Curated Context"]
        self.assertEqual(article["parse_format"], "B")
        self.assertEqual(article["source"], "Nielsen Norman Group")
        self.assertEqual(article["published_iso"], "2026-07-24")

    def test_format_c_entry_takes_its_url_from_the_summary(self):
        article = self.by_title["The Loom That Raised Its Hand"]
        self.assertEqual(article["parse_format"], "C")
        self.assertEqual(article["source"], "UX Collective")
        self.assertEqual(article["url"], "https://uxdesign.cc/the-loom-that-raised-its-hand-4e8981b3ef88")
        self.assertNotIn("Read →", article["summary"])

    def test_heading_drift_maps_to_three_focus_areas(self):
        areas = {a["focus_area"] for a in self.data["articles"]}
        self.assertEqual(
            areas,
            {
                "AI in the Research Practice",
                "Research for AI-Powered Products",
                "UX Research Job Market",
            },
        )

    def test_repeated_urls_are_folded_into_one_record(self):
        article = self.by_title["Human-Led Research Remains Essential"]
        self.assertEqual(article["first_seen"], "2026-08-05")
        self.assertTrue(article["repeats"], "the Aug 5 digest repeated the catch-up entry")
        urls = [a["url"].rstrip("/").lower() for a in self.data["articles"]]
        self.assertEqual(len(urls), len(set(urls)))

    def test_source_aliases_are_folded(self):
        self.assertNotIn("NN/G", self.data["sources"])
        self.assertNotIn("dscout", self.data["sources"])
        self.assertIn("Nielsen Norman Group", self.data["sources"])

    def test_leading_italic_aside_becomes_a_note(self):
        article = self.by_title["Surviving the 2026 UX Research Job Market Shift"]
        self.assertIn("Independent blog", article["note"])
        self.assertFalse(article["summary"].startswith("*("))

    def test_catch_up_post_is_read_before_the_same_day_digest(self):
        # Both are dated 2026-08-05 and share entries; the catch-up is the first sighting.
        article = self.by_title["Human-Led Research Remains Essential"]
        self.assertEqual(article["first_seen_file"], "2026-08-05-catchup.md")

    def test_empty_sections_are_recorded(self):
        quiet = next(d for d in self.data["digests"] if d["date"] == "2026-09-16")
        self.assertEqual(quiet["article_count"], 0)
        self.assertEqual(len(quiet["empty_sections"]), 3)


class DateTest(unittest.TestCase):
    def test_dates(self):
        cases = [
            ("Aug 18", "2026-08-18"),
            ("Aug 27–28, 2026", "2026-08-27"),
            ("Sep 2026", "2026-09"),
            ("Apr 2, 2026", "2026-04-02"),
            ("updated Aug 5", "2026-08-05"),
            ("Updated July 2026", "2026-07"),
            ("late July", "2026-07"),
            ("Aug ~9", "2026-08-09"),
            ("", None),
            ("no date here", None),
        ]
        for raw, expected in cases:
            self.assertEqual(_parse_date(raw, 2026), expected, raw)

    def test_source_and_date_split(self):
        self.assertEqual(_split_source_date("NN/G (Jul 24)"), ("NN/G", "Jul 24"))
        self.assertEqual(_split_source_date("NN/g, Aug 7"), ("NN/g", "Aug 7"))
        self.assertEqual(
            _split_source_date("Updated July 2026 (User Interviews)"),
            ("User Interviews", "Updated July 2026"),
        )


class RankingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = load_digest(POSTS)["articles"]

    def test_question_finds_the_obvious_article(self):
        top = rank_articles("what did MeasuringU find about synthetic users?", self.articles, limit=5)
        self.assertTrue(any("Synthetic Users" in a["title"] for a in top), [a["title"] for a in top])

    def test_stopword_only_question_returns_something(self):
        self.assertTrue(rank_articles("what is it about", self.articles, limit=3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
