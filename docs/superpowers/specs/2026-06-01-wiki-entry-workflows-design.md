# Design: project-wiki entry workflows (slice / relate / fleet)

Date: 2026-06-01
Skill: `project-wiki`
Status: approved (pending spec review)

## Problem

Creating a card has several **entry points** — extracting from a source file, jotting
one's own idea, or organising the content of an AI discussion into a draft. The author
noticed that these scenarios differ only at the **front** (how the material arrives); the
**middle and back** stages are shared:

- finding cards/documents related to the new content (so links can be placed), and
- deciding what knowledge points to split out of a source / whether to aggregate.

Two of these shared stages are the real pain points:

1. **"Hard to find possibly-related cards."**
2. **"Don't know what knowledge points can be cut out of a document."**

The existing `extract` workflow already does both of these, but they are fused into a
file-based entry and a full propose-confirm write walk-through. There is no way to invoke
just the judgement-heavy parts, and no clean entry for "turn this discussion into cards."

## Decision: no new skill

These capabilities stay inside the single `project-wiki` skill as additional workflows.
**Zero new skills.** Reasoning:

- The card pipeline (identify concepts → place links → write → bookkeeping) is shared
  across every entry. Splitting entries into separate skills would duplicate or
  cross-reference that pipeline knowledge and invite drift.
- A skill is the unit of **auto-triggering** (matched by its `description`). One skill's
  description can advertise several trigger situations and route internally after loading;
  one-action-per-skill is not required.
- The entry adapters (`extract` for files, `fleet` for the current session) are the same
  kind of thing — only the first step differs. Promoting one to its own skill while the
  other stays a workflow is asymmetric and buys nothing.
- The only pull toward a separate `fleet` skill — trigger disambiguation against
  `jackli-work-log` — is solved by description wording plus a clarifying question, not by
  a skill split. `fleet` also fails the "knowledge cleanly separable" test: it writes to
  `wiki/_inbox/` and relies on the wiki's inbox/ref infrastructure.

This decision is reversible: if `fleet` later grows wiki-independent logic or its trigger
keeps misfiring, splitting it out is cheap.

## Resulting shape

```
project-wiki (single skill)
├── entries:   extract (a source file)   fleet (current session → inbox)
├── judgement (callable standalone, also called by entries):  slice, relate
├── existing:  query, promote, audit
└── scripts:   audit.py, conflict-mark.py, inbox-promote.py
```

The two pain-point capabilities become standalone, **read-only** operations that
`extract` (and `fleet`'s downstream `extract`) call internally. The author gets the
bottom-up decomposition they wanted: the painful stages ARE the shared core.

## New workflow: `slice` — read-only concept map from a source

- **Trigger phrasings:** 「這份文件能切出哪些知識點」「slice 一下這份」「這份有哪些卡可做」
- **Input:** one source reference — a file under `docs/`, `src/`, `meetings/`, or an
  inbox item under `wiki/_inbox/`.
- **Behaviour (read-only):**
  1. Read the source.
  2. Identify N independent concepts per the existing splitting rules (Rules 1–4).
  3. Do a **light** scan of the wiki from `_root.md` to tag each candidate `NEW` or
     `EXPAND → <existing-card-id>` (an existing card already covers the concept).
- **Output:** a numbered list; each line = title + `(NEW)` / `(EXPAND → id)` + a one-line
  description. Ends by asking which to write. **Writes no files.**
- **Read-only boundary:** pure proposal. This is the existing `extract` step 2, surfaced
  as a standalone, stop-early operation.
- **Relationship to extract:** `extract` calls `slice` as its candidate-identification
  step; standalone `slice` simply stops after presenting the map.

## New workflow: `relate` — related cards/docs + link placement (read-only)

- **Trigger phrasings:** 「找跟這張卡相關的」「這段內容該連去哪」「relate」
- **Input:** a piece of content — an existing card id, a draft card, or a concept/snippet
  of text.
- **Behaviour (read-only):** traverse the wiki from `_root.md` downward and surface:
  - related cards (same concept / nearby / candidate 主題卡), each annotated with **where**
    the link should go (frontmatter `links:` / inline in `## 摘要` / `## 何時往下追` /
    a 主題卡's 子題導覽) and the direction(s);
  - related source documents → to be recorded under `sources:`.
- **Output:** grouped suggestions (related cards with placement; related docs). **Writes no
  files.** The user places the links, or asks Claude to.
- **Read-only boundary:** the contrast with `extract`'s `[LINK]` items — those **write**
  after confirmation; standalone `relate` is the advisory-only version.

## New workflow: `fleet` — capture the current session into an inbox note

- **Trigger phrasings:** 「把這段討論記成閃記／卡片初稿」「fleet」「把我們討論的整理進 wiki」
- **Disambiguation (vs `jackli-work-log`):** only enter `fleet` when the message mentions
  卡片 / 閃記 / inbox / wiki. When ambiguous, ask: 「要記成 wiki 閃記，還是寫工作日誌？」
- **Behaviour:** write the relevant span of the discussion to
  `wiki/_inbox/YYYY-MM-DD-slug.md` (free-form markdown, low friction). Show the draft;
  confirm. Then ask 「要現在接著萃取成卡片嗎？」 — on yes, run `extract` on that inbox file.
- **Boundary:** `fleet` **only creates the inbox file.** It moves no files. The inbox→ref
  promotion happens later, at `extract`'s tail (existing step 6, `inbox-promote.py`),
  which runs only when at least one card was written. So `fleet` is a thin entry adapter.

## Change to existing `extract`

Minimal, mostly reframing:

- Rename the inline prose of step 2 ("identify candidates") and the link-scanning portion
  to **invoke `slice` and `relate` as shared sub-procedures**, so the same logic is not
  written twice in SKILL.md.
- The walk-through, `[LINK]` writes, and tail `inbox-promote.py` step are **unchanged**.
- Confirm the tail promotion condition stays "at least one card written"; document that
  `fleet → extract` with zero cards leaves the inbox file in place.

## Change to the skill `description` (frontmatter)

- Add trigger phrasings for `slice`, `relate`, and `fleet`.
- Add a one-line disambiguation note steering 討論-capture toward `fleet` / wiki and away
  from work-log when wiki/card/inbox is mentioned.

## SKILL.md size

Adding three workflows lengthens SKILL.md (the whole core loads into context on trigger).
Evaluate length after drafting; if it grows too large, move each workflow's step-by-step
detail into `references/` and keep the SKILL.md core to routing + shared rules (progressive
disclosure). Do this only if length actually warrants it.

## Out of scope

- No changes to `query`, `promote`, `audit`, or the three scripts' logic.
- No proactive/automatic detection of "card-worthy" moments — all entries are
  user-triggered.
- No new "jot my own idea" entry yet; if added later it is just another thin adapter that
  writes an inbox file and hands off to `extract` (no pipeline change).
