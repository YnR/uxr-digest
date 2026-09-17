"""Question answering over the parsed digest.

Retrieval is always local. If the `anthropic` SDK is installed and credentials
are available, the retrieved articles are handed to Claude for a written
answer; otherwise the endpoint returns the ranked articles on their own so the
reader still works with no setup.
"""

from __future__ import annotations

import math
import re
from collections import Counter

MODEL = "claude-opus-5"
MAX_CONTEXT_ARTICLES = 12

STOPWORDS = {
    "a", "about", "all", "an", "and", "any", "are", "as", "at", "be", "been",
    "but", "by", "can", "did", "do", "does", "for", "from", "has", "have",
    "how", "i", "in", "is", "it", "its", "me", "of", "on", "or", "say", "should",
    "so", "tell", "that", "the", "their", "them", "there", "these", "they",
    "this", "to", "was", "we", "were", "what", "when", "where", "which", "who",
    "why", "will", "with", "you", "your",
}

SYSTEM_PROMPT = (
    "You answer questions about a UX research news digest. You are given the "
    "digest entries that best match the question: each has a title, source, "
    "date and the digest's own summary of the article. Answer only from those "
    "entries. Cite the articles you use by title. If the entries do not cover "
    "the question, say so plainly rather than guessing — the reader can widen "
    "the search themselves. Keep the answer short and concrete."
)


def _tokenise(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOPWORDS]


def rank_articles(question: str, articles: list[dict], limit: int = MAX_CONTEXT_ARTICLES) -> list[dict]:
    """Plain BM25-flavoured scoring over title, source, focus area and summary."""
    query = _tokenise(question)
    if not query:
        return articles[:limit]

    docs = [
        _tokenise(" ".join([a["title"], a["source"], a["focus_area"], a["summary"], a.get("note") or ""]))
        for a in articles
    ]
    counts = [Counter(d) for d in docs]
    lengths = [len(d) or 1 for d in docs]
    avg_len = sum(lengths) / len(lengths)
    total = len(docs)
    doc_freq = Counter(term for doc in docs for term in set(doc))

    k1, b = 1.5, 0.75
    scored = []
    for index, article in enumerate(articles):
        score = 0.0
        for term in set(query):
            freq = counts[index].get(term, 0)
            if not freq:
                continue
            idf = math.log(1 + (total - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            norm = freq * (k1 + 1) / (freq + k1 * (1 - b + b * lengths[index] / avg_len))
            score += idf * norm
        # A title match is worth more than a body match.
        title_terms = set(_tokenise(article["title"]))
        score += 1.5 * len(title_terms & set(query))
        if score > 0:
            scored.append((score, index, article))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return [article for _, _, article in scored[:limit]]


def _format_context(articles: list[dict]) -> str:
    blocks = []
    for index, article in enumerate(articles, start=1):
        date = article["published_iso"] or article["published_raw"] or f"digest {article['first_seen']}"
        blocks.append(
            f"[{index}] {article['title']}\n"
            f"Source: {article['source']} | Published: {date} | "
            f"Focus area: {article['focus_area']}\n"
            f"URL: {article['url'] or 'n/a'}\n"
            f"Digest summary: {article['summary']}"
        )
    return "\n\n".join(blocks)


def _claude_client():
    try:
        import anthropic
    except ImportError:
        return None, "install-sdk"
    try:
        return anthropic.Anthropic(), None
    except Exception:  # unreadable credentials
        return None, "no-credentials"


def _is_auth_error(error: Exception) -> bool:
    return isinstance(error, TypeError) and "authentication" in str(error).lower()


def _create(client, question: str, matches: list[dict]):
    """Ask Claude, falling back to a plainer request if the account rejects the extras."""
    messages = [
        {
            "role": "user",
            "content": f"Digest entries:\n\n{_format_context(matches)}\n\nQuestion: {question}",
        }
    ]
    try:
        return client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            # Low effort: a short read over a dozen short summaries.
            output_config={"effort": "low"},
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
        # Older SDK or an account without those betas: the plain request still works.
        return client.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM_PROMPT, messages=messages
        )


def answer(question: str, articles: list[dict]) -> dict:
    matches = rank_articles(question, articles)
    result = {"question": question, "matches": matches, "answer": None, "notice": None}

    if not matches:
        result["notice"] = "Nothing in the digest matches those words. Try a different phrasing."
        return result

    client, problem = _claude_client()
    if problem == "install-sdk":
        result["notice"] = (
            "Showing the best keyword matches. For written answers, run "
            "`pip install anthropic` and set ANTHROPIC_API_KEY, then restart the reader."
        )
        return result
    if problem == "no-credentials":
        result["notice"] = (
            "Showing the best keyword matches. Set ANTHROPIC_API_KEY (or run `ant auth login`) "
            "for written answers."
        )
        return result

    try:
        response = _create(client, question, matches)
    except Exception as error:  # network, auth, rate limit — the matches still stand
        if _is_auth_error(error):
            result["notice"] = (
                "Showing the best keyword matches. Set ANTHROPIC_API_KEY for written answers."
            )
        else:
            result["notice"] = (
                f"Keyword matches only — the Claude request failed "
                f"({error.__class__.__name__}: {error})."
            )
        return result

    if getattr(response, "stop_reason", None) == "refusal":
        result["notice"] = "Claude declined to answer that one. The keyword matches are below."
        return result

    result["answer"] = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    return result
