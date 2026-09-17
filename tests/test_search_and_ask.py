"""Checks search, source fetching and the answering layer.

Everything here runs against the real posts in `posts/` and never touches the
network: the fetching tests drive the cache and the HTML extraction directly.
"""

import json
import os
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "reader"))

import sources  # noqa: E402
from ask import (  # noqa: E402
    USE_SOURCE_CHOICES,
    Passage,
    _split,
    answer,
    gather_passages,
    rank_articles,
    rank_passages,
)
from digest_parser import load_digest  # noqa: E402
from search import SearchIndex, snippet, stem, tokenise  # noqa: E402


class SearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = load_digest(os.path.join(ROOT, "posts"))["articles"]
        cls.index = SearchIndex(cls.articles)
        cls.by_title = {a["title"]: a for a in cls.articles}

    def test_results_are_ordered_by_relevance(self):
        hits = self.index.search("star wars")
        self.assertTrue(hits)
        self.assertEqual(hits[0].article["title"], "What Star Wars Got Right About AI")
        scores = [h.score for h in hits]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_plurals_match_either_way(self):
        # Substring matching finds "researchers" for "research" but not the reverse.
        self.assertEqual(stem("researchers"), stem("researcher"))
        self.assertTrue(self.index.search("synthetic user"))
        self.assertTrue(self.index.search("synthetic users"))

    def test_a_title_hit_outranks_a_summary_hit(self):
        hits = self.index.search("job board")
        self.assertIn("Job Board", hits[0].article["title"])

    def test_quoted_phrase_must_appear(self):
        self.assertTrue(self.index.search('"synthetic users"'))
        # Quotes mean required: the words are all common, the phrase is not there.
        self.assertFalse(self.index.search('"no digest ever wrote this phrase"'))

    def test_stopwords_alone_match_nothing(self):
        self.assertEqual(tokenise("what is it about"), [])
        self.assertEqual(self.index.search("what is it about"), [])

    def test_filters_narrow_the_results(self):
        rows = self.index.browse(focus_area="UX Research Job Market")
        self.assertTrue(rows)
        self.assertTrue(all(a["focus_area"] == "UX Research Job Market" for a in rows))
        recent = self.index.browse(since="2026-09-01")
        self.assertTrue(recent)
        # Month-only dates count when the month contains the cutoff, so compare
        # at month precision rather than as raw strings.
        self.assertTrue(all((a["published_iso"] or a["first_seen"])[:7] >= "2026-09"
                            for a in recent))

    def test_month_only_dates_are_not_dropped_by_a_date_filter(self):
        # "Sep 2026" parses to "2026-09", which sorts before every day of its
        # own month; comparing it raw hides those articles from a since filter.
        titles = {a["title"] for a in self.index.browse(since="2026-09-01")}
        self.assertIn("Persistent lessons in human-centered automation", titles)
        partial = [a for a in self.articles if len(a["published_iso"] or "") == 7]
        september = [a for a in partial if a["published_iso"] == "2026-09"]
        self.assertTrue(september)
        for article in september:
            self.assertIn(article["title"], titles)

    def test_a_date_filter_still_excludes_what_it_should(self):
        rows = self.index.browse(since="2026-09-01")
        self.assertTrue(rows)
        for article in rows:
            when = article["published_iso"] or article["first_seen"]
            # Either a September-or-later day, or a month that includes one.
            self.assertGreaterEqual(when[:7], "2026-09")

    def test_filters_apply_to_a_query_too(self):
        hits = self.index.search("AI", focus_area="UX Research Job Market")
        self.assertTrue(all(h.article["focus_area"] == "UX Research Job Market"
                            for h in hits))

    def test_snippet_lands_on_the_matching_words(self):
        article = self.by_title["State of Synthetic Users Report"]
        text = snippet(article, {"synthetic"})
        self.assertIn("synthetic", text.lower())

    def test_repeat_summaries_are_searchable(self):
        # "agents proliferate" appears only in the later of this article's two
        # summaries, so finding it proves repeats are indexed, not discarded.
        article = self.by_title["Building Trustworthy AI Chatbots"]
        self.assertNotIn("agents proliferate", article["all_summaries"][0].lower())
        hits = self.index.search('"agents proliferate"')
        self.assertEqual([h.article["title"] for h in hits],
                         ["Building Trustworthy AI Chatbots"])


class SourceFetchTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self._saved = sources.CACHE_DIR
        sources.CACHE_DIR = self._dir.name
        self.article = {"id": "abc123", "title": "T",
                        "url": "https://example.com/a-piece"}

    def tearDown(self):
        sources.CACHE_DIR = self._saved
        self._dir.cleanup()

    def test_html_becomes_readable_text(self):
        raw = ("<html><head><title>A Piece — Site</title></head><body>"
               "<nav>Home</nav><script>var x=1;</script>"
               "<article><h1>Head</h1><p>Body with &amp; entity.</p></article>"
               "<footer>copyright</footer></body></html>")
        text, title = sources.html_to_text(raw)
        self.assertEqual(title, "A Piece — Site")
        self.assertIn("Body with & entity.", text)
        for chrome in ("Home", "var x", "copyright"):
            self.assertNotIn(chrome, text)

    def test_an_entry_without_a_url_fails_cleanly(self):
        result = sources.fetch({"id": "x", "title": "T", "url": None})
        self.assertFalse(result.ok)
        self.assertIn("no source URL", result.error)

    def test_a_cached_page_is_returned_without_fetching(self):
        sources._store(self.article, sources.Source(
            url=self.article["url"], ok=True, text="x" * 2000,
            title="A Piece", fetched_at=time.time()))
        hit = sources.cached(self.article)
        self.assertIsNotNone(hit)
        self.assertTrue(hit.from_cache)
        self.assertTrue(hit.usable)

    def test_a_thin_page_is_not_treated_as_usable(self):
        thin = sources.Source(url=self.article["url"], ok=True, text="too short",
                              fetched_at=time.time())
        self.assertFalse(thin.usable)

    def test_a_stale_failure_is_not_cached_for_long(self):
        # A transient network failure must not block retries for a month.
        sources._store(self.article, sources.Source(
            url=self.article["url"], ok=False, error="boom",
            fetched_at=time.time() - sources.FAILURE_TTL - 1))
        self.assertIsNone(sources.cached(self.article))

    def test_a_fresh_success_survives(self):
        sources._store(self.article, sources.Source(
            url=self.article["url"], ok=True, text="y" * 1000,
            fetched_at=time.time() - 60))
        self.assertIsNotNone(sources.cached(self.article))

    def test_a_corrupt_cache_file_is_ignored(self):
        path = os.path.join(sources.CACHE_DIR, f"{self.article['id']}.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(sources.cached(self.article))


class FetchIntegrationTest(unittest.TestCase):
    """The whole chain — fetch, extract, cache, ground — against a local page.

    The real article sites are not reachable from a test run, so this serves a
    page shaped like one from localhost and drives the same code path.
    """

    PAGE = ("<html><head><title>Synthetic Users, Measured</title></head><body>"
            "<nav>menu</nav><article><h1>Synthetic Users, Measured</h1>"
            "<p>We recruited 412 participants for the benchmark study. "
            "Each completed six tasks.</p>"
            "<p>" + ("Detail about the method. " * 60) + "</p>"
            "</article><footer>copyright</footer></body></html>")

    @classmethod
    def setUpClass(cls):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading

        page = cls.PAGE

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = (b"User-agent: *\nAllow: /\n" if self.path == "/robots.txt"
                        else page.encode("utf-8"))
                kind = ("text/plain" if self.path == "/robots.txt" else "text/html")
                self.send_response(200)
                self.send_header("Content-Type", f"{kind}; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self._saved = sources.CACHE_DIR
        sources.CACHE_DIR = self._dir.name
        self.article = {
            "id": "local1", "title": "Synthetic Users, Measured",
            "url": f"http://127.0.0.1:{self.port}/article",
            "summary": "The digest's one-paragraph take on the study.",
            "all_summaries": ["The digest's one-paragraph take on the study."],
            "first_seen": "2026-08-05", "repeats": [],
        }

    def tearDown(self):
        sources.CACHE_DIR = self._saved
        self._dir.cleanup()

    def test_a_fetched_page_becomes_grounding(self):
        fetched = sources.fetch(self.article)
        self.assertTrue(fetched.ok, fetched.error)
        self.assertTrue(fetched.usable)
        self.assertIn("412 participants", fetched.text)
        self.assertNotIn("copyright", fetched.text)

        # The detail is in the article and not in the digest's summary.
        self.assertNotIn("412", self.article["summary"])
        passages = gather_passages([self.article], "cached", [])
        kinds = {p.kind for p in passages}
        self.assertEqual(kinds, {"summary", "source"})
        self.assertTrue(any("412 participants" in p.text for p in passages))

    def test_summaries_only_ignores_a_cached_page(self):
        sources.fetch(self.article)
        passages = gather_passages([self.article], "never", [])
        self.assertTrue(all(p.kind == "summary" for p in passages))

    def test_the_second_read_comes_from_the_cache(self):
        sources.fetch(self.article)
        again = sources.fetch(self.article)
        self.assertTrue(again.from_cache)

    def test_a_missing_page_is_reported_not_guessed(self):
        missing = dict(self.article, id="local2",
                       url=f"http://127.0.0.1:{self.port + 1}/gone")
        notices = []
        passages = gather_passages([missing], "fetch", notices)
        self.assertTrue(all(p.kind == "summary" for p in passages))
        self.assertTrue(notices)
        self.assertIn("Could not read the source page", notices[0])


class AnswerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = load_digest(os.path.join(ROOT, "posts"))["articles"]
        cls.by_title = {a["title"]: a for a in cls.articles}

    def test_summaries_only_by_default_without_a_cache(self):
        article = self.by_title["State of Synthetic Users Report"]
        notices = []
        passages = gather_passages([article], "never", notices)
        self.assertTrue(passages)
        self.assertTrue(all(p.kind == "summary" for p in passages))
        self.assertEqual(notices, [])

    def test_every_summary_of_a_repeated_article_is_grounding(self):
        article = self.by_title["A Review of Experiments with Synthetic Users"]
        passages = gather_passages([article], "never", [])
        self.assertGreater(len(passages), 1)

    def test_an_unknown_source_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            answer("anything", self.articles, use_source="wishful")
        self.assertEqual(USE_SOURCE_CHOICES, ("never", "cached", "fetch"))

    def test_a_stopword_question_still_returns_articles(self):
        self.assertTrue(rank_articles("what is it about", self.articles, limit=3))

    def test_ranking_puts_source_excerpts_after_summaries(self):
        passages = [
            Passage("an excerpt about sample sizes", "source", "1", "T", "article page"),
            Passage("a digest summary", "summary", "1", "T", "digest summary, 2026-08-05"),
        ]
        ranked = rank_passages(passages, "sample size")
        self.assertEqual(ranked[0].kind, "summary")
        self.assertEqual(ranked[1].kind, "source")

    def test_long_text_splits_into_readable_passages(self):
        chunks = _split("A sentence here. " * 200)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 900 for c in chunks))

    def test_answering_without_credentials_still_returns_matches(self):
        result = answer("junior researchers and AI", self.articles, use_source="never")
        self.assertTrue(result["matches"])
        self.assertTrue(result["passages"])
        self.assertFalse(result["used_source_pages"])
        # No key in the test environment, so a notice explains the missing answer.
        if result["answer"] is None:
            self.assertTrue(result["notice"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
