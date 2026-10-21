"""Read `sources.json`, the project's one list of sources.

`sources.json` in the repo root names every source the digest monitors, with
the URL to check and the names earlier posts have used for it. The scheduled
digest task reads it to decide what to check; this module is how the reader app
reads the same file, so neither carries its own copy of the list.

Not to be confused with `sources.py`, which fetches one article's own page when
a question needs more than the digest's summary. This module is about the list
of publications; that one is about the pages they publish.

The posts name the same publication several ways — `NN/G`, `NN/g`, `Nielsen
Norman Group`, and bylines like `Tanner Kohler, Nielsen Norman Group` — so
`resolve()` folds a cited name onto one registry entry, which is what lets the
reader group and filter by source.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

SOURCES_FILENAME = "sources.json"
# An alias shorter than this is not used for substring matching: "NNG" inside a
# longer name is as likely to be a coincidence as a credit.
MIN_SUBSTRING_ALIAS = 4


def default_sources_path() -> str:
    override = os.environ.get("UXR_SOURCES_FILE")
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), SOURCES_FILENAME)


def host_of(url: str | None) -> str:
    """The hostname of a URL, with or without a scheme, lowercased and bare."""
    if not url:
        return ""
    cleaned = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url.strip(), flags=re.I)
    host = cleaned.split("/")[0].split("?")[0].split("#")[0].lower()
    host = host.split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


@dataclass
class SourceEntry:
    id: str
    name: str
    url: str | None = None
    monitored: bool = False
    domains: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "url": self.url,
                "monitored": self.monitored}

    @property
    def names(self) -> list[str]:
        return [self.name, *self.aliases]


class Registry:
    """The parsed `sources.json`, with the lookups the clients need."""

    def __init__(self, entries: list[SourceEntry]):
        self.entries = entries
        self._by_id = {e.id: e for e in entries}
        self._by_name: dict[str, SourceEntry] = {}
        self._by_domain: dict[str, SourceEntry] = {}
        for entry in entries:
            for name in entry.names:
                self._by_name.setdefault(name.strip().lower(), entry)
            for domain in entry.domains:
                self._by_domain.setdefault(host_of(domain), entry)
        # Longest name first, so "The User Research Strategist" wins over a
        # shorter alias that also appears in the cited name.
        self._substring = sorted(
            ((name.strip().lower(), entry) for entry in entries for name in entry.names
             if len(name.strip()) >= MIN_SUBSTRING_ALIAS),
            key=lambda pair: len(pair[0]),
            reverse=True,
        )

    def __len__(self) -> int:
        return len(self.entries)

    @property
    def monitored(self) -> list[SourceEntry]:
        return [e for e in self.entries if e.monitored]

    @property
    def others(self) -> list[SourceEntry]:
        return [e for e in self.entries if not e.monitored]

    def by_id(self, source_id: str) -> SourceEntry | None:
        return self._by_id.get(source_id)

    def by_domain(self, url: str | None) -> SourceEntry | None:
        host = host_of(url)
        if not host:
            return None
        if host in self._by_domain:
            return self._by_domain[host]
        # A subdomain belongs to its parent: newsletter.uxdesign.cc is UX Collective.
        for domain, entry in self._by_domain.items():
            if host.endswith("." + domain):
                return entry
        return None

    def resolve(self, name: str | None, url: str | None = None) -> SourceEntry | None:
        """Fold a cited source name onto one registry entry.

        The URL decides first: it is the one part of an entry that a byline
        cannot muddle, so `Patrick Neeman, UX Collective` lands on UX Collective
        by way of uxdesign.cc. Then an exact name or alias, then a name quoted
        inside a longer credit.
        """
        by_url = self.by_domain(url)
        if by_url:
            return by_url
        cited = (name or "").strip().lower()
        if not cited:
            return None
        if cited in self._by_name:
            return self._by_name[cited]
        for candidate, entry in self._substring:
            if candidate in cited:
                return entry
        return None


def load(path: str | None = None) -> Registry:
    """Parse `sources.json`. A missing or broken file yields an empty registry.

    The reader is useful without the file — sources simply stay as the posts
    spell them — so a bad file degrades the grouping rather than the app.
    """
    target = path or default_sources_path()
    try:
        with open(target, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return Registry([])
    entries = []
    for row in payload.get("sources") or []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        entries.append(SourceEntry(
            id=row.get("id") or re.sub(r"[^a-z0-9]+", "-", row["name"].lower()).strip("-"),
            name=row["name"].strip(),
            url=(row.get("url") or None),
            monitored=bool(row.get("monitored")),
            domains=[d for d in (row.get("domains") or []) if d],
            aliases=[a for a in (row.get("aliases") or []) if a],
        ))
    return Registry(entries)


_cached: tuple[str, float, Registry] | None = None


def registry(path: str | None = None) -> Registry:
    """The shared registry, re-read when the file changes on disk."""
    global _cached
    target = path or default_sources_path()
    try:
        stamp = os.path.getmtime(target)
    except OSError:
        stamp = 0.0
    if _cached and _cached[0] == target and _cached[1] == stamp:
        return _cached[2]
    loaded = load(target)
    _cached = (target, stamp, loaded)
    return loaded


if __name__ == "__main__":
    reg = registry()
    print(f"{len(reg)} sources in {default_sources_path()}")
    for entry in reg.entries:
        mark = "monitored" if entry.monitored else "cited only"
        print(f"  {entry.name:32} {mark:11} {entry.url or '-'}")
