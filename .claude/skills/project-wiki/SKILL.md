---
name: project-wiki
description: Build and maintain a Zettelkasten-style project wiki under `wiki/` in a project folder. Cards are atomic markdown notes that link to each other Wikipedia-style (via standard markdown links) and reference (but never modify) source files like code, docs, PDFs, and meeting notes. Use this skill whenever the user wants to extract cards from project material, link related cards, promote a card into a hub, audit wiki health, drop fleeting material into the inbox, or query the wiki to answer a project question. Trigger this skill for any mention of "card", "wiki", "Zettelkasten", "MOC", "knowledge base", "project notes", "inbox", or when the user asks Claude to "find", "look up", or "summarize" something from project documentation. Prefer this skill over reading raw source files when a `wiki/` folder exists in the project — the wiki is designed to answer questions with far fewer tokens than scanning source.
---

# Project Wiki (Zettelkasten for Projects)

A Zettelkasten-style wiki that lives inside a project folder. Every card is an atomic markdown note. Cards link to each other Wikipedia-style — both as frontmatter metadata and inline in prose — using **standard CommonMark markdown links**, so any markdown viewer (VS Code, GitHub, GitLab, etc.) can render them as clickable links without extensions. Original source files (code, PDFs, docs, meeting notes) are never modified; cards reference them via path + line/page numbers.

## Core principles

1. **Flat structure, emergent hierarchy.** All cards live in `cards/`. There is no `index/` folder. A card becomes a "hub" by virtue of being linked-to and by its content, not by its location.
2. **One concept per card.** The test: can you use the card's title as a noun phrase in another card's prose? If not, split it.
3. **Sources are read-only.** Cards link back to source via `sources:` frontmatter. Never edit source files. If source changes, mark the card stale in `_meta/stale.md`.
4. **Two link layers.** `frontmatter.links` is the machine-readable index (list of card ids). Inline standard markdown links `[display text](./other-card.md)` form the narrative — the wiki reads like Wikipedia, not like a directory.
5. **Semi-automatic.** Every extract / link / promote action proposes changes and waits for user confirmation. Never silently mass-edit cards.

## Directory layout

```
<project>/
├── src/                  # source code (read-only)
├── docs/                 # design docs, PDFs (read-only)
├── meetings/             # meeting notes (read-only)
└── wiki/                 # wiki content (created by this skill)
    ├── _root.md          # the one fixed entry point
    ├── _inbox/           # fleeting material awaiting processing
    │   └── 2026-05-22-jwt-想法.md
    ├── cards/            # all cards, flat
    │   ├── auth-jwt-flow.md
    │   ├── auth-overview.md
    │   ├── decision-jwt-vs-session.md
    │   └── ...
    ├── ref/              # source material that came in via inbox (read-only after move)
    │   └── 2026-05-20-架構討論.md
    └── _meta/
        ├── orphans.md    # cards nobody links to
        ├── stale.md      # cards whose source has changed since
        └── conflicts.md  # pairs of cards with opposing claims, awaiting resolution
```

This skill itself is installed at `.claude/skills/project-wiki/SKILL.md` (Claude Code auto-loads it from there). It operates on the `wiki/` folder shown above.

Underscore-prefix entries (`_root.md`, `_inbox/`, `_meta/`) are wiki infrastructure. The rest (`cards/`, `ref/`) are content.

## Inbox: capturing fleeting material

`wiki/_inbox/` is a staging area for material that **doesn't exist anywhere else yet** — fleeting notes, captured ideas, quick jottings the user wants Claude to help turn into cards later.

**Inbox conventions:**

- **Free-form markdown.** No required frontmatter, no required structure. Low friction is the point.
- **Filename**: descriptive, ideally date-prefixed (`YYYY-MM-DD-slug.md`), but not enforced.
- **Content = source.** Inbox items are the originating source for the cards extracted from them; they are not pointers to other files. (If the user wants to process an existing file like `docs/foo.pdf`, they should invoke `extract` on it directly without going through inbox.)

**When inbox items get processed** (via `extract`), the file is **moved** from `_inbox/` to `ref/` and is from then on treated as a source — read-only, never deleted, never modified. The corresponding cards' `sources:` field points to the new `ref/...` path.

**`ref/` semantics:** parallel to `src/`, `docs/`, `meetings/` — it's source material, just material that came in through the wiki workflow. The skill never modifies anything inside `ref/`.

Claude **does not proactively check** the inbox at session start. It only surfaces inbox items when:
- The user explicitly asks ("看一下 inbox" / "what's in inbox?" / "處理 inbox")
- `audit` runs (it reports pending-inbox count as one of its checks)

## Card format

Every card is a markdown file with YAML frontmatter.

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
payload 的 stateless token。根據[當初的決策](./decision-jwt-vs-session.md),
本系統採 stateless 設計而非 server-side session。

## 內容
登入流程依[auth layer 規範](./architecture-auth-layer.md),先由 API gateway
驗證請求格式,再交給 auth service 處理。簽發後,session 狀態追蹤交給
[auth-session-mgmt](./auth-session-mgmt.md) 負責,並用
[token rotation 策略](./security-token-rotation.md)降低洩漏風險。

## 何時往下追
- 為什麼選 JWT,不選 session → [decision-jwt-vs-session](./decision-jwt-vs-session.md)
- session 怎麼配合 → [auth-session-mgmt](./auth-session-mgmt.md)
- 實作細節 → `src/auth/jwt.ts:12-89`
- 規格原文 → `docs/auth-spec.pdf` p.4-6
```

**Required fields**: `id`, `created`, `sources` (can be empty list), `links` (can be empty list).
**Optional fields**: `conflicts` (list of card-ids this card opposes — must be bidirectional, both sides list each other), `updated`, `tags`.
**Optional sections**: `## 前提與局限` (when the card's content is a claim/decision — record the assumptions it rests on, and when it would need re-evaluation), `## 衝突與爭議` (narrative explanation of disagreements, pairs with `conflicts:` frontmatter).
**Forbidden**: `type` field. A card's role (atomic / hub / decision / claim) is emergent from content, not declared.

### Three layers of links

| Layer | Where | Purpose | Audience |
|---|---|---|---|
| `frontmatter.links` | YAML (list of card ids) | Machine-readable index; used by `audit` and `link` workflows; powers backlinks | Tooling |
| Inline `[text](./other-card.md)` | Within prose | The card reads as continuous narrative, with concepts linking to their definitions; clickable in any markdown viewer | Humans + Claude reading the card |
| "何時往下追" section | End of card | Explicit navigation hints — "for X go to Y" | Claude during query-time traversal |

All three should exist on most cards. Frontmatter `links` should be a superset of (or equal to) the cards mentioned inline.

### Relative path conventions

Cards live in `wiki/cards/`. Common link targets and their relative paths:

| Target | Relative path from a card |
|---|---|
| Another card | `./other-card.md` |
| `_root.md` | `../_root.md` |
| A `ref/` item | `../ref/2026-05-20-架構討論.md` |
| Code in `src/` | `../../src/auth/jwt.ts` (rarely linked inline; usually in `sources:`) |

From `_root.md` (which lives in `wiki/`), links into `cards/` look like `./cards/auth-overview.md`.

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

**Rule 4 — When in doubt, split.** Two concepts in one card means neither can be referenced cleanly. Splitting is cheap; merging via inline links is free.

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
**架構** → [architecture-overview](./cards/architecture-overview.md)
**決策脈絡** → [decisions-log](./cards/decisions-log.md)
**模組** → [auth-overview](./cards/auth-overview.md) / [db-overview](./cards/db-overview.md) / [api-overview](./cards/api-overview.md)
**會議共識** → [meetings-index](./cards/meetings-index.md)

## 查詢提示給 Claude
- 先讀本卡 → 挑一張最相關的卡 → 沿 links 往下追
- 一次查詢不要讀超過 5 張卡;超過就回頭跟使用者確認方向
- 找不到答案時,讀 atomic card 的 `sources:` 欄位去原檔
```

The "查詢提示給 Claude" section is meta-instruction — it tells Claude how to navigate **this specific wiki**.

---

## Tooling: scripts vs Claude judgement

Mechanical, deterministic operations live in Python scripts under `.claude/skills/project-wiki/scripts/`. Claude judgement is reserved for the semantic parts (identifying concepts, detecting contradictions, deciding which links to weave, conversing with the user).

| Operation | Implementation |
|---|---|
| Audit (all 8 health checks + `_meta/` writes) | `scripts/audit.py` |
| Mark a bidirectional conflict between two cards | `scripts/conflict-mark.py` |
| Promote an inbox file to `ref/` and rewrite card `sources:` paths | `scripts/inbox-promote.py` |
| Concept identification, contradiction detection, link proposals, query traversal | Claude |
| All propose-confirm interaction with the user | Claude |

**Dependency**: the scripts require PyYAML (`pip install pyyaml`). They use `pathlib` and the standard library otherwise; no other deps.

**Script-first principle**: when an operation is fully deterministic — parsing frontmatter, checking link validity, moving files, writing bidirectional edges — invoke the script. Don't reimplement these as Claude tool calls. Scripts avoid editing mistakes and are 10–50× cheaper in tokens than reading every card.

---

## Workflows

The skill has five workflows. Always announce which one is running, and always run them semi-automatically (propose → confirm → write).

### Workflow 1: `query` — answer a question using the wiki

**Trigger**: user asks a question that the wiki should answer.

Steps:
1. Read `wiki/_root.md`.
2. Identify the most relevant link in `_root.md`. Follow it. Read that card.
3. From that card, identify which links (inline or frontmatter) most likely contain the answer. Follow at most 2 of them.
4. Repeat step 3 up to a depth of about 5 cards total. If still not found, fall back to reading `sources:` of the most relevant card and look up the original file at the referenced lines/pages.
5. If 5 cards aren't enough and no source is conclusive, stop and report to the user: "I've read [list of cards] and the answer isn't there. Should I read [next candidate] or look at source X?"

**Budget**: roughly 1500–2500 tokens per query. If a card alone is over ~500 tokens, it's probably violating Rule 4 (split it).

### Workflow 2: `extract` — turn source material into cards

**Trigger**: user provides one or more source files (code, PDF, doc, meeting notes, or an inbox item) and asks to extract cards.

Steps:
1. Read the source material. If it's a `_inbox/...` file, treat it as the originating source for the resulting cards.
2. Identify N independent concepts following the splitting rules. List them as candidate cards.
3. **For each candidate, traverse the existing wiki** starting from `_root.md` to find:
   - Is there already a card on this concept? → propose **expand existing card** instead of creating new.
   - Are there cards on nearby concepts? → note them as link targets for the new card.
   - Is this a completely new branch? → flag that a new hub may be needed (suggest `promote` later).
   - **Does any neighbor card contradict this candidate?** Read the neighbor's prose and ask "do these make opposing claims about the same question?" If yes, flag as `[CONFLICT?]` in step 4. Be conservative — different framings of the same fact are not conflicts; different conclusions on the same question are.
   - **Does the candidate's content rest on premises** (language like "選 X 而非 Y" / "採 X 策略" / "X 比 Y 好" / "前提是…")? If yes, propose adding a `## 前提與局限` section as `[SECTION?]` in step 4. This is a content cue — the card itself still has no `type:`.
4. **Present a proposal** to the user. Prefix every item with `[1]`, `[2]`, ... so the user can reference them by number (see "Numbered proposal items" in Operating conventions):
   ```
   From src/auth/jwt.ts I propose:
     [1] [NEW] auth-jwt-flow      → will link to: auth-overview, decision-jwt-vs-session
     [2] [NEW] auth-refresh-token → will link to: auth-jwt-flow, security-token-rotation
     [3] [EXPAND] auth-overview   → add subsection mentioning the new cards
     [4] [UPDATE] _root.md        → no change (auth-overview already linked)

     [5] [SECTION?] decision-jwt-vs-session → propose adding ## 前提與局限
         draft: "本決策前提是 token 生命週期 < 1hr。若改長期 token,
                需重評 revocation 機制。"

     [6] [CONFLICT?] auth-jwt-flow ↔ decision-jwt-vs-session
         新卡: "JWT 適合所有 stateless 場景"
         舊卡: "JWT 僅限低敏感場景,因 revocation 缺陷"
         (m) mark    — 兩張卡 frontmatter 互加 conflicts:,原文不動
         (r) resolve — 現在處理,會再問您要改哪一邊 / 合併 / 重寫
         (n) not really — 不算衝突,別標
         (s) skip    — 跳過,extract 繼續

   Confirm? (y / edit <n> / skip <n>)
   ```
5. On confirmation, write the cards. Each new card must include:
   - Definition sentence as the first line of `## 摘要`
   - Inline links to existing cards mentioned in the body (use `[display text](./card-id.md)`)
   - `sources:` pointing to exact paths + lines/pages
   - `## 何時往下追` section
   - **If a `[SECTION?]` proposal was accepted**: include the `## 前提與局限` section using the draft (or the user's edited version).
   - **For each `[CONFLICT?]` answered `m` (mark)**: invoke `python .claude/skills/project-wiki/scripts/conflict-mark.py <card-a> <card-b> --description "<one-liner>"`. The script bidirectionally adds the conflict to both cards' `conflicts:` frontmatter and appends to `_meta/conflicts.md`. Do **not** modify either card's prose.
   - **For each `[CONFLICT?]` answered `r` (resolve)**: enter a resolution sub-flow before writing — ask the user whether to (a) keep one side and rewrite the other, (b) reconcile both into one revised wording, or (c) create a new card that frames both as valid under different conditions. Show the diff. Confirm.
   - Answers `n` and `s`: no further action; the conflict is not recorded.
6. **Update affected hub cards** in the same pass: if `auth-overview` exists and a new sub-card was created, propose insertion into its "子題導覽" or prose. Show the diff. Confirm.
7. **If the source was an inbox item**: after cards are written and confirmed, run `python .claude/skills/project-wiki/scripts/inbox-promote.py wiki/_inbox/<filename>`. The script moves the file to `wiki/ref/` and rewrites any card's `sources:` path that referenced the old `_inbox/` location. The inbox file is **never deleted** — it's preserved in `ref/` for traceability.

**Never** edit source files in `src/`, `docs/`, `meetings/`, or `ref/`.

### Workflow 3: `link` — find and weave links between existing cards

**Trigger**: user asks "find missing links" or after a batch of `extract`.

Steps:
1. Pick the target card(s).
2. Scan all other cards in `cards/` for concept overlap. Concept overlap = card B's title (or a close paraphrase) appears in card A's prose, OR card A and B share strong tag overlap and topic.
3. For each potential link, propose:
   - **frontmatter link**: add `card-b` to `links:` of `card-a`
   - **inline link**: rewrite a specific sentence in `card-a` to embed `[...](./card-b.md)`
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

**Invocation**: from the project root, run

```bash
python .claude/skills/project-wiki/scripts/audit.py
```

The script runs 8 deterministic checks against `wiki/` and (unless `--no-write` is passed) writes report files to `wiki/_meta/orphans.md`, `wiki/_meta/stale.md`, and `wiki/_meta/conflicts.md`. Exit code is nonzero if any issues found.

After it runs, **Claude reads the stdout output and summarises findings to the user**, then proposes fixes via other workflows (`link`, `promote`, `conflict-mark.py`). The script itself never auto-fixes.

Checks performed by the script:

1. **Orphans**: cards with zero inbound `frontmatter.links` from any other card. Likely candidates for inline-linking from a hub.
2. **Inline-orphan**: card appears in some `frontmatter.links` but **never** appears as an inline markdown link in any other card's prose. Means: indexed but not narratively woven. Propose where to weave it in.
3. **Dead-end cards**: cards with zero outbound links AND no `## 何時往下追` section. Suggest follow-ups.
4. **Stale**: source file `mtime` is newer than card `updated` field. Listed in `_meta/stale.md` for human review. Do not auto-update — the card author needs to decide what changed.
5. **Oversized cards**: any card body over ~2000 characters (≈ 500 tokens). Probably violates one-concept-per-card. Suggest split.
6. **Broken links**: an inline `[text](./xyz.md)` or `links: [xyz]` where no `xyz.md` exists in `cards/`.
7. **Single-sided conflicts**: card A has `conflicts: [B]` but card B does not list A. Conflict edges must be bidirectional — propose fixing.
8. **Inbox pending**: list files currently in `wiki/_inbox/` with their age (days since file mtime). Purely informational — does not push the user to process them.

`_meta/conflicts.md` is regenerated on every audit run from current frontmatter: pairs still listed in both sides' `conflicts:` are preserved (along with any human-written disagreement descriptions); pairs no longer mutually claimed are dropped.

## Operating conventions

- **Filenames**: `cards/<id>.md` where `<id>` matches the frontmatter `id`. Use kebab-case, lowercase, ASCII (no spaces, no CJK in filenames — but card titles and content can be any language). Lowercase matters for Linux case-sensitivity.
- **Card IDs are stable**. If you must rename, update all inbound links (frontmatter `links:` AND inline markdown links) across all cards in the same commit / batch.
- **Dates**: ISO format `YYYY-MM-DD`.
- **Source references**: always include exact lines (for code) or pages (for PDFs). `src/foo.ts:42-58`, `docs/spec.pdf` p.4-6.
- **Inline links**: standard CommonMark format `[display text](./other-card.md)`. Use `./` for same-folder cards; `../ref/...` and `../_root.md` for cross-folder. Display text should be the natural prose noun phrase, not the id.
- **No deletions without confirmation**. Even orphan cards stay until the user explicitly says delete. `ref/` items are never deleted by the skill.
- **Numbered proposal items**. Whenever a workflow presents two or more proposed changes for the user to confirm / edit / skip, prefix each item with `[1]`, `[2]`, `[3]`, ... so the user can reference them by number (`edit 2`, `skip 3`). Apply this even when items already have card-ids — the user shouldn't have to retype a long id like `decision-jwt-vs-session`. Numbers are local to one proposal; if some items are accepted and you re-propose the rest, renumber from 1.

## When to refuse or defer

- If the user asks to modify a source file (anything in `src/`, `docs/`, `meetings/`, or `wiki/ref/`), refuse — explain that sources are read-only and the wiki is a layer on top, not a replacement.
- If the user asks to mass-import a giant document without splitting, push back: propose how to split it into cards first.
- If `_root.md` doesn't exist yet, before doing anything else, propose creating it with the user.

## Initial setup

If `wiki/` doesn't exist when the skill is invoked:
1. Create `wiki/`, `wiki/cards/`, `wiki/_inbox/`, `wiki/ref/`, `wiki/_meta/`.
2. Create `wiki/_root.md` from the template above, with the project description filled in (ask user).
3. Optionally seed with a few top-level hub cards based on what's visible in the project root (e.g. if there's `src/auth/`, propose `auth-overview` as a stub).
