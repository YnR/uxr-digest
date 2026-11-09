# Maintaining the AI evals resources page

How to add or edit entries on [`README.md`](README.md), the page published at
<https://ynr.github.io/uxr-digest/evals/>. These are Yann's rules; this file is
not published.

## Adding a resource

Add the new entry in date order (oldest first) and add a row to the
"At a glance" table. Record:

- **Author / Author(s)** for writing, or **Speaker / Speakers** for talks,
  podcasts and interview pieces (list the people interviewed as speakers, with
  their role in brackets).
- **Affiliation(s):** the organization each person was at when the piece was
  published, and nothing else: no caveats, sourcing notes or career history.
  Use a role in brackets only when it adds something (for example
  "Google (UX Research Manager, Google Docs)"). With several people, write
  "Name: Org. Name: Org." If someone had no affiliation, or it is not known,
  leave them out rather than writing "unknown"; check LinkedIn if in doubt.
- **Find them:** links to their blog and/or LinkedIn.
- **Format:** Article, Podcast or Presentation, with a short note in brackets.
- **Published:** the exact publication date as `YYYY-MM-DD`. For a video, use
  the date it was published. If you cannot find it, ask Yann rather than
  estimating.
- **What it adds:** what the piece contributes to the conversation about AI
  evals, specific enough to be useful on its own (concrete frameworks, cases,
  findings). A bulleted breakdown under the opening paragraph is fine for long
  talks.

Add an **In context** section when later work has moved the conversation on
(for example, Lick's 2023 article predates LLM-as-judge evals and user evals).

## Overlapping resources

If two contributions overlap a lot, the **oldest** is the canonical entry and
the newer one goes under it as a related take
(`### Na. Related take: Title`) from a different person. A related take has the
same field list and a **How it differs** section. Do not add a "Why it sits
under…" paragraph. If a newer find turns out to be older than the current
canonical entry, swap them so the oldest leads the group.

## Sourcing

Do not guess. If a page cannot be fetched (YouTube and Medium often fail from
the cloud environment), ask Yann to paste the text or a summary, then write
the entry from that. Do not leave notes on the page about how a summary was
sourced or what could not be read.

## Page shape

Keep the intro short; no notes about methodology. Keep each entry to the same
shape (a `## N.` or `### Na. Related take:` heading, the `- **Field:**` list,
then sections that open with a bold lead-in such as `**What it adds.**`),
because `reader/evals_resources.py` builds the published page, the RSS and JSON
feeds and `resources.json` from it. Run `python -m unittest discover -s tests`
before pushing.

## Publishing

Merging to `main` rebuilds and deploys the page and its feeds through
`.github/workflows/feeds.yml`. Yann asks for the merge; open a pull request
otherwise.
