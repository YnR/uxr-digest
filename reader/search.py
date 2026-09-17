"""Ranked search over the parsed digest.

BM25 across a few weighted fields, with light plural stemming, quoted-phrase
support and filters. The collection is well under a thousand entries, so the
whole thing runs in memory on every query with no index files and no
dependencies.

Substring matching was the obvious first move and it goes wrong in both
directions here: searching "researchers" misses "research", and every match
looks as good as every other because nothing is ranked.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

# A title hit says more about relevance than a summary hit.
FIELD_WEIGHTS = {"title": 3, "source": 2, "focus_area": 1, "summary": 1, "note": 1}

K1, B = 1.2, 0.75

STOPWORDS = {
    "a", "about", "all", "also", "an", "and", "any", "are", "as", "at", "be", "been",
    "but", "by", "can", "could", "did", "do", "does", "for", "from", "had", "has",
    "have", "how", "i", "in", "into", "is", "it", "its", "me", "more", "most", "of",
    "on", "only", "or", "our", "over", "say", "should", "so", "some", "such", "tell",
    "than", "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "to", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "why", "will", "with", "would", "you", "your",
}

_WORD = re.compile(r"[a-z0-9]+")
_PHRASE = re.compile(r'"([^"]+)"')


def stem(token: str) -> str:
    """Plurals only. Anything more aggressive mangles the short queries people type."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenise(text: str) -> list[str]:
    return [stem(t) for t in _WORD.findall((text or "").lower())
            if len(t) > 1 and t not in STOPWORDS]


@dataclass
class Hit:
    article: dict
    score: float
    matched: list[str]
    snippet: str


def _searchable(article: dict) -> dict[str, str]:
    summaries = article.get("all_summaries") or [article.get("summary") or ""]
    return {
        "title": article.get("title") or "",
        "source": " ".join(filter(None, [article.get("source"), article.get("source_raw")])),
        "focus_area": article.get("focus_area") or "",
        "summary": " ".join(summaries),
        "note": article.get("note") or "",
    }


class SearchIndex:
    def __init__(self, articles: list[dict]):
        self.articles = articles
        self.by_id = {a["id"]: a for a in articles}

        self._docs: list[Counter] = []
        for article in articles:
            counts: Counter = Counter()
            for field, text in _searchable(article).items():
                weight = FIELD_WEIGHTS[field]
                for token in tokenise(text):
                    counts[token] += weight
            self._docs.append(counts)

        self._lengths = [sum(d.values()) or 1 for d in self._docs]
        self._avg_len = (sum(self._lengths) / len(self._lengths)) if self._lengths else 1.0
        doc_freq: Counter = Counter()
        for doc in self._docs:
            doc_freq.update(doc.keys())
        total = len(self._docs)
        self._idf = {t: math.log(1 + (total - n + 0.5) / (n + 0.5))
                     for t, n in doc_freq.items()}

    def search(self, query: str, *, focus_area: str | None = None,
               source: str | None = None, since: str | None = None,
               until: str | None = None, limit: int = 20) -> list[Hit]:
        terms = set(tokenise(query))
        phrases = [p.lower().strip() for p in _PHRASE.findall(query) if p.strip()]
        hits: list[Hit] = []

        for i, article in enumerate(self.articles):
            if not matches_filters(article, focus_area, source, since, until):
                continue
            counts, length = self._docs[i], self._lengths[i]
            score, matched = 0.0, []
            for term in terms:
                freq = counts.get(term, 0)
                if not freq:
                    continue
                matched.append(term)
                norm = freq * (K1 + 1) / (
                    freq + K1 * (1 - B + B * length / self._avg_len))
                score += self._idf.get(term, 0.0) * norm

            if phrases:
                fields = _searchable(article)
                haystack = f"{fields['title']} {fields['summary']} {fields['note']}".lower()
                if not all(phrase in haystack for phrase in phrases):
                    continue          # quotes mean the phrase is required, not preferred
                score += 5.0 * len(phrases)   # a strong signal on a collection this small

            if score <= 0:
                continue
            hits.append(Hit(article, score, sorted(matched), snippet(article, terms)))

        hits.sort(key=lambda h: (-h.score, h.article.get("published_iso")
                                 or h.article.get("first_seen") or ""))
        return hits[:limit]

    def browse(self, *, focus_area: str | None = None, source: str | None = None,
               since: str | None = None, until: str | None = None,
               limit: int = 500) -> list[dict]:
        """Filters with no query, newest first."""
        rows = [a for a in self.articles
                if matches_filters(a, focus_area, source, since, until)]
        rows.sort(key=lambda a: (a.get("published_iso") or a.get("first_seen") or ""),
                  reverse=True)
        return rows[:limit]


def matches_filters(article: dict, focus_area, source, since, until) -> bool:
    if focus_area and (article.get("focus_area") or "").lower() != focus_area.lower():
        return False
    if source and source.lower() not in (article.get("source") or "").lower():
        return False
    when = article.get("published_iso") or article.get("first_seen") or ""
    if since and when < since:
        return False
    if until and when > until:
        return False
    return True


def snippet(article: dict, terms: set[str], words_wide: int = 42) -> str:
    """The stretch of summary carrying the most query terms."""
    text = article.get("summary") or ""
    words = text.split()
    if not terms or len(words) <= words_wide:
        return text
    marks = [any(stem(t) in terms for t in _WORD.findall(w.lower())) for w in words]
    best_start, best_hits = 0, -1
    for start in range(0, len(words) - words_wide + 1, 3):
        found = sum(marks[start:start + words_wide])
        if found > best_hits:
            best_start, best_hits = start, found
    out = " ".join(words[best_start:best_start + words_wide])
    if best_start:
        out = "… " + out
    if best_start + words_wide < len(words):
        out += " …"
    return out
