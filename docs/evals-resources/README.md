# AI Evals Resources

A running collection of writing, talks and videos on evaluating AI systems, with
a focus on what UX research and design bring to evals. Each entry records who
made the argument, where they worked when they published it, where to find them,
the format, and what the piece adds to the conversation.

*Last updated: 2026-11-09.*

## How this page is organized

- **Chronological, oldest first**, so the conversation reads in the order it
  developed.
- **Overlapping pieces are grouped.** When two contributions cover much of the
  same ground, the older one is the canonical entry and the newer one is listed
  under it as a *related take* from a different person, with a note on how it
  differs.
- **Only what could be checked.** Details come from the resource itself or the
  author's own pages. Where a page could not be fetched, or a detail was not
  stated, the entry says so instead of filling the gap.

## At a glance

| # | Resource | Author(s) | Company at publication | Format | Published |
|---|----------|-----------|------------------------|--------|-----------|
| 1 | [How UX Research Can Meet the Moment](#1-how-ux-research-can-meet-the-moment) | David J. Lick | Google | Article | 2023-10-07 |
| 1a | ↳ [From UX Measurement to AI Evaluation](#1a-related-take-from-ux-measurement-to-ai-evaluation) | Saeideh Bakhshi | OpenAI | Article (paid) | 2026-08-09 |
| 2 | [How to Automate AI Evals (Correctly)](#2-how-to-automate-ai-evals-correctly) | Shreya Shankar (on Hamel Husain's channel) | See entry | Presentation (talk with live demo) | 2026-07-03 |
| 3 | [Own the loop: how designers and researchers win with AI evals](#3-own-the-loop-how-designers-and-researchers-win-with-ai-evals) | Setor Zilevu | Figma | Presentation (Config 2026 talk) | 2026-07-06 |
| 4 | [Putting the user back into AI Evaluation](#4-putting-the-user-back-into-ai-evaluation) | Chris Monnier, Chuck Kwong, Wendy Wang (interviewees) | Microsoft (Microsoft AI) | Article (interview) | 2026-09-17 |
| 4a | ↳ [The Model Got Better. Did the Experience?](#4a-related-take-the-model-got-better-did-the-experience) | Chuck Kwong | Microsoft | Article | 2026-10-22 |
| 5 | [Building AI Evals: Who Gets to Decide What's Good?](#5-building-ai-evals-who-gets-to-decide-whats-good) | Not confirmed | DoorDash (publication) | Article | Not confirmed |

---

## 1. How UX Research Can Meet the Moment

- **Link:** <https://medium.com/@davidjameslick/how-ux-research-can-meet-the-moment-3e145acb5471>
- **Author:** David J. Lick, PhD
- **Company at publication:** Google. The byline says Senior UX Researcher; the
  body says he was a research manager, and his
  [UXPA Magazine bio](https://uxpamagazine.org/author/david-lick/) describes him
  managing a Google UX Research team focused on AI and human productivity
  (previously Facebook and Vine).
- **Find them:** [Medium](https://medium.com/@davidjameslick). No LinkedIn or
  personal site is linked from the article or his bio.
- **Format:** Article (Medium, 6 min)
- **Published:** 2023-10-07

**What it adds.** The starting point for this collection, and one of the
earliest pieces to argue that evals are where UX research earns its place in
generative AI work. Written amid the 2023 "is UX research still needed?"
debate, it says the quality of model output decides whether a GenAI feature
succeeds, that human evals are the gold standard for judging it, and that they
are often faster and more reliable than A/B tests early in model testing. Its
key reframe is that a human eval is essentially a repeated-measures survey, in
which raters score outputs on several dimensions, so researchers' survey-design
skills transfer directly: writing and refining rating questions, keeping an
example library with suggested ratings, analyzing rater data and advising on
model choice. It closes with six practices from Lick's Google team: define
criteria clearly, provide a reference library, meet raters often, use 3 to 5
raters per output, check inter-rater agreement, and standardize templates.

It also cites academic work on human evaluation of generated text worth
following up, including Howcroft et al. (2020),
[*Twenty Years of Confusion in Human Evaluation*](https://pure.hw.ac.uk/ws/portalfiles/portal/54138831/2020.inlg_1.23.pdf),
and Gatt & Krahmer (2018),
[*Survey of the State of the Art in Natural Language Generation*](https://www.jair.org/index.php/jair/article/view/11173).

### 1a. Related take: From UX Measurement to AI Evaluation

- **Link:** <https://saeidehbakhshi.substack.com/p/what-ux-and-survey-researchers-bring>
- **Author:** Saeideh Bakhshi
- **Company at publication:** OpenAI. Her About page and
  [personal site](https://saeideh.com) say she is a quantitative UX research
  leader currently at OpenAI (previously Meta, Google, Block and Yahoo), and that
  her views are her own. The post itself does not restate her employer.
- **Find them:** [Research toolbox (Substack)](https://saeidehbakhshi.substack.com) ·
  [LinkedIn](https://www.linkedin.com/in/saeideh-bakhshi-68a3676/) ·
  [saeideh.com](https://saeideh.com) · book project:
  [Building AI Evals](https://humancenteredevals.com/)
- **Format:** Article (Substack, paid). Part 1 of her "AI Evals" series.
- **Published:** 2026-08-09

**Why it sits under Lick.** It makes the same core claim, that UX and survey
researchers' measurement skills transfer to AI evaluation, from a different
person nearly three years later.

**How it differs.** Where Lick argues researchers *should* run evals, Bakhshi
gives them a measurement framework for doing it. She lays out a backward-design
chain (decision, claim, construct, task set, observable evidence, judge, score)
with a question to answer at each step, and names eval failures in research
terms: raters reading a rubric differently is a response-process problem, narrow
task sets are a sampling and coverage problem, collapsing several qualities into
one number is a construct and scoring problem, and a stable score unrelated to
the decision is a validity problem. The series goes on to rubrics, sampling and
LLM graders. *Only the free preview was read; the section on which skills
transfer and which need new fluency is paywalled.*

---

## 2. How to Automate AI Evals (Correctly)

- **Link:** <https://www.youtube.com/watch?v=tqUDjc1HzO4>
- **Speaker:** Shreya Shankar, on Hamel Husain's YouTube channel. The
  description does not say whether Husain also speaks.
- **Company at publication:** The description calls Shankar "a CS professor and
  co-creator of the AI Evals course on Maven" (taught with Husain under Parlance
  Labs). Her [site](https://www.sh-reya.com) says she did her PhD at UC Berkeley
  and joins Carnegie Mellon University as an Assistant Professor in 2027; it
  does not make clear which institution she was at in July 2026. Husain
  describes himself as an ML engineer formerly at Airbnb and GitHub.
- **Find them:** Shreya Shankar: [site](https://www.sh-reya.com) ·
  [blog](https://www.sh-reya.com/blog) ·
  [LinkedIn](https://www.linkedin.com/in/shrshn). Hamel Husain:
  [blog](https://hamel.dev) ·
  [LinkedIn](https://www.linkedin.com/in/hamelhusain/)
- **Format:** Presentation (27-minute session with a live demo)
- **Published:** 2026-07-03

**What it adds.** The practitioner and tooling view, from people who teach evals
to engineers. Its central point is order of operations: do error analysis on
your real logs before writing evals, because writing a rubric before looking at
any data is a common mistake. Error analysis, reading and annotating traces to
build a failure-mode taxonomy, is presented as the most human-intensive part of
evals and the part no tool can fully automate. The session covers an
analyze-measure-improve lifecycle, three mistakes (asking AI to just "find the
issues", reviewing data only once, holding every app to the same accuracy bar),
a live build of a review interface, and an "Error Discovery" skill that updates
the taxonomy as you annotate and uses active learning to pick the next examples.
For researchers, it is a useful bridge: error analysis is close to qualitative
coding, done on model traces. *Summary based on the video description and
chapter list; no transcript was available.*

---

## 3. Own the loop: how designers and researchers win with AI evals

- **Link:** <https://www.youtube.com/watch?v=VfA-vjsFQ1o>
- **Speaker:** Setor Zilevu
- **Company at publication:** Figma (as stated in the video title). His job
  title is not given.
- **Find them:** No blog or LinkedIn is linked in the video description, and
  none could be confirmed.
- **Format:** Presentation (Config 2026 talk, published on Figma's channel)
- **Published:** 2026-07-06

**What it adds.** A design-tool company's case that evals belong to designers
and researchers, not only engineers. The talk frames AI evaluation as something
that has mostly been treated as an engineering problem, argues that the teams
doing well with AI are the ones measuring carefully rather than just shipping
fast, and puts the definition of "good", from a human-centered standpoint, at
the center of the work. Its strategic claim is that as model capabilities become
commoditized, design becomes the lasting advantage, so designers and researchers
should "own the loop" of deciding how AI is judged against real human needs.
*Summary based on the video description only; the talk itself was not
transcribed.*

---

## 4. Putting the user back into AI Evaluation

- **Link:** <https://microsoft.design/articles/putting-the-user-back-into-ai-evaluation/>
- **Authors:** No byline. The piece is built from conversations with three
  researchers at Microsoft AI: **Chris Monnier** (Principal UX Researcher),
  **Chuck Kwong** (Principal UX Researcher) and **Wendy Wang** (leads the
  Copilot UX Research team).
- **Company at publication:** Microsoft (Microsoft AI, Copilot)
- **Find them:** The article links no personal profiles. Chuck Kwong writes at
  [chuckkwong.substack.com](https://chuckkwong.substack.com). LinkedIn profiles
  for the three could not be confirmed.
- **Format:** Article (interview, Microsoft Design; second in a series)
- **Published:** 2026-09-17

**What it adds.** An inside look at a working, product-scale eval program
(response quality for Copilot) run with UX research at the table. The core claim:
machine evals can check whether an answer meets the criteria you set, but only
users can say whether it actually worked for them, and the gap between a team's
idea of "good" and what users prefer is bigger than expected. Concrete practices
include deriving 5 to 8 evaluation dimensions from qualitative conversations
(Monnier), turning findings into "golden" datasets and a shared loss-pattern
taxonomy so data science, engineering and PM use the same vocabulary (Wang),
having real users write their own prompts rather than relying on AI-generated
"perfect" prompts, and favoring multi-turn evals that treat a conversation as a
prototype. Kwong argues no single discipline should own evals, but the user's
voice is what LLM-as-judge and expert-annotator setups miss. It also separates
evaluating a model from evaluating a whole product experience, which is harder,
and notes that frameworks go stale fast.

### 4a. Related take: The Model Got Better. Did the Experience?

- **Link:** <https://chuckkwong.substack.com/p/the-model-got-better-did-the-experience>
- **Author:** Chuck Kwong
- **Company at publication:** Microsoft. The post draws on his team's work on
  "User evals" at Microsoft; it gives no job title, but the Microsoft Design
  piece above names him a Principal UX Researcher at Microsoft AI.
- **Find them:** [Substack](https://chuckkwong.substack.com). No LinkedIn is
  linked from the post or his About page.
- **Format:** Article (Substack)
- **Published:** 2026-10-22

**Why it sits under the Microsoft Design piece.** It describes the same program
and many of the same ideas (golden datasets, loss patterns, users judging their
own interactions). Kwong was one of the three voices in the earlier interview;
this is his own first-person account of it.

**How it differs.** It names the practice, **user evals** (users judging their
own interactions with AI), and argues that the label is clearer than "UX evals"
or "product evals" because it says who does the evaluating. It is organized as
four lessons: clarify what is being evaluated, capture the experience and not
just the outcome, consider what the evidence shows, and close the loop. A
worked example (a support assistant drafting ticket replies, compared in
counterbalanced order by reps using their own tickets) shows how a polished,
empathetic reply can still fail the task. It also explains why thumbs-up/down
feedback is weak (self-selection bias) and spells out the improvement loop most
explicitly: user findings become loss patterns, loss patterns feed golden
datasets, and those datasets calibrate expert annotators and LLM judges against
user judgment. It links a related talk on user evals Kwong gave at Learners with
[Giuliano Morse](https://www.linkedin.com/in/giulianomorse/) (Meta):
<https://www.youtube.com/watch?v=O6D80IgjaxI>.

---

## 5. Building AI Evals: Who Gets to Decide What's Good?

- **Link:** <https://medium.com/design-doordash/building-ai-evals-who-gets-to-decide-whats-good-39671385f50d>
- **Author:** Not confirmed. *The page could not be fetched, so the author,
  their role and the publication date are not recorded here rather than
  guessed.*
- **Company at publication:** Published on DoorDash's design publication on
  Medium (from the URL); the author's own affiliation is not confirmed.
- **Find them:** Not confirmed.
- **Format:** Article (Medium)
- **Published:** Not confirmed

**What it adds.** *Not summarized, because the article could not be read.* Its
title raises the question of who defines "good" in an eval, which connects it to
the Figma talk (3) and the Microsoft Design piece (4). Once it can be read, check
whether it overlaps enough with either to be grouped under it.

---

## Adding a resource

Add the new entry in date order and add a row to the table. Record the author,
their company at publication, links to their blog and/or LinkedIn, the format
(article, podcast or presentation), the publication date and what the piece
adds. If it largely overlaps an existing entry, list it under the older one as a
related take and say how it differs. If a page cannot be read, say so in the
entry.
