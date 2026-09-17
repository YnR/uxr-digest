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

## Asking questions

The ask box always works: it ranks the digest entries against the question and
shows the closest ones. For a written answer on top of those entries:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...      # or: ant auth login
python3 reader/server.py
```

Claude only sees the dozen entries that match the question, and is told to
answer from them alone and to cite the articles it used. Without the key the
reader falls back to the ranked list and says so.

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
digest it first appeared in. A URL that appears in more than one post becomes a
single record dated to its first sighting, with the repeats listed — the same
rule `CLAUDE.md` sets for writing the digest.

Source names are folded too, so `NN/G`, `NN/g` and `Nielsen Norman Group` are
one filter entry.

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests run against the real posts: every bold entry parses, every article
ends up with a URL and a summary, each of the three entry shapes is checked by
name, and the date and dedup rules have their own cases.
