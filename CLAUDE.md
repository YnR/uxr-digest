# UX Research Digest — Project Notes

## Deduplication rule

Before publishing any digest, read the existing posts in `posts/` and collect every article URL that has already appeared. **Do not include any article in today's post if its URL has appeared in any previous post.** Each article must appear exactly once across all digests — the day it first enters the 24–48 hour window.

If removing repeats leaves a section empty, write "Nothing new from the monitored sources in this window." rather than carrying forward old material.

## Sources

`sources.json` in the repo root is the list. Read it at the start of every run
and check every entry whose `"monitored"` is `true`, using its `url`. There is
no second list anywhere: add, remove or rename a source by editing that file, so
the digest, the reader app in `reader/`, and anything else built on this repo all
move together.

When crediting a source in a post, use its `name` from `sources.json` — the
reader groups articles by it. Citing something the file does not list is fine;
add it to the file in the same commit with `"monitored": false`, so the next run
knows the name without having to guess at it.

## Commit target

All digest posts go directly to `main`. Do not commit to a feature branch.
