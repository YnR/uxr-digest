"""Parse the digest posts in `posts/` into structured article records.

The posts were written by hand over several weeks and the entry format drifted.
Three shapes appear:

  A (newer)  **Title** — [Source](url) *(Aug 18)*
  B (older)  **[Title — Source (Jul 24)](url)**
  C (rare)   **"Title" — Source (Aug 11)**
             Summary text ... ([Read →](url))

Section headings drifted too: `## Focus Area 2: ...` and `## 2. ...` both occur,
with slightly different wording for the same area.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import date

POSTS_DIRNAME = "posts"

# Canonical focus areas, keyed by the number used in the headings.
FOCUS_AREAS = {
    1: "AI in the Research Practice",
    2: "Research for AI-Powered Products",
    3: "UX Research Job Market",
}
UNCATEGORISED = "Uncategorised"

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:-(.+))?\.md$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BOLD_LEAD_RE = re.compile(r"^\*\*(.+?)\*\*(.*)$")
FULL_LINK_RE = re.compile(r"^\[(.+)\]\((\S+?)\)$")
# **Title** — [Source](url) *(date)*
SOURCE_LINK_RE = re.compile(
    r"^\s*[—–-]\s*\[([^\]]+)\]\((\S+?)\)\s*(?:\*\(([^)]*)\)\*)?\s*$"
)
READ_LINK_RE = re.compile(r"\(\[[^\]]*\]\((\S+?)\)\)\s*$")
ITALIC_NOTE_RE = re.compile(r"^\*\((.+)\)\*$")
# The posts name the same publication several ways; fold them for filtering.
SOURCE_ALIASES = {
    "nn/g": "Nielsen Norman Group",
    "nn/g, aug 7": "Nielsen Norman Group",
    "nng": "Nielsen Norman Group",
    "nielsen norman group": "Nielsen Norman Group",
    "dscout": "People Nerds (dscout)",
    "people nerds (dscout)": "People Nerds (dscout)",
    "ux collective newsletter": "UX Collective",
    "ux collective": "UX Collective",
    "the user research strategist, nikki anderson": "The User Research Strategist",
    "the user research strategist": "The User Research Strategist",
    "jan ahrend / user weekly": "User Weekly (Jan Ahrend)",
}


def canonical_source(name: str) -> str:
    cleaned = (name or "").strip()
    return SOURCE_ALIASES.get(cleaned.lower(), cleaned)


TRACKING_PARAMS = ("utm_", "ref_src", "ref_url", "fbclid", "gclid", "source=")


@dataclass
class Article:
    id: str
    title: str
    url: str | None
    source: str
    source_raw: str
    published_raw: str | None
    published_iso: str | None
    focus_area: str
    focus_area_raw: str
    summary: str
    note: str | None
    first_seen: str          # digest date the article first appeared in
    first_seen_file: str
    repeats: list[str] = field(default_factory=list)   # later digests repeating it
    # Every digest summary written about this article, first appearance first.
    all_summaries: list[str] = field(default_factory=list)
    parse_format: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Digest:
    date: str
    file: str
    title: str
    intro: str
    footer: str
    article_count: int = 0
    empty_sections: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _canonical_focus_area(heading: str) -> tuple[str, str]:
    """Return (canonical name, raw heading text) for a `##` heading."""
    raw = heading.strip()
    m = re.match(r"^(?:Focus Area\s*)?(\d)[.:]\s*(.*)$", raw)
    if m:
        number = int(m.group(1))
        return FOCUS_AREAS.get(number, m.group(2).strip()), raw
    lowered = raw.lower()
    for number, name in FOCUS_AREAS.items():
        if name.lower() in lowered:
            return name, raw
    if "job market" in lowered:
        return FOCUS_AREAS[3], raw
    return raw, raw


def _looks_like_date(text: str) -> bool:
    lowered = text.lower()
    if any(month in lowered for month in MONTHS):
        return True
    return bool(re.search(r"\b(19|20)\d{2}\b", text))


def _parse_date(raw: str | None, fallback_year: int) -> str | None:
    """Best-effort ISO date from strings like 'Aug 18', 'Sep 2026', 'Apr 2, 2026'."""
    if not raw:
        return None
    text = raw.replace("–", "-").replace("—", "-")
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    year = int(year_match.group(0)) if year_match else fallback_year
    month, month_match = None, None
    for candidate in re.finditer(r"[A-Za-z]{3,9}", text):
        found = MONTHS.get(candidate.group(0).lower())
        if found:
            month, month_match = found, candidate
            break
    if month is None:
        return None
    # First standalone 1-2 digit number after the month name is the day.
    tail = text[month_match.end():]
    day_match = re.search(r"\b(\d{1,2})\b", tail)
    if not day_match:
        return f"{year:04d}-{month:02d}"
    day = int(day_match.group(1))
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return f"{year:04d}-{month:02d}"


def _source_from_url(url: str | None) -> str:
    if not url:
        return "Unknown source"
    host = re.sub(r"^https?://", "", url).split("/")[0]
    return host[4:] if host.startswith("www.") else host


def _split_title_tail(text: str) -> tuple[str, str]:
    """Split '<title> — <source and date>' on the last em dash."""
    parts = re.split(r"\s+[—–]\s+", text)
    if len(parts) == 1:
        return text.strip(), ""
    return " — ".join(parts[:-1]).strip(), parts[-1].strip()


def _split_source_date(tail: str) -> tuple[str, str | None]:
    """Pull a date out of tails like 'NN/G (Jul 24)' or 'NN/g, Aug 7'."""
    tail = tail.strip()
    if not tail:
        return "", None
    paren = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", tail)
    if paren:
        head, inner = paren.group(1).strip(), paren.group(2).strip()
        if _looks_like_date(inner):
            return head, inner
        # e.g. 'Updated July 2026 (User Interviews)' — the parenthetical is the source.
        if _looks_like_date(head):
            return inner, head
        return f"{head} ({inner})".strip(), None
    if "," in tail:
        head, _, last = tail.rpartition(",")
        if _looks_like_date(last):
            return head.strip(), last.strip()
    return tail, None


def _strip_quotes(text: str) -> str:
    return text.strip().strip('"').strip("“”").strip()


def _normalise_url(url: str | None) -> str | None:
    if not url:
        return None
    cleaned = url.strip().rstrip(").,")
    cleaned = re.sub(r"^https?://", "", cleaned)
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    cleaned = cleaned.split("#")[0]
    if "?" in cleaned:
        base, _, query = cleaned.partition("?")
        kept = [p for p in query.split("&") if not p.lower().startswith(TRACKING_PARAMS)]
        cleaned = base + ("?" + "&".join(kept) if kept else "")
    return cleaned.rstrip("/").lower()


# Last path segments that name a section index rather than one article.
INDEX_SEGMENTS = {"articles", "article", "blog", "posts", "post", "news", "p"}


def _is_section_url(normalised: str) -> bool:
    """True when the URL points at a section index rather than one article."""
    parts = [p for p in normalised.split("/") if p]
    return len(parts) < 2 or parts[-1] in INDEX_SEGMENTS


def _make_id(url: str | None, title: str, source: str) -> str:
    """Identity is the URL, which survives a later digest retitling an article.

    Some entries cite a bare section URL (nngroup.com/articles/) for more than
    one article, so those fall back to url+title — keyed on the URL alone they
    would collapse into a single record and one of the articles would vanish.
    """
    normalised = _normalise_url(url)
    if not normalised:
        seed = f"{title.lower()}|{source.lower()}"
    elif _is_section_url(normalised):
        seed = f"{normalised}|{title.strip().lower()}"
    else:
        seed = normalised
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def _parse_entry_head(bold: str, rest: str) -> dict | None:
    """Parse the bold line that opens an article entry."""
    link_in_rest = SOURCE_LINK_RE.match(rest)
    if link_in_rest:  # format A
        source, url, published = link_in_rest.groups()
        return {
            "title": _strip_quotes(bold),
            "source": source.strip(),
            "url": url,
            "published_raw": published.strip() if published else None,
            "parse_format": "A",
        }

    full_link = FULL_LINK_RE.match(bold.strip())
    if full_link:  # format B
        text, url = full_link.groups()
        title, tail = _split_title_tail(text)
        source, published = _split_source_date(tail)
        return {
            "title": _strip_quotes(title),
            "source": source or _source_from_url(url),
            "url": url,
            "published_raw": published,
            "parse_format": "B",
        }

    if rest.strip() in ("", ":"):  # format C — url lives in the summary
        title, tail = _split_title_tail(bold)
        source, published = _split_source_date(tail)
        if not tail:
            return None
        return {
            "title": _strip_quotes(title),
            "source": source,
            "url": None,
            "published_raw": published,
            "parse_format": "C",
        }
    return None


def _clean_summary(lines: list[str]) -> tuple[str, str | None, str | None]:
    """Return (summary, note, url found in a trailing '([Read →](url))')."""
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    note = None
    if lines and ITALIC_NOTE_RE.match(lines[0].strip()):
        note = ITALIC_NOTE_RE.match(lines[0].strip()).group(1).strip()
        lines = lines[1:]
    url = None
    if lines:
        trailing = READ_LINK_RE.search(lines[-1])
        if trailing:
            url = trailing.group(1)
            lines[-1] = READ_LINK_RE.sub("", lines[-1]).strip()
    return "\n\n".join(line.strip() for line in lines if line.strip()), note, url


def parse_post(path: str) -> tuple[Digest, list[Article]]:
    name = os.path.basename(path)
    m = FILENAME_RE.match(name)
    if not m:
        raise ValueError(f"unexpected post filename: {name}")
    year, month, day, suffix = m.groups()
    digest_date = f"{year}-{month}-{day}"

    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")

    title = ""
    intro_lines: list[str] = []
    footer_lines: list[str] = []
    focus_area, focus_area_raw = UNCATEGORISED, ""
    empty_sections: list[str] = []
    articles: list[Article] = []
    seen_heading = False

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        heading = HEADING_RE.match(line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2)
            if level == 1:
                title = text
            else:
                seen_heading = True
                focus_area, focus_area_raw = _canonical_focus_area(text)
            index += 1
            continue

        bold = BOLD_LEAD_RE.match(line) if stripped.startswith("**") else None
        if bold:
            head = _parse_entry_head(bold.group(1), bold.group(2))
            if head:
                body: list[str] = []
                index += 1
                while index < len(lines):
                    nxt = lines[index]
                    if nxt.strip().startswith(("**", "#", "---")):
                        break
                    body.append(nxt)
                    index += 1
                summary, note, body_url = _clean_summary(body)
                url = head["url"] or body_url
                articles.append(
                    Article(
                        id=_make_id(url, head["title"], head["source"]),
                        title=head["title"],
                        url=url,
                        source=canonical_source(head["source"]) or _source_from_url(url),
                        source_raw=head["source"] or _source_from_url(url),
                        published_raw=head["published_raw"],
                        published_iso=_parse_date(head["published_raw"], int(year)),
                        focus_area=focus_area,
                        focus_area_raw=focus_area_raw or focus_area,
                        summary=summary,
                        note=note,
                        first_seen=digest_date,
                        first_seen_file=name,
                        parse_format=head["parse_format"],
                    )
                )
                continue

        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            body_text = stripped.strip("*").strip()
            if body_text.lower().startswith("nothing new"):
                empty_sections.append(focus_area)
            elif seen_heading:
                footer_lines.append(body_text)
            else:
                intro_lines.append(body_text)
            index += 1
            continue

        if stripped and not seen_heading and not stripped.startswith("---"):
            intro_lines.append(stripped)
        index += 1

    digest = Digest(
        date=digest_date,
        file=name,
        title=title or f"UX Research Digest — {digest_date}",
        intro=" ".join(intro_lines).strip(),
        footer=" ".join(footer_lines).strip(),
        article_count=len(articles),
        empty_sections=sorted(set(empty_sections)),
    )
    if suffix:
        digest.file = name
    return digest, articles


def _sort_key(path: str) -> tuple:
    name = os.path.basename(path)
    m = FILENAME_RE.match(name)
    year, month, day, suffix = m.groups()
    # A catch-up post covers everything before its own date, so it comes first.
    return (f"{year}-{month}-{day}", 0 if suffix else 1)


def load_digest(posts_dir: str) -> dict:
    """Parse every post and fold repeated URLs into a single article record."""
    paths = sorted(
        (
            os.path.join(posts_dir, name)
            for name in os.listdir(posts_dir)
            if name.endswith(".md") and FILENAME_RE.match(name)
        ),
        key=_sort_key,
    )

    digests: list[Digest] = []
    by_key: dict[str, Article] = {}
    ordered: list[Article] = []
    duplicate_count = 0

    for path in paths:
        digest, articles = parse_post(path)
        digests.append(digest)
        for article in articles:
            # article.id already encodes the identity rule, including the
            # section-URL case where two articles are cited under one URL.
            key = article.id
            existing = by_key.get(key)
            if existing:
                duplicate_count += 1
                if digest.date not in existing.repeats:
                    existing.repeats.append(digest.date)
                # A later digest often writes a fuller summary of the same
                # article. Keep them all — they are extra grounding for Q&A.
                if article.summary and article.summary not in existing.all_summaries:
                    existing.all_summaries.append(article.summary)
                if len(article.summary or "") > len(existing.summary or ""):
                    existing.summary = article.summary
                if not existing.note and article.note:
                    existing.note = article.note
                if not existing.published_raw and article.published_raw:
                    existing.published_raw = article.published_raw
                    existing.published_iso = article.published_iso
                continue
            if article.summary:
                article.all_summaries.append(article.summary)
            by_key[key] = article
            ordered.append(article)

    ordered.sort(key=lambda a: (a.published_iso or a.first_seen, a.first_seen), reverse=True)

    sources = sorted({a.source for a in ordered}, key=str.lower)
    areas = [name for name in FOCUS_AREAS.values() if any(a.focus_area == name for a in ordered)]
    areas += sorted({a.focus_area for a in ordered} - set(areas))

    return {
        "articles": [a.as_dict() for a in ordered],
        "digests": [d.as_dict() for d in sorted(digests, key=lambda d: d.date, reverse=True)],
        "sources": sources,
        "focus_areas": areas,
        "stats": {
            "articles": len(ordered),
            "digests": len(digests),
            "duplicates_folded": duplicate_count,
            "missing_url": sum(1 for a in ordered if not a.url),
            "first_digest": digests[0].date if digests else None,
            "last_digest": digests[-1].date if digests else None,
        },
    }


def default_posts_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), POSTS_DIRNAME)


if __name__ == "__main__":
    import json
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else default_posts_dir()
    print(json.dumps(load_digest(target)["stats"], indent=2))
