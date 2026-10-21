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

## Feeds for other clients

The digest is also published as a stream any feed reader or script can
consume. Each article is one item: its title, a link to the article, the
digest's short summary, the date it entered the digest, its focus area and its
source. Repeats are folded, so an article appears once.

It comes in two formats with the same items:

- **RSS 2.0** (`.xml`) for feed readers. The summary is the item description
  (with an HTML version in `content:encoded`), and the focus area and source
  are `<category>` elements whose `domain` ends in `#focus-area` or `#source`.
- **JSON Feed 1.1** (`.json`) for apps and scripts. Each item adds a `_uxr`
  object with `focus_area`, `source`, `source_id` and `source_url` (from
  `sources.json`), `author`, `published` (the article's own
  date, when the digest gives one), `digest_date` and `note`.

Published on GitHub Pages by `.github/workflows/feeds.yml` on every push to
`main`, at `https://ynr.github.io/uxr-digest/`:

| Path | What |
| --- | --- |
| `feed.xml`, `feed.json` | everything, newest first |
| `topics/<slug>.xml` / `.json` | one per focus area |
| `sources/<slug>.xml` / `.json` | one per publication |
| `months/<YYYY-MM>.xml` / `.json` | the archive by digest month |
| `feeds.opml` | every RSS feed, to import into a reader in one go |
| `index.json` | catalogue of all feeds with item counts |
| `digest.json` | the full parse, for scripts |

Build them yourself with `python3 reader/feeds.py --out _site`. The local
server also serves the stream live with any combination of filters:
`/feed.xml` or `/feed.json`, taking `topic`, `source`, `month`, `since` and
`until`, for example
`http://127.0.0.1:8765/feed.xml?topic=UX+Research+Job+Market&since=2026-09-01`.

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

Source names come from `sources.json` (see below), so `NN/G`, `NN/g`,
`Nielsen Norman Group` and the byline form `Tanner Kohler, Nielsen Norman Group`
are one filter entry.

## Sources

`sources.json` in the repo root is the project's one list of sources: what the
scheduled digest task checks, and what this app groups and filters by. Nothing
keeps a second copy. `reader/source_registry.py` reads it; `reader/sources.py`,
despite the name, is the separate business of fetching one article's own page.

| Field | Meaning |
| --- | --- |
| `id` | stable short key, safe to reference from other tools |
| `name` | what posts should call the source, and what the reader groups by |
| `url` | the page the digest checks; `null` when the source has no stable one |
| `monitored` | `true` if the scheduled task should check it every run |
| `domains` | hosts belonging to the source, used to fold bylined credits |
| `aliases` | other names posts have used for it |

A cited source is matched to an entry by its article's host first, then by an
exact name or alias, then by a name quoted inside a longer credit — which is why
`Patrick Neeman, UX Collective` groups under UX Collective. A source the file
does not list keeps the name the post gave it and shows up under "cited, not
monitored", rather than quietly joining a monitored one.

The sidebar lists the monitored sources first, each one linked and counted,
including any that have produced nothing — that a monitored source has yielded
no articles is worth seeing. Sources that are only cited appear below, once
something cites them.

Adding a source is one edit to `sources.json`. Reload the page and the filters
follow; the next digest run picks it up with no prompt change.

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests run against the real posts: every bold entry parses, every article
ends up with a URL and a summary, each of the three entry shapes is checked by
name, and the date and dedup rules have their own cases. `test_search_and_ask.py`
covers ranking, stemming, required phrases and filters, the source cache and its
HTML extraction, and the grounding rules — none of it touches the network.
`test_source_registry.py` covers the registry: the real `sources.json` parses,
the matching rules hold, and a missing file degrades instead of raising.
