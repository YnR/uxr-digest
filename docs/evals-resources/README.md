# AI Evals Resources

A running collection of writing, talks and videos on evaluating AI systems, with
a focus on what UX research and design bring to evals.

*Last updated: 2026-11-09.*

This page is also published at <https://ynr.github.io/uxr-digest/evals/>, with
an [RSS feed](https://ynr.github.io/uxr-digest/evals/feed.xml), a
[JSON Feed](https://ynr.github.io/uxr-digest/evals/feed.json) and a plain
[resources.json](https://ynr.github.io/uxr-digest/evals/resources.json) list, so
the resources and their summaries can be read programmatically.

## How this page is organized

- **Chronological, oldest first**, so the conversation reads in the order it
  developed.
- **Overlapping pieces are grouped.** When two contributions cover much of the
  same ground, the older one is the canonical entry and the newer one is listed
  under it as a *related take* from a different person, with a note on how it
  differs.

## At a glance

| # | Resource | Author(s) | Company at publication | Format | Published |
|---|----------|-----------|------------------------|--------|-----------|
| 1 | [How UX Research Can Meet the Moment](#1-how-ux-research-can-meet-the-moment) | David J. Lick | Google | Article | 2023-10-07 |
| 1a | ↳ [From UX Measurement to AI Evaluation](#1a-related-take-from-ux-measurement-to-ai-evaluation) | Saeideh Bakhshi | OpenAI | Article (paid) | 2026-08-09 |
| 2 | [How to Automate AI Evals (Correctly)](#2-how-to-automate-ai-evals-correctly) | Shreya Shankar, Hamel Husain | OpenAI (Husain); none (Shankar) | Presentation (talk with live demo) | 2026-07-03 |
| 3 | [Own the loop: how designers and researchers win with AI evals](#3-own-the-loop-how-designers-and-researchers-win-with-ai-evals) | Setor Zilevu | Figma | Presentation (Config 2026 talk) | 2026-07-06 |
| 4 | [UXR AI Evals (Research Week 2026)](#4-uxr-ai-evals-research-week-2026) | Giuliano Morse, Chuck Kwong | Meta, Microsoft | Presentation (conference talk) | 2026-08-20 |
| 4a | ↳ [Putting the user back into AI Evaluation](#4a-related-take-putting-the-user-back-into-ai-evaluation) | Chris Monnier, Chuck Kwong, Wendy Wang (interviewees) | Microsoft (Microsoft AI) | Article (interview) | 2026-09-17 |
| 4b | ↳ [The Model Got Better. Did the Experience?](#4b-related-take-the-model-got-better-did-the-experience) | Chuck Kwong | Microsoft | Article | 2026-10-22 |
| 5 | [Building AI Evals: Who Gets to Decide What's Good?](#5-building-ai-evals-who-gets-to-decide-whats-good) | Nam Pham, Andrea Cavicchi | DoorDash | Article | 2026-09-18 |

---

## 1. How UX Research Can Meet the Moment

- **Link:** <https://medium.com/@davidjameslick/how-ux-research-can-meet-the-moment-3e145acb5471>
- **Author:** David J. Lick, PhD
- **Company at publication:** Google. UX Research Manager at Google (Google
  Docs) at the time of publication.
- **Find them:** [Medium](https://medium.com/@davidjameslick) ·
  [LinkedIn](https://www.linkedin.com/in/david-lick-10b28a105/)
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

**In context.** The piece predates two later shifts in the conversation:
automated judging (machine and LLM-as-judge evals) and **user evals**, where real
users judge output on their own tasks (see 4). Lick treats human evals by
trained raters as the gold standard; later work argues that user evals are the
more canonical judgment, because they are more ecologically valid: they capture
the person's real context, which raters following a rubric do not see.

### 1a. Related take: From UX Measurement to AI Evaluation

- **Link:** <https://saeidehbakhshi.substack.com/p/what-ux-and-survey-researchers-bring>
- **Author:** Saeideh Bakhshi
- **Company at publication:** OpenAI
- **Find them:** [Research toolbox (Substack)](https://saeidehbakhshi.substack.com) ·
  [LinkedIn](https://www.linkedin.com/in/saeideh-bakhshi-68a3676/) ·
  [saeideh.com](https://saeideh.com) · book project:
  [Building AI Evals](https://humancenteredevals.com/)
- **Format:** Article (Substack, paid). Part 1 of her "AI Evals" series.
- **Published:** 2026-08-09

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
- **Speakers:** Shreya Shankar, with Hamel Husain introducing and closing, on
  his YouTube channel. It is part 1 of a 12-part mini-course on AI product
  engineering.
- **Company at publication:** Hamel Husain: OpenAI (ML engineer). Shreya Shankar:
  no affiliation at the time; she co-teaches the AI Evals course on Maven with
  Husain.
- **Find them:** Shreya Shankar: [site](https://www.sh-reya.com) ·
  [blog](https://www.sh-reya.com/blog) ·
  [LinkedIn](https://www.linkedin.com/in/shrshn). Hamel Husain:
  [blog](https://hamel.dev) ·
  [LinkedIn](https://www.linkedin.com/in/hamelhusain/)
- **Format:** Presentation (27-minute session with a live demo)
- **Published:** 2026-07-03

**What it adds.** The practitioner and tooling view, from people who teach evals
to engineers, and a clear answer to "can't an agent just do our evals?" No, for
an epistemic reason: what "good" means for a product lives in the builder's
domain judgment, not in the traces. AI tooling should help people express and
apply that judgment faster, not replace it.

- **A three-step lifecycle.** Error analysis (read traces to discover failure
  modes), measurement (count how often each occurs; a few modes usually cause
  most issues) and improvement (prompts, model changes, fine-tuning,
  guardrails). AI is weak at the first step because it lacks product taste,
  and strong downstream once failure modes are well defined.
- **Mistake 1: pointing an agent at your logs and asking it to "find the
  issues".** It misses taste issues that were never written down, flags vague
  or minor problems while missing severe ones (hallucinations, off-brand
  output), and keeps no state between runs. The better pattern is an agent
  skill that builds a review app: it samples and clusters traces, color-codes
  key fields, and watches as the human tags errors, turning those tags into a
  failure taxonomy in the background. The live demo does this on 33
  AI-written blog posts, picking 21 representative samples and naming
  categories such as "contrastive framing" ("it's not just X, it's Y") from
  her highlights.
- **Mistake 2: reviewing traces only once.** More data changes your mental
  model, so earlier traces deserve a second look. Run an outer loop over the
  data and an inner loop over failure hypotheses, and have the agent search
  past and unlabeled traces for new failure modes for quick human
  confirmation.
- **Mistake 3: one accuracy bar for every app.** A low-risk internal summarizer
  can tolerate errors that a customer-facing or high-stakes tool cannot. Ask
  an agent to brainstorm worst-case outcomes (privacy leaks, fabricated
  citations) and work back to the guardrails and evals needed.
- **On vendors.** In Shankar's ongoing benchmarking, general coding agents with
  custom prompts and harnesses often match or beat dedicated eval discovery
  tools; Husain adds that many platforms are essentially prompt wrappers.

For researchers, its closing idea is the bridge: evaluation is about
externalizing tacit domain taste into code, prompts and harnesses, and error
analysis is close to qualitative coding done on model traces. *Summary based on
a timestamped summary of the video supplied by Yann, plus the video
description.*

---

## 3. Own the loop: how designers and researchers win with AI evals

- **Link:** <https://www.youtube.com/watch?v=VfA-vjsFQ1o>
- **Speaker:** Setor Zilevu
- **Company at publication:** Figma (as stated in the video title). His job
  title is not given; he describes a background in computer science applied to
  healthcare and assistive cyber-human systems at Emory University.
- **Find them:** [LinkedIn](https://www.linkedin.com/in/setor-zilevu/)
- **Format:** Presentation (Config 2026 talk, published on Figma's channel)
- **Published:** 2026-07-06

**What it adds.** A design-tool company's case that evals belong to designers
and researchers, with a ready vocabulary for making it. It opens with a
cautionary story: a home-rehab app told a stroke survivor his mobility was
improving, while a physical therapist could see he was compensating by
hyperextending his shoulder. The model was correct to its spec and still wrong,
because nobody checked its definition of "good" against the therapist's
expertise.

- **What an eval is.** An exercise where the room splits evenly on two
  AI-generated designs makes the point that in AI work, disagreement is the
  data: an eval distills subjective disagreement into shared, measurable
  criteria and uses them to steer outputs.
- **Two myths.** That evals are engineering-only (generating output is half
  the job; judging it, and saying why, takes research and design), and that
  "good" can be defined once (probabilistic outputs and rising expectations
  mean quality must be directed continuously: define intent, set criteria,
  measure, learn, repeat).
- **Three layers.** Human evals (calibrated expert rubrics; the ground truth,
  but slow), auto evals (an LLM applying the same rubric at scale, "only as good
  as the human alignment they learn from", otherwise "scaling noise"), and UX
  evals (users in real context, with signals that feed model-level fixes, not
  just UI changes).
- **Skills that map across.** Defining a north star becomes writing the
  rubric; interpreting user disagreement becomes calibrating graders;
  synthesizing edge cases becomes triaging failure modes; recruiting personas
  becomes curating eval datasets.
- **Figma's flywheel.** For its agent features, the team prioritized a few
  high-impact use cases, calibrated raters on rubrics (content quality,
  response quality, prompt success), isolated frequent and severe failure
  modes, and handed failure clusters to engineers to fix prompts and harnesses,
  with results reported to the Chief Design Officer and leadership.
- **Four levers designers and researchers can own:** system prompts, eval
  design ("whoever defines the rubric defines the target"), datasets, and the
  agent's capabilities and tooling.

*Summary based on a timestamped summary of the talk supplied by Yann, plus the
video description.*

---

## 4. UXR AI Evals (Research Week 2026)

- **Link:** <https://www.youtube.com/watch?v=O6D80IgjaxI>
- **Speakers:** Giuliano Morse (UX Researcher, Meta) and Chuck Kwong (UX
  Researcher, Microsoft AI)
- **Company at publication:** Meta and Microsoft
- **Find them:** Giuliano Morse:
  [LinkedIn](https://www.linkedin.com/in/giulianomorse/). Chuck Kwong:
  [Substack](https://chuckkwong.substack.com) ·
  [LinkedIn](https://www.linkedin.com/in/charleskwong/)
- **Format:** Presentation (about 30-minute conversation with audience Q&A at
  Learners Research Week 2026, a UX research conference in San Francisco;
  published on the [Learners YouTube channel](https://www.youtube.com/@JoinLearners))
- **Published:** 2026-08-20

**What it adds.** The earliest of three pieces on **user evals**, the practice
of having real users judge AI output on their own tasks (4a and 4b below are
related takes). It brings evidence from two companies and the most detail on
how user evals plug into ML pipelines:

- **Why standard human evals mislead.** At Meta, traditional human evals kept
  ranking an internal model ahead of competitors, against both leadership
  intuition and real user experience. Annotators rated raw API calls in a
  sandbox, bypassing system prompts, retrieval and tool calls; moving to real
  users on the full end-to-end product brought eval results in line with
  product performance.
- **The workflow.** A user brings an authentic task, does it with Model A, then
  Model B, makes a comparative preference judgment, and Likert ratings plus
  AI-moderated follow-up probing capture why. Early prototypes found
  side-by-side comparison far richer than single-model review.
- **Outputs are engineering assets, not just decks.** The preference data trains
  reward models, fine-tunes classifiers, calibrates LLM judges and steers
  production models. Showing the gap between annotator and user evals is what
  won cross-functional buy-in.
- **Where judges fail.** LLM judges handle objective criteria (latency,
  factuality) but struggle with tone, humor and contextual fit, and annotators
  told to "pretend" to be users miss nuance. Its memorable example: for beach
  wedding footwear, a model recommended designer stilettos, rated highly by
  automated and human annotators, while real users pointed out that heels sink
  into sand.
- **Practical advice.** Static rubrics go stale because user baselines shift as
  people use several frontier models daily. Researchers can start at the
  prompt layer, without touching model training; user evals also catch product
  defects outside the model (UI, copy, copy-paste); and evaluate what happens
  after the output, not just whether it is correct.
- **From the Q&A.** For agentic systems, split samples between naturalistic
  sessions and targeted scenarios (for example, assigned shopping tasks) to
  surface rare tool-calling failures. To untangle many implicit dimensions
  (tone, length, structure), pair discovery interviews with post-eval attribute
  ratings and run a driver analysis against the preference signal.

*Summary based on a timestamped summary of the talk supplied by Yann.*

### 4a. Related take: Putting the user back into AI Evaluation

- **Link:** <https://microsoft.design/articles/putting-the-user-back-into-ai-evaluation/>
- **Authors:** No byline. The piece is built from conversations with three
  researchers at Microsoft AI: **Chris Monnier** (Principal UX Researcher),
  **Chuck Kwong** (Principal UX Researcher) and **Wendy Wang** (leads the
  Copilot UX Research team).
- **Company at publication:** Microsoft (Microsoft AI, Copilot)
- **Find them:** The article links no personal profiles. Chuck Kwong:
  [Substack](https://chuckkwong.substack.com) ·
  [LinkedIn](https://www.linkedin.com/in/charleskwong/). LinkedIn profiles for
  Chris Monnier and Wendy Wang have not been confirmed.
- **Format:** Article (interview, Microsoft Design; second in a series)
- **Published:** 2026-09-17

**How it differs.** An inside look at a working, product-scale eval program
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

### 4b. Related take: The Model Got Better. Did the Experience?

- **Link:** <https://chuckkwong.substack.com/p/the-model-got-better-did-the-experience>
- **Author:** Chuck Kwong
- **Company at publication:** Microsoft. The post draws on his team's work on
  "User evals" at Microsoft; it gives no job title, but the Microsoft Design
  piece (4a) names him a Principal UX Researcher at Microsoft AI.
- **Find them:** [Substack](https://chuckkwong.substack.com) ·
  [LinkedIn](https://www.linkedin.com/in/charleskwong/)
- **Format:** Article (Substack)
- **Published:** 2026-10-22

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
[Giuliano Morse](https://www.linkedin.com/in/giulianomorse/) (Meta); see 4.

---

## 5. Building AI Evals: Who Gets to Decide What's Good?

- **Link:** <https://medium.com/design-doordash/building-ai-evals-who-gets-to-decide-whats-good-39671385f50d>
- **Authors:** Nam Pham (senior researcher) and Andrea Cavicchi (staff
  researcher), published under the DoorDash Design Team byline
- **Company at publication:** DoorDash (UX Research)
- **Find them:** Nam Pham: [LinkedIn](https://www.linkedin.com/in/namph/).
  Andrea Cavicchi: [LinkedIn](https://www.linkedin.com/in/andreakc/).
  Publication: [Design @ DoorDash](https://medium.com/design-doordash)
- **Format:** Article (Medium, 7 min; first in a series)
- **Published:** 2026-09-18

**What it adds.** A taxonomy for the question "whose judgment should the answer
key reflect?", and a worked case of building an LLM judge from user research.
It splits "good" into the objective (checkable with a rule or AI judge) and the
subjective, which lives in people and has to be gathered from them before a
machine can test against it. It then names three kinds of eval question, each
calling for different people to recruit: **Fit** (is this right for this
individual? only the user can say), **Authority** (is it actually high quality?
set by experts or the community) and **Boundaries** (should the AI do this at
all? set by the people affected).

The case study, personalized homepage recommendations, shows survey craft
shaping the judge. The team's rejection reasons had never been tested with
consumers; open-ended answers showed people picking the nearest box ("cuisine
mismatch") for other reasons, and surfaced missing ones ("I could make this at
home", "not right now", "doesn't travel well"). Switching from
check-all-that-apply to one primary reason plus confidence gave cleaner data
and a grounded answer key, and the judges were then tuned in a
prompt-benchmark-analyze loop, catching dietary restrictions 2.5x better than
an untrained judge on held-out data. It closes with a caution: human taste is
inconsistent, so a judge can only be as consistent as the human baseline, and
over-optimizing agreement leads to "number gaming".

**How it relates to others.** It shares the Microsoft Design piece's (4a) core
idea of calibrating automated judges against user judgment, published a day
later by a different team. It stays a separate entry because its main
contribution, the Fit / Authority / Boundaries framework for choosing whose
judgment counts, is not in the other pieces. Its survey-design lessons are a
concrete example of the skills Lick (1) and Bakhshi (1a) say transfer to evals.

---

## Adding a resource

Add the new entry in date order and add a row to the table. Record the author,
their company at publication, links to their blog and/or LinkedIn, the format
(article, podcast or presentation), the publication date and what the piece
adds. If it largely overlaps an existing entry, list it under the older one as a
related take and say how it differs. If a page cannot be read, say so in the
entry.

Keep each entry to the same shape (a `## N.` or `### Na. Related take:`
heading, the `- **Field:**` list, then sections that open with a bold lead-in
such as `**What it adds.**`), because `reader/evals_resources.py` builds the
published page and feeds from it.
