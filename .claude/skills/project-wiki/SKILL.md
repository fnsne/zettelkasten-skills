---
name: project-wiki
description: Build and maintain a Zettelkasten-style project wiki under `.wiki/` in a project folder. Cards are atomic markdown notes that link to each other Wikipedia-style and reference (but never modify) source files like code, docs, PDFs, and meeting notes. Use this skill whenever the user wants to extract cards from project material, link related cards, promote a card into a hub, audit wiki health, or query the wiki to answer a project question. Trigger this skill for any mention of "card", "wiki", "Zettelkasten", "MOC", "knowledge base", "project notes", or when the user asks Claude to "find", "look up", or "summarize" something from project documentation. Prefer this skill over reading raw source files when a `.wiki/` folder exists in the project — the wiki is designed to answer questions with far fewer tokens than scanning source.
---

# Project Wiki (Zettelkasten for Projects)

A Zettelkasten-style wiki that lives inside a project folder. Every card is an atomic markdown note. Cards link to each other Wikipedia-style — both as metadata and inline in prose. Original source files (code, PDFs, docs, meeting notes) are never modified; cards reference them via path + line/page numbers.

## Core principles

1. **Flat structure, emergent hierarchy.** All cards live in `cards/`. There is no `index/` folder. A card becomes a "hub" by virtue of being linked-to and by its content, not by its location.
2. **One concept per card.** The test: can you use the card's title as a noun phrase in another card's prose? If not, split it.
3. **Sources are read-only.** Cards link back to source via `sources:` frontmatter. Never edit source files. If source changes, mark the card stale in `_meta/stale.md`.
4. **Two link layers.** `frontmatter.links` is the machine-readable index. Inline `[[card-id|display text]]` is the narrative — the wiki reads like Wikipedia, not like a directory.
5. **Semi-automatic.** Every extract / link / promote action proposes changes and waits for user confirmation. Never silently mass-edit cards.

## Directory layout

```
<project>/
├── src/                # source code (read-only)
├── docs/               # design docs, PDFs (read-only)
├── meetings/           # meeting notes (read-only)
└── .wiki/              # wiki content (created by this skill)
    ├── _root.md        # the one fixed entry point
    ├── cards/          # all cards, flat
    │   ├── auth-jwt-flow.md
    │   ├── auth-overview.md
    │   ├── decision-jwt-vs-session.md
    │   └── ...
    └── _meta/
        ├── orphans.md  # cards nobody links to
        └── stale.md    # cards whose source has changed since
```

This skill itself is installed at `.claude/skills/project-wiki/SKILL.md` (Claude Code auto-loads it from there). It operates on the `.wiki/` folder shown above.

## Card format

Every card is a markdown file with YAML frontmatter. Obsidian-compatible.

```markdown
---
id: auth-jwt-flow
created: 2026-05-15
updated: 2026-05-15
sources:
  - path: src/auth/jwt.ts
    lines: 12-89
    note: implementation
  - path: docs/auth-spec.pdf
    pages: 4-6
links:
  - auth-overview
  - decision-jwt-vs-session
  - security-token-rotation
tags: [auth, security]
---

# JWT 簽發流程

## 摘要
JWT 簽發流程是本系統認證的核心步驟,負責在使用者登入後產生帶 user
payload 的 stateless token。根據 [[decision-jwt-vs-session|當初的決策]],
本系統採 stateless 設計而非 server-side session。

## 內容
登入流程依 [[architecture-auth-layer|auth layer 規範]],先由 API gateway
驗證請求格式,再交給 auth service 處理。簽發後,session 狀態追蹤交給
[[auth-session-mgmt]] 負責,並用 [[security-token-rotation|token rotation
策略]]降低洩漏風險。

## 何時往下追
- 為什麼選 JWT,不選 session → [[decision-jwt-vs-session]]
- session 怎麼配合 → [[auth-session-mgmt]]
- 實作細節 → `src/auth/jwt.ts:12-89`
- 規格原文 → `docs/auth-spec.pdf` p.4-6
```

**Required fields**: `id`, `created`, `sources` (can be empty list), `links` (can be empty list).
**Forbidden**: `type` field. A card's role (atomic / hub / decision) is emergent, not declared.

### Three layers of links

| Layer | Where | Purpose | Audience |
|---|---|---|---|
| `frontmatter.links` | YAML | Machine-readable index; used by `audit` and `link` workflows; powers backlinks | Tooling |
| Inline `[[card-id\|text]]` | Within prose | The card reads as continuous narrative, with concepts linking to their definitions | Humans + Claude reading the card |
| "何時往下追" section | End of card | Explicit navigation hints — "for X go to Y" | Claude during query-time traversal |

All three should exist on most cards. Frontmatter `links` should be a superset of (or equal to) the cards mentioned inline.

## Card splitting rules

When extracting cards, apply these rules. They make inline linking possible.

**Rule 1 — One referenceable concept per card.** Title must be a noun phrase another card can use mid-sentence. ✅ "JWT 簽發流程", "使用者資料表結構", "為什麼選 JWT 而非 session". ❌ "Auth 相關的一些想法", "JWT 是怎麼運作的?", "5/12 會議記錄".

**Rule 2 — Summary opens with a definition sentence.** First sentence of `## 摘要` must define what this card is, in one sentence, so readers arriving via inline link grasp the concept immediately.

**Rule 3 — Granularity guide.**
- One decision → one card (e.g. "為什麼選 JWT")
- One flow/process → one card (e.g. "JWT 簽發流程")
- One schema/data structure → one card
- One module overview → one card (this often becomes a hub)
- A meeting / PDF is **not** a card — it's a source. Extract the concepts inside it into multiple cards.

**Rule 4 — When in doubt, split.** Two concepts in one card means neither can be referenced cleanly. Splitting is cheap; merging via `[[ ]]` is free.

## The `_root.md` entry point

`_root.md` is the only fixed entry point. Claude reads it first on every query. Template:

```markdown
---
id: _root
updated: 2026-05-15
---

# 專案 Wiki 入口

## 這個專案是什麼
一句話 / 一段話描述專案。

## 主要切入點
**架構** → [[architecture-overview]]
**決策脈絡** → [[decisions-log]]
**模組** → [[auth-overview]] / [[db-overview]] / [[api-overview]]
**會議共識** → [[meetings-index]]

## 查詢提示給 Claude
- 先讀本卡 → 挑一張最相關的卡 → 沿 links 往下追
- 一次查詢不要讀超過 5 張卡;超過就回頭跟使用者確認方向
- 找不到答案時,讀 atomic card 的 `sources:` 欄位去原檔
```

The "查詢提示給 Claude" section is meta-instruction — it tells Claude how to navigate **this specific wiki**.

---

## Workflows

The skill has five workflows. Always announce which one is running, and always run them semi-automatically (propose → confirm → write).

### Workflow 1: `query` — answer a question using the wiki

**Trigger**: user asks a question that the wiki should answer.

Steps:
1. Read `.wiki/_root.md`.
2. Identify the most relevant link in `_root.md`. Follow it. Read that card.
3. From that card, identify which links (inline or frontmatter) most likely contain the answer. Follow at most 2 of them.
4. Repeat step 3 up to a depth of about 5 cards total. If still not found, fall back to reading `sources:` of the most relevant card and look up the original file at the referenced lines/pages.
5. If 5 cards aren't enough and no source is conclusive, stop and report to the user: "I've read [list of cards] and the answer isn't there. Should I read [next candidate] or look at source X?"

**Budget**: roughly 1500–2500 tokens per query. If a card alone is over ~500 tokens, it's probably violating Rule 4 (split it).

### Workflow 2: `extract` — turn source material into cards

**Trigger**: user provides one or more source files (code, PDF, doc, meeting notes) and asks to extract cards.

Steps:
1. Read the source material.
2. Identify N independent concepts following the splitting rules. List them as candidate cards.
3. **For each candidate, traverse the existing wiki** starting from `_root.md` to find:
   - Is there already a card on this concept? → propose **expand existing card** instead of creating new.
   - Are there cards on nearby concepts? → note them as link targets for the new card.
   - Is this a completely new branch? → flag that a new hub may be needed (suggest `promote` later).
4. **Present a proposal** to the user, like:
   ```
   From src/auth/jwt.ts I propose:
     [NEW] auth-jwt-flow      → will link to: auth-overview, decision-jwt-vs-session
     [NEW] auth-refresh-token → will link to: auth-jwt-flow, security-token-rotation
     [EXPAND] auth-overview   → add subsection mentioning the new cards
     [UPDATE] _root.md        → no change (auth-overview already linked)
   Confirm? (y / edit / skip <id>)
   ```
5. On confirmation, write the cards. Each new card must include:
   - Definition sentence as the first line of `## 摘要`
   - Inline links to existing cards mentioned in the body (use `[[card-id|display text]]`)
   - `sources:` pointing to exact paths + lines/pages
   - `## 何時往下追` section
6. **Update affected hub cards** in the same pass: if `auth-overview` exists and a new sub-card was created, propose insertion into its "子題導覽" or prose. Show the diff. Confirm.

**Never** edit source files in `src/`, `docs/`, `meetings/`.

### Workflow 3: `link` — find and weave links between existing cards

**Trigger**: user asks "find missing links" or after a batch of `extract`.

Steps:
1. Pick the target card(s).
2. Scan all other cards in `cards/` for concept overlap. Concept overlap = card B's title (or a close paraphrase) appears in card A's prose, OR card A and B share strong tag overlap and topic.
3. For each potential link, propose:
   - **frontmatter link**: add `card-b` to `links:` of `card-a`
   - **inline link**: rewrite a specific sentence in `card-a` to embed `[[card-b|...]]`
4. Show the proposed prose change as a diff. Confirm before writing.

Inline link rewrites should be **minimally invasive** — keep the original sentence's meaning, just wrap or substitute the relevant noun phrase.

### Workflow 4: `promote` — turn a card into a hub, or create a new hub

**Trigger**: user requests, or `audit` flags that a topic now has > ~5 cards with no hub.

Steps:
1. Identify the cluster of related cards.
2. Choose between:
   - **Expand an existing card** into a hub (preferred if one card is already broadly about the topic).
   - **Create a new hub card** if no good candidate exists.
3. The hub card must have:
   - A definition sentence summarizing the whole subtopic
   - A "子題導覽" section listing all cluster cards with one-line descriptions
   - Inline links to the most important sub-cards woven into a short narrative
4. Update `_root.md` if this is a top-level hub. Propose the change; confirm before writing.

### Workflow 5: `audit` — health check

**Trigger**: user asks "check the wiki" / "what's broken".

Reports (writes to `_meta/orphans.md` and `_meta/stale.md`, doesn't auto-fix):

1. **Orphans**: cards with zero inbound `frontmatter.links` from any other card. Likely candidates for inline-linking from a hub.
2. **Inline-orphan**: card appears in some `frontmatter.links` but **never** appears as an inline `[[ ]]` in any other card's prose. Means: indexed but not narratively woven. Propose where to weave it in.
3. **Dead-end cards**: cards with zero outbound links AND no `## 何時往下追` section. Suggest follow-ups.
4. **Stale**: source file `mtime` is newer than card `updated` field. List in `_meta/stale.md` for human review. Do not auto-update — the card author needs to decide what changed.
5. **Oversized cards**: any card body over ~500 tokens. Probably violates one-concept-per-card. Suggest split.
6. **Broken links**: `[[xyz]]` or `links: [xyz]` where no `xyz.md` exists in `cards/`.

## Operating conventions

- **Filenames**: `cards/<id>.md` where `<id>` matches the frontmatter `id`. Use kebab-case, lowercase, ASCII (no spaces, no CJK in filenames — but card titles and content can be any language).
- **Card IDs are stable**. If you must rename, update all inbound links across all cards in the same commit / batch.
- **Dates**: ISO format `YYYY-MM-DD`.
- **Source references**: always include exact lines (for code) or pages (for PDFs). `src/foo.ts:42-58`, `docs/spec.pdf` p.4-6.
- **Wiki links**: prefer `[[id|display text]]` over bare `[[id]]` when the id and the natural prose phrase differ.
- **No deletions without confirmation**. Even orphan cards stay until the user explicitly says delete.

## When to refuse or defer

- If the user asks to modify a source file (anything outside `.wiki/`), refuse — explain that the wiki is a layer on top, not a replacement.
- If the user asks to mass-import a giant document without splitting, push back: propose how to split it into cards first.
- If `_root.md` doesn't exist yet, before doing anything else, propose creating it with the user.

## Initial setup

If `.wiki/` doesn't exist when the skill is invoked:
1. Create `.wiki/`, `.wiki/cards/`, `.wiki/_meta/`.
2. Create `.wiki/_root.md` from the template above, with the project description filled in (ask user).
3. Optionally seed with a few top-level hub cards based on what's visible in the project root (e.g. if there's `src/auth/`, propose `auth-overview` as a stub).
