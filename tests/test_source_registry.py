"""Checks the canonical source list and the matching rules built on it.

The real `sources.json` is one of the fixtures: it is the file the digest task
and the reader both read, so a typo in it is a bug in both.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reader"))

import source_registry  # noqa: E402
from digest_parser import default_posts_dir, load_digest, resolve_source  # noqa: E402

SOURCES_FILE = source_registry.default_sources_path()


class SourcesFileTest(unittest.TestCase):
    """The file itself: every client depends on it being well formed."""

    @classmethod
    def setUpClass(cls):
        with open(SOURCES_FILE, encoding="utf-8") as handle:
            cls.payload = json.load(handle)
        cls.rows = cls.payload["sources"]

    def test_lives_in_the_repo_root(self):
        self.assertTrue(os.path.isfile(SOURCES_FILE))
        self.assertEqual(os.path.basename(SOURCES_FILE), "sources.json")

    def test_every_entry_has_the_required_fields(self):
        for row in self.rows:
            self.assertTrue(row.get("id"), row)
            self.assertTrue(row.get("name"), row)
            self.assertIn("monitored", row)
            self.assertIsInstance(row.get("domains", []), list)
            self.assertIsInstance(row.get("aliases", []), list)

    def test_ids_and_names_are_unique(self):
        ids = [row["id"] for row in self.rows]
        names = [row["name"].lower() for row in self.rows]
        self.assertCountEqual(ids, set(ids))
        self.assertCountEqual(names, set(names))

    def test_a_monitored_source_has_a_url_to_check(self):
        for row in self.rows:
            if row["monitored"]:
                self.assertTrue(row.get("url"), f"{row['name']} is monitored with no url")
                self.assertTrue(row["url"].startswith("https://"), row["url"])

    def test_no_alias_collides_with_another_source(self):
        owner = {}
        for row in self.rows:
            for name in [row["name"], *row.get("aliases", [])]:
                key = name.strip().lower()
                self.assertNotIn(key, owner, f"{name!r} claimed by {owner.get(key)} and {row['id']}")
                owner[key] = row["id"]

    def test_the_monitored_sources_are_listed(self):
        monitored = {row["name"] for row in self.rows if row["monitored"]}
        self.assertEqual(len(monitored), 11)
        for name in ("Nielsen Norman Group", "Baymard Institute", "MeasuringU",
                     "UX Collective", "People Nerds (dscout)", "User Interviews",
                     "UX Design Weekly", "Dense Discovery", "Sidebar",
                     "Quantitative UX Research Blog", "Research toolbox"):
            self.assertIn(name, monitored)


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.registry = source_registry.registry()

    def test_exact_name(self):
        self.assertEqual(self.registry.resolve("MeasuringU").id, "measuringu")

    def test_alias(self):
        self.assertEqual(self.registry.resolve("NN/G").id, "nngroup")
        self.assertEqual(self.registry.resolve("dscout").id, "people-nerds")
        self.assertEqual(self.registry.resolve("Quant UX Blog").id, "quant-ux")

    def test_case_and_padding_do_not_matter(self):
        self.assertEqual(self.registry.resolve("  nn/g  ").id, "nngroup")

    def test_url_wins_over_a_bylined_name(self):
        entry = self.registry.resolve("Patrick Neeman, UX Collective",
                                      "https://uxdesign.cc/some-article-123")
        self.assertEqual(entry.id, "ux-collective")

    def test_subdomain_belongs_to_the_parent(self):
        entry = self.registry.resolve("", "https://newsletter.uxdesign.cc/p/whatever")
        self.assertEqual(entry.id, "ux-collective")

    def test_name_quoted_inside_a_longer_credit(self):
        entry = self.registry.resolve("Jim Lewis & Jeff Sauro, MeasuringU")
        self.assertEqual(entry.id, "measuringu")

    def test_unknown_source_is_not_forced_onto_an_entry(self):
        self.assertIsNone(self.registry.resolve("Some New Blog", "https://example.com/x"))

    def test_resolve_source_falls_back_to_the_cited_name(self):
        name, source_id, url = resolve_source("Some New Blog", "https://example.com/x")
        self.assertEqual(name, "Some New Blog")
        self.assertIsNone(source_id)
        self.assertIsNone(url)

    def test_resolve_source_returns_the_registry_url(self):
        name, source_id, url = resolve_source("NN/g", "https://www.nngroup.com/articles/x/")
        self.assertEqual((name, source_id), ("Nielsen Norman Group", "nngroup"))
        self.assertEqual(url, "https://www.nngroup.com/articles/")

    def test_monitored_and_others_partition_the_list(self):
        self.assertEqual(len(self.registry.monitored) + len(self.registry.others),
                         len(self.registry))


class HostTest(unittest.TestCase):
    def test_strips_scheme_www_port_and_path(self):
        for url, host in (
            ("https://www.nngroup.com/articles/x/", "nngroup.com"),
            ("http://measuringu.com:8080/blog", "measuringu.com"),
            ("uxdesign.cc/a-post-123", "uxdesign.cc"),
            ("https://WWW.Sidebar.IO/", "sidebar.io"),
        ):
            self.assertEqual(source_registry.host_of(url), host)

    def test_no_url_is_no_host(self):
        self.assertEqual(source_registry.host_of(None), "")
        self.assertEqual(source_registry.host_of(""), "")


class MissingFileTest(unittest.TestCase):
    """The reader stays usable when the file is absent or broken."""

    def test_missing_file_is_an_empty_registry(self):
        registry = source_registry.load(os.path.join(tempfile.gettempdir(), "no-such-sources.json"))
        self.assertEqual(len(registry), 0)
        self.assertIsNone(registry.resolve("MeasuringU"))

    def test_broken_json_is_an_empty_registry(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{not json")
            path = handle.name
        try:
            self.assertEqual(len(source_registry.load(path)), 0)
        finally:
            os.unlink(path)

    def test_entries_without_a_name_are_skipped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"sources": [{"id": "x"}, {"name": "Real Blog", "monitored": True}]}, handle)
            path = handle.name
        try:
            registry = source_registry.load(path)
            self.assertEqual([e.name for e in registry.entries], ["Real Blog"])
            self.assertEqual(registry.entries[0].id, "real-blog")
        finally:
            os.unlink(path)


class GroupingTest(unittest.TestCase):
    """What the reader's sidebar is built from."""

    @classmethod
    def setUpClass(cls):
        cls.data = load_digest(default_posts_dir())

    def test_groups_are_monitored_first(self):
        labels = [group["label"] for group in self.data["source_groups"]]
        self.assertEqual(labels[0], "Monitored sources")
        self.assertTrue(all(row["monitored"] for row in self.data["source_groups"][0]["sources"]))

    def test_a_monitored_source_is_listed_even_with_no_articles(self):
        monitored = {row["name"]: row for row in self.data["source_groups"][0]["sources"]}
        self.assertIn("Sidebar", monitored)
        self.assertEqual(monitored["Sidebar"]["count"], 0)

    def test_every_listed_source_carries_its_url(self):
        for row in self.data["source_groups"][0]["sources"]:
            self.assertTrue(row["url"], row["name"])

    def test_bylined_credits_do_not_become_their_own_filter_entry(self):
        for name in self.data["sources"]:
            self.assertNotIn(", UX Collective", name)
            self.assertNotIn(", MeasuringU", name)
            self.assertNotIn(", Nielsen Norman Group", name)

    def test_counts_add_up_to_the_articles(self):
        total = sum(row["count"]
                    for group in self.data["source_groups"]
                    for row in group["sources"])
        self.assertEqual(total, len(self.data["articles"]))

    def test_articles_carry_the_registry_id_for_listed_sources(self):
        nng = [a for a in self.data["articles"] if a["source"] == "Nielsen Norman Group"]
        self.assertTrue(nng)
        for article in nng:
            self.assertEqual(article["source_id"], "nngroup")
            self.assertEqual(article["source_url"], "https://www.nngroup.com/articles/")

    def test_every_cited_source_is_in_the_file(self):
        """A source the posts cite but the file omits should be added to it."""
        self.assertEqual(self.data["stats"]["sources_unlisted"], 0)


if __name__ == "__main__":
    unittest.main()
