"""Question answering over the parsed digest.

Grounding policy — the digest summary is the default, the article's own page
is opt-in:

  "never"   summaries only.
  "cached"  (default) summaries, plus the page of any article already fetched
            and sitting in the local cache. Never touches the network.
  "fetch"   summaries, plus fetch the pages of the articles in play.

Only summaries live in the repo, so anything past the digest author's framing
— a sample size, a method, the actual recommendation — is not there to answer
from. Rather than choose one side once and for all, the default answers from
summaries and says plainly when the answer is not in them, and consulting the
sources is one explicit step away. Fetched text is cached outside the repo and
never committed.

Retrieval is always local. If the `anthropic` SDK is installed and credentials
are available, the retrieved passages are handed to Claude for a written
answer; otherwise they are returned on their own so the reader still works
with no setup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from search import SearchIndex, stem, tokenise
from sources import cached as cached_source
from sources import fetch as fetch_source

MODEL = "claude-opus-5"
MAX_CONTEXT_ARTICLES = 12
MAX_PASSAGES = 16
PASSAGE_CHARS = 900
USE_SOURCE_CHOICES = ("never", "cached", "fetch")

SYSTEM_PROMPT = (
    "You answer questions about a UX research news digest.\n\n"
    "You are given numbered passages. Each is either a digest summary — the "
    "digest author's own words about an article — or an excerpt from the "
    "article's page.\n\n"
    "Rules:\n"
    "- Answer only from the passages. Do not draw on outside knowledge of these "
    "articles.\n"
    "- Cite what you use as [1], [2], and so on.\n"
    "- A digest summary is a characterisation, not the article's own words. If "
    "the question asks for a specific the summaries do not contain, say so and "
    "name the article whose source page would need consulting, rather than "
    "inferring it.\n"
    "- If the passages do not answer the question, say so plainly and say what "
    "is there instead.\n"
    "- Keep the answer short and concrete. No preamble."
)


@dataclass
class Passage:
    text: str
    kind: str          # "summary" | "source"
    article_id: str
    title: str
    origin: str


def _split(text: str, size: int = PASSAGE_CHARS) -> list[str]:
    """Split on paragraph, then sentence boundaries, so passages stay readable."""
    chunks: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}" if current else para
            continue
        if current:
            chunks.append(current)
        while len(para) > size:
            cut = para.rfind(". ", 0, size)
            cut = cut + 1 if cut > size // 2 else size
            chunks.append(para[:cut].strip())
            para = para[cut:].strip()
        current = para
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def gather_passages(articles: list[dict], use_source: str,
                    notices: list[str]) -> list[Passage]:
    passages: list[Passage] = []
    for article in articles:
        summaries = article.get("all_summaries") or [article.get("summary") or ""]
        appearances = [article.get("first_seen", "")] + list(article.get("repeats") or [])
        for i, summary in enumerate(summaries):
            if not summary:
                continue
            when = appearances[i] if i < len(appearances) else article.get("first_seen", "")
            passages.append(Passage(summary, "summary", article["id"], article["title"],
                                    f"digest summary, {when}" if when else "digest summary"))
        if use_source == "never" or not article.get("url"):
            continue

        source = cached_source(article) if use_source == "cached" else fetch_source(article)
        if source is None:
            continue
        if not source.ok:
            notices.append(f"Could not read the source page for “{article['title']}”: "
                           f"{source.error}.")
            continue
        if not source.usable:
            notices.append(f"The source page for “{article['title']}” returned too little "
                           "text to use — likely a paywall or a page that needs JavaScript.")
            continue
        for chunk in _split(source.text):
            passages.append(Passage(chunk, "source", article["id"], article["title"],
                                    "article page"))
    return passages


def rank_passages(passages: list[Passage], question: str,
                  limit: int = MAX_PASSAGES) -> list[Passage]:
    """Keep every summary — they are short and identify the article — then add
    the best-matching source excerpts."""
    terms = set(tokenise(question))
    summaries = [p for p in passages if p.kind == "summary"]
    sources = [p for p in passages if p.kind == "source"]

    def score(passage: Passage) -> float:
        words = [stem(w) for w in re.findall(r"[a-z0-9]+", passage.text.lower())]
        if not words:
            return 0.0
        return sum(1 for w in words if w in terms) / (len(words) ** 0.5)

    sources.sort(key=score, reverse=True)
    room = max(0, limit - len(summaries))
    return summaries[:limit] + sources[:room]


def rank_articles(question: str, articles: list[dict],
                  limit: int = MAX_CONTEXT_ARTICLES) -> list[dict]:
    """The articles a question is about, best first.

    A question with nothing to match on — empty, or all stopwords — falls back
    to the most recent articles rather than answering with nothing.
    """
    if not tokenise(question):
        return articles[:limit]
    return [hit.article for hit in SearchIndex(articles).search(question, limit=limit)]


def _format_context(passages: list[Passage], articles: list[dict]) -> str:
    meta = {a["id"]: a for a in articles}
    blocks = []
    for i, passage in enumerate(passages, start=1):
        article = meta.get(passage.article_id, {})
        kind = "DIGEST SUMMARY" if passage.kind == "summary" else "ARTICLE PAGE EXCERPT"
        date = (article.get("published_iso") or article.get("published_raw")
                or f"digest {article.get('first_seen', '')}")
        blocks.append(
            f"[{i}] {kind} — {passage.title}\n"
            f"Source: {article.get('source', '')} | Published: {date} | "
            f"Focus area: {article.get('focus_area', '')}\n"
            f"URL: {article.get('url') or 'n/a'}\n"
            f"{passage.text}"
        )
    return "\n\n".join(blocks)


def _claude_client():
    try:
        import anthropic
    except ImportError:
        return None, "install-sdk"
    try:
        return anthropic.Anthropic(), None
    except Exception:
        # The SDK raises when it cannot resolve any credential.
        return None, "no-credentials"


def _is_auth_error(error: Exception) -> bool:
    """A missing credential raises TypeError from the constructor; a bad or
    expired one comes back as the SDK's AuthenticationError."""
    if isinstance(error, TypeError) and "authentication" in str(error).lower():
        return True
    try:
        import anthropic
    except ImportError:
        return False
    return isinstance(error, (anthropic.AuthenticationError, anthropic.PermissionDeniedError))


def _create(client, question: str, passages: list[Passage], articles: list[dict],
            effort: str):
    """Ask Claude, falling back to a plainer request if the account rejects the extras."""
    messages = [{
        "role": "user",
        "content": (f"Passages:\n\n{_format_context(passages, articles)}\n\n"
                    f"Question: {question}"),
    }]
    try:
        return client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            output_config={"effort": effort},
            thinking={"type": "adaptive"},
            # Route around a safety refusal rather than failing the request.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        )
    except Exception as error:
        if _is_auth_error(error):
            raise
        import anthropic

        if not isinstance(error, (anthropic.BadRequestError, TypeError)):
            raise
        # Older SDK, or an account without those betas: the plain request still works.
        return client.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM_PROMPT, messages=messages
        )


def answer(question: str, articles: list[dict], *, use_source: str = "cached",
           article_ids: list[str] | None = None) -> dict:
    if use_source not in USE_SOURCE_CHOICES:
        raise ValueError(f"use_source must be one of {USE_SOURCE_CHOICES}")

    notices: list[str] = []
    if article_ids:
        by_id = {a["id"]: a for a in articles}
        matches = [by_id[i] for i in article_ids if i in by_id]
        unknown = [i for i in article_ids if i not in by_id]
        if unknown:
            notices.append("Some of the articles asked about are not in the digest.")
    else:
        matches = rank_articles(question, articles)

    result = {"question": question, "matches": matches, "answer": None,
              "notice": None, "notices": notices, "passages": [],
              "used_source_pages": False}

    if not matches:
        notices.append("Nothing in the digest matches those words. Try a different phrasing.")
        result["notice"] = " ".join(notices)
        return result

    passages = rank_passages(gather_passages(matches, use_source, notices), question)
    used_sources = any(p.kind == "source" for p in passages)
    result["used_source_pages"] = used_sources
    result["passages"] = [{"kind": p.kind, "article_id": p.article_id,
                           "title": p.title, "origin": p.origin, "text": p.text}
                          for p in passages]

    if use_source == "cached" and not used_sources:
        notices.append("Answered from digest summaries only. Turn on “consult source "
                       "pages” to read the articles themselves.")

    client, problem = _claude_client()
    if problem == "install-sdk":
        notices.append("Showing the best matches. For written answers, run "
                       "`pip install anthropic` and set ANTHROPIC_API_KEY, then restart.")
        result["notice"] = " ".join(notices)
        return result
    if problem == "no-credentials":
        notices.append("Showing the best matches. Set ANTHROPIC_API_KEY (or run "
                       "`ant auth login`) for written answers.")
        result["notice"] = " ".join(notices)
        return result

    # Source excerpts are long; summaries alone are a short read.
    effort = "medium" if used_sources else "low"
    try:
        response = _create(client, question, passages, matches, effort)
    except Exception as error:   # network, auth, rate limit — the matches still stand
        if _is_auth_error(error):
            notices.append("Showing the best matches. Set ANTHROPIC_API_KEY for "
                           "written answers.")
        else:
            notices.append(f"Matches only — the Claude request failed "
                           f"({error.__class__.__name__}: {error}).")
        result["notice"] = " ".join(notices)
        return result

    if getattr(response, "stop_reason", None) == "refusal":
        notices.append("Claude declined to answer that one. The matches are below.")
        result["notice"] = " ".join(notices)
        return result

    result["answer"] = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()
    result["notice"] = " ".join(notices) or None
    return result
