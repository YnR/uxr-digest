# Digest reader

A local web app for reading the digests in `posts/`. It parses the markdown
into article records, lists them with filters, links each one to its source,
and answers questions about them.

## Run it

```bash
python3 reader/server.py
```

That parses `posts/`, serves the reader on <http://127.0.0.1:8765> and opens a
browser. Nothing is installed and nothing leaves the machine. Useful flags:
`--port`, `--host`, `--posts <dir>`, `--no-browser`.

Edit or add a post and reload the page — the server re-parses whenever a file
in `posts/` changes.

## Searching

Typing in the filter box ranks every article against the query rather than
filtering on substrings, so "researchers" finds "research" and the best match
comes first instead of the most recent. Results carry the stretch of summary
the query matched. Quoting a phrase makes it required: `"synthetic users"`
returns only articles whose text actually contains it.

Ranking lives in `reader/search.py` (BM25 over title, source, focus area and
summary, with the title weighted highest) and is served from `/api/search`.
The focus-area and source checkboxes still apply on top of a ranked result.

## Asking questions

The ask box always works: it ranks the digest entries against the question and
shows the closest ones. For a written answer on top of those entries:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...      # or: ant auth login
python3 reader/server.py
```

Claude only sees the passages that match the question, and is told to answer
from them alone and to cite what it used. Without the key the reader falls back
to the ranked passages and says so.

### Summaries, or the articles themselves

`posts/` holds the digest's own summaries and never the article text. A summary
is one paragraph of the digest author's framing, so a question about a sample
size, a method, or what an article actually recommends cannot be answered from
it. So the reader does both, and the choice is yours per question:

| Setting | What it reads | Network |
| --- | --- | --- |
| `never` | the digest summaries | no |
| `cached` (default) | summaries, plus any source page already fetched | no |
| `fetch` — the **consult source pages** tickbox | summaries, plus the pages of the articles in play | yes |

The default answers from summaries and says plainly when the answer is not in
them, naming the article whose page would need reading. Ticking the box is the
one explicit step to go and read it.

Fetching takes one article at a time, never the whole collection, honours
`robots.txt`, and caches the text under `.cache/source-pages/` — which is
git-ignored, so the repo stays summaries-only. Paywalled and JavaScript-only
pages come back too thin to use and say so rather than answering from nothing.
`POST /api/fetch {"article_id": "…"}` fetches one on its own.

## What the parser handles

`reader/digest_parser.py` reads every `posts/YYYY-MM-DD[-suffix].md` file. The
entry format drifted over the life of the digest, so three shapes are parsed:

| Shape | Example |
| --- | --- |
| A (newer) | `**Title** — [Source](url) *(Aug 18)*` |
| B (older) | `**[Title — Source (Jul 24)](url)**` |
| C (rare)  | `**"Title" — Source (Aug 11)**` with the link in the summary's `([Read →](url))` |

Section headings drifted too (`## Focus Area 2: …` and `## 2. …`, with varying
wording); all of them fold onto the three standing focus areas.

Each article record carries title, url, source, publication date (raw and
best-effort ISO), focus area, the digest's summary, any italic aside, and which
digest it first appeared in. An article that appears in more than one post
becomes a single record dated to its first sighting, with the repeats listed —
the same rule `CLAUDE.md` sets for writing the digest. Every summary written
about it is kept in `all_summaries`, because a later digest often describes the
same article more fully, and all of them are searchable and usable as grounding.

Identity is the article's URL, so a later digest retitling a piece still folds
onto one record. The exception is a bare section URL: a couple of entries cite
`nngroup.com/articles/` for two different articles, and keyed on the URL alone
one of those articles disappears, so those fall back to URL plus title.

Source names are folded too, so `NN/G`, `NN/g` and `Nielsen Norman Group` are
one filter entry.

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests run against the real posts: every bold entry parses, every article
ends up with a URL and a summary, each of the three entry shapes is checked by
name, and the date and dedup rules have their own cases. `test_search_and_ask.py`
covers ranking, stemming, required phrases and filters, the source cache and its
HTML extraction, and the grounding rules — none of it touches the network.
