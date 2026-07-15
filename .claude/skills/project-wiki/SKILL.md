---
name: project-wiki
description: Build and maintain a Zettelkasten-style project wiki under `wiki/` in a project folder. Cards are atomic markdown notes that link to each other Wikipedia-style (via standard markdown links) and reference (but never modify) source files like code, docs, PDFs, and meeting notes. Use this skill whenever the user wants to extract cards from project material, link related cards, promote a card into a 主題卡 (hub card), audit wiki health, drop fleeting material into the inbox, slice a source into candidate cards, find the cards related to a piece of content, capture the current discussion into the inbox as a fleeting note, or query the wiki to answer a project question. Trigger this skill for any mention of "card", "wiki", "Zettelkasten", "MOC", "knowledge base", "project notes", "inbox", or when the user asks Claude to "find", "look up", or "summarize" something from project documentation. When the user asks to save or organise the current discussion and mentions card/閃記/inbox/wiki, this skill's `fleet` workflow applies; if it is ambiguous whether they want a wiki note or a work log, ask which first. Prefer this skill over reading raw source files when a `wiki/` folder exists in the project — the wiki is designed to answer questions with far fewer tokens than scanning source.
---

# Project Wiki (Zettelkasten for Projects)

A Zettelkasten-style wiki that lives inside a project folder. Every card is an atomic markdown note. Cards link to each other Wikipedia-style — both as frontmatter metadata and inline in prose — using **standard CommonMark markdown links**, so any markdown viewer (VS Code, GitHub, GitLab, etc.) can render them as clickable links without extensions. Original source files (code, PDFs, docs, meeting notes) are never modified; cards reference them via path + line/page numbers.

## Core principles

1. **Flat structure, emergent hierarchy.** All cards live in `cards/`. There is no `index/` folder. A card becomes a **主題卡 (hub card)** by virtue of being linked-to and by its content, not by its location. The term "hub" is kept here for searchability; in user-facing prose, call it 主題卡.
2. **One concept per card.** The test: can you use the card's title as a noun phrase in another card's prose? If not, split it.
3. **Sources are read-only.** Cards link back to source via `sources:` frontmatter. Never edit source files. If source changes, mark the card stale in `_meta/stale.md`.
4. **Two link layers.** `frontmatter.links` is the machine-readable index (list of card ids). Inline standard markdown links `[display text](./other-card.md)` form the narrative — the wiki reads like Wikipedia, not like a directory.
5. **Semi-automatic — nothing reaches the live wiki unconfirmed.** No live `cards/` file is created or modified without explicit user approval. `promote` and one-off edits propose each change, show full content, and wait for a reply before writing. `extract` (v2) stages every draft in `wiki/_drafts/` first — **staging is not a live write** — then the user reviews and annotates, and a draft reaches live `cards/` only when the user ticks its OK box (one `go` action revises the `FB:`'d ones and writes the ticked ones, per-draft). Writing to `_drafts/` is the proposal; the tick is the confirmation. Never silently mass-edit live cards; a live card is never moved out to be edited (see `extract`).

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
    ├── _drafts/          # (v2) staged card drafts + edit proposals awaiting review & finalize
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

Underscore-prefix entries (`_root.md`, `_inbox/`, `_drafts/`, `_meta/`) are wiki infrastructure. The rest (`cards/`, `ref/`) are content.

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
title: JWT 簽發流程
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
```

（這張卡的出處 `src/auth/jwt.ts:12-89`、`docs/auth-spec.pdf` p.4-6 都記在上方 `sources:` frontmatter——出處不在內文出現,內文只連相關卡片。）

**Required fields**: `id`, `created`, `sources` (can be empty list), `links` (can be empty list).
**Recommended field**: `title` — the human-readable card title, mirroring the `# H1`. Lets Obsidian and similar tools show the concept name instead of the kebab-case `id` in backlinks, file explorer, and graph (see "Reading the wiki in Obsidian"). `slice` / `extract` / `fleet` write it on every new card.
**Optional fields**: `conflicts` (list of card-ids this card opposes — must be bidirectional, both sides list each other), `updated`, `tags`.
**Optional sections**: `## 前提與局限` (when the card's content is a claim/decision — record the assumptions it rests on, and when it would need re-evaluation), `## 衝突與爭議` (narrative explanation of disagreements, pairs with `conflicts:` frontmatter).
**Forbidden**: `type` field. A card's role (atomic / 主題卡 / decision / claim) is emergent from content, not declared.

### Two layers of links

| Layer | Where | Purpose | Audience |
|---|---|---|---|
| `frontmatter.links` | YAML (list of card ids) | Machine-readable index; used by `audit` and by `extract`'s `[LINK]` items; powers backlinks | Tooling |
| Inline `[text](./other-card.md)` | Within prose (摘要 / 內容, including bullet lists) | The card reads as continuous narrative, with concepts linking to their definitions; clickable in any markdown viewer. This is also the only navigation layer — "往下追" means following these links to the next related **card** | Humans + Claude reading the card |

Both should exist on most cards. Frontmatter `links` should be a superset of (or equal to) the cards mentioned inline.

**Links point card→card only.** A source file is never a link target in the body. The card is the detail distilled *from* its source, so the source is **provenance** — recorded in `sources:` frontmatter (with precise lines/pages for traceability), not a place the reader navigates *to*. There is no separate navigation section; the description and its bullet points already carry the "for X go to card Y" hints via inline links.

### Relative path conventions

Cards live in `wiki/cards/`. Common link targets and their relative paths:

| Target | Relative path from a card |
|---|---|
| Another card | `./other-card.md` |
| `_root.md` | `../_root.md` |
| A `ref/` item | `../ref/2026-05-20-架構討論.md` |
| Code in `src/` | `../../src/auth/jwt.ts` — recorded in `sources:` frontmatter (provenance) only; **never linked in the body**. The body links card→card. |

From `_root.md` (which lives in `wiki/`), links into `cards/` look like `./cards/auth-overview.md`.

## Card splitting rules

When extracting cards, apply these rules. They make inline linking possible.

**Rule 1 — One referenceable concept per card.** Title must be a noun phrase another card can use mid-sentence. ✅ "JWT 簽發流程", "使用者資料表結構", "為什麼選 JWT 而非 session". ❌ "Auth 相關的一些想法", "JWT 是怎麼運作的?", "5/12 會議記錄".

**Rule 2 — Summary opens with a definition sentence.** First sentence of `## 摘要` must define what this card is, in one sentence, so readers arriving via inline link grasp the concept immediately.

**Rule 3 — Granularity guide.**
- One decision → one card (e.g. "為什麼選 JWT")
- One flow/process → one card (e.g. "JWT 簽發流程")
- One schema/data structure → one card
- One module overview → one card (this often becomes a 主題卡)
- A meeting / PDF is **not** a card — it's a source. Extract the concepts inside it into multiple cards.

**Rule 4 — When in doubt, split.** Two concepts in one card means neither can be referenced cleanly. Splitting is cheap; merging via inline links is free.

**Rule 5 — Self-contained prose; the source is provenance, not a destination.** A reader must grasp the concept from the card alone, without opening any source file. The card is the detail distilled *from* its source, so the source is **where the card came from** — recorded in `sources:` frontmatter, never linked in the body and never used as a "go read it there" substitute for explaining. Two things follow:

- **Forbidden in card prose**: deferral words like 「詳見 / 詳閱 / 參見 / 參照 / (請)參考 … source / 原始檔 / 原文」 or "see source / refer to source" used *in place of* explaining. Telltale failure to avoid: after reading the card the reader still doesn't know *what the thing is* and would have to open the source to find out. **State the actual content in the card.**
- **No source link in the body.** "往下追" follows inline links to the next related **card**, not back to raw material. A source file never appears as a body link or `→` pointer; its location lives in `sources:` frontmatter (keep precise lines/pages there for traceability). Mentioning a path in prose as plain text is fine; linking it as a navigation target is not.

✅ 內文把概念講完,相關概念用 inline 連到別張卡:`…採 [stateless 設計](./decision-jwt-vs-session.md)…`;出處 `src/auth/jwt.ts:60-85` 寫在 `sources:`。
❌ `- rotation 細節詳見 src/auth/jwt.ts`  ❌ `- keyring 機制 → [src/auth/jwt.ts:1-120](../../src/auth/jwt.ts)` (source 不該是內文導覽目標)  ❌ `各欄位定義請參考 source`

> When a chunk of a source is itself one atomic unit (e.g. "120 個錯誤碼"), don't make a separate card that merely *describes* it: if that's the source's only content, just mention it where relevant; if the source also holds other concepts, extract that chunk **as one card**. Either way no "see the full list in source" body link is ever needed.

**Rule 6 — Link, don't restate (self-containment ≠ duplication).** Self-containment (Rule 5) means a reader grasps *this card's own* concept without opening a **source file** — it does **not** license re-explaining content that belongs to another **card**. When a card needs a concept that already has its own home card, give a **one-sentence orienting reference + an inline link**, never a re-explanation. The distinction:

- ✅ **Orienting reference** (keep — Rule 5 needs it): `…採 [stateless 設計](./decision-jwt-vs-session.md)，因此 token 無狀態…` — one sentence, then link.
- ❌ **Restating substance** (the smell): copying the linked card's actual reasoning / steps / field list / definition into this card. The same passage living in two cards means a concept has no single home.

**Fix when you catch duplication while extracting:**
- If the repeated block is itself a **referenceable concept** (its title passes Rule 1's noun-phrase test, and ≥2 cards need it) → **extract it into its own atomic card**, and replace every restatement with a link to it.
- Otherwise → pick **one owner card** for that content and have the others link to it.
- **Don't over-atomize**: only spin off a shared card when its title passes the noun-phrase test; never shatter prose into junk micro-cards to avoid a sentence of overlap. A one-sentence orienting reference is *not* duplication — a repeated paragraph / list / definition is.

> Why this rule exists: a card written to be self-contained, by a writer who doesn't feel the friction of retyping, will happily re-explain a sibling card's content inline. That is the main source of wiki-wide redundancy. The cure is the same one Zettelkasten always uses — one home per concept, everyone else links.

## Reading the wiki in Obsidian

The wiki renders in any markdown viewer, but [Obsidian](https://obsidian.md) is the best reader — it gives backlinks, a graph view, quick-switch, and full-text search over the cards. Guidance:

- **Open the `wiki/` folder itself as the vault**, not the parent project root. A code-repo root drags in `node_modules` / build output and can choke Obsidian's indexer. If you must open the project root (e.g. to follow inline links to docs that live outside `wiki/`), add the heavy folders (`node_modules/`, `dist/`) to Settings → Files & links → Excluded files.
- **Backlinks and the graph come from the inline `[text](./other-card.md)` links, not the frontmatter `links:` array** — Obsidian treats a bare-string `links:` list as plain properties, not edges. This is the practical reason every card weaves its links inline as well as listing them in frontmatter.
- **Readable titles**: Obsidian's backlinks / explorer / graph display the file's `id` (kebab-case), not the `# H1`. To show the human title instead, give each card a `title:` field (the workflows do this) and install the **Front Matter Title** community plugin, point it at the `title` property, and enable its Explorer / Graph / Backlink features. Filenames stay ASCII — so `id`s and links remain stable and Git-host-safe — while the UI shows the concept name.
- **Do not rename card files to CJK** to get readable names: it couples `id`s to non-ASCII filenames, risks NFC/NFD git mismatches across OSes, and breaks link rendering on Git hosts. The `title:` + plugin route gives the same readability without those costs.

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
| Audit (all 10 health checks + `_meta/` writes) | `scripts/audit.py` |
| Verify FB closure in `_drafts/` (no `FB:` left unanswered) after a `go` pass | `scripts/draft_audit.py` |
| Mark a bidirectional conflict between two cards | `scripts/conflict-mark.py` |
| Promote an inbox file to `ref/` and rewrite card `sources:` paths | `scripts/inbox-promote.py` |
| Concept identification, contradiction detection, link proposals, query traversal | Claude |
| All propose-confirm interaction with the user | Claude |

**Dependency**: the scripts require PyYAML (`pip install pyyaml`). They use `pathlib` and the standard library otherwise; no other deps.

**Script-first principle**: when an operation is fully deterministic — parsing frontmatter, checking link validity, moving files, writing bidirectional edges — invoke the script. Don't reimplement these as Claude tool calls. Scripts avoid editing mistakes and are 10–50× cheaper in tokens than reading every card.

---

## Workflows

The skill has seven workflows. Always announce which one is running, and always run them semi-automatically (propose → confirm → write). They group as: **entry adapters** (`extract` from a source file, `fleet` from the current discussion) that funnel into a shared card pipeline; **read-only judgement steps** (`slice`, `relate`) that can be invoked standalone and are also called inside that pipeline; plus `query`, `promote`, and `audit`. Link maintenance is **not** a separate workflow — it's folded into `extract` as `[LINK]` items and surfaced by `audit` as missing-link findings.

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

**Shape (v2 — batch-draft, not walk-through)**: the expensive generation happens **once, up front**, into a staging area (`wiki/_drafts/`); the user then reviews all drafts at reading speed, annotating feedback **inline in the draft files**; Claude revises in batch; and a draft **reaches live `cards/` only when the user ticks its OK box** (there is no separate "revise" vs "finalize" — one action handles each draft by its state). This decouples the user's review time from generation time, lets feedback be written where the content is (not re-described in chat), and — critically — **never moves or hides a live card**, so a parallel session can keep reading the wiki.

Two write targets, never confused (every draft filename carries a zero-padded ordinal prefix `NN-` matching the map order from step 3, so Obsidian's A–Z file sort lists them in review order):
- **NEW card** → a brand-new draft `wiki/_drafts/NN-<id>.md`. It does not exist in `cards/` yet, so no other session can be relying on it.
- **EDIT of an existing card** (`[EXPAND]` / `[LINK]` / `[SECTION?]`) → a proposal `wiki/_drafts/NN-<id>.edit.md` holding a ```diff against the live card. **The live `cards/<id>.md` is NOT moved, renamed, or modified during drafting** — it stays in place and findable; the change applies only once the user ticks the proposal's OK box.

Steps:

1. **Read the source material.** If it's a `_inbox/...` file, treat it as the originating source for the resulting cards.

2. **Identify candidates and scan the wiki.** Identify N independent concepts following the splitting rules. *(This candidate-identification + NEW/EXPAND scan is the canonical home of the **`slice`** procedure, Workflow 5; the link-target scan in this step is the canonical home of **`relate`**, Workflow 6. Both can also be invoked standalone and read-only — `extract` runs them and then writes.)* For each, traverse the wiki from `_root.md` to find:
   - Existing card on the same concept → mark as `[EXPAND]` instead of `[NEW]`.
   - Cards on nearby concepts → record as link targets.
   - Completely new branch with no 主題卡 → note for later `promote`.
   - **Contradicts a neighbor card?** Read the neighbor's prose and ask "do these make opposing claims about the same question?" Be conservative — different framings ≠ conflict; different conclusions on the same question = conflict. If yes, plan a `[CONFLICT?]` item.
   - **Rests on premises?** (language like "選 X 而非 Y" / "採 X 策略" / "前提是…") → plan a `[SECTION?]` item adding `## 前提與局限`.

   Then enumerate **`[LINK]` items** — every existing card that needs a back-link or a newly-discovered link, surfaced as its own walkthrough item so the user sees explicitly what will change in each affected card:
   - **Back-link of a `[NEW]` card**: for each card B listed in a new card A's `links:`, plan a `[LINK]` item updating B (add A to B's frontmatter `links:`, and where natural, weave an inline mention of A in B's prose). Exception: if B is *already* being modified by another item this batch (e.g., `[EXPAND] B`), fold the back-link into that item — don't create a redundant `[LINK]`.
   - **Missing link between existing cards**: if during the scan you notice that existing card X mentions a concept covered by another existing card Y but isn't linked to it, plan a `[LINK]` item X → Y. This is how plain link-maintenance happens — there is no separate `link` workflow.
   - One `[LINK]` item = one direction of a connection. Don't fold bidirectional changes into one item; each direction gets its own line so the user can accept/skip independently.

3. **Show the map.** List all planned items with title + intent only, in **dependency order**:
   - `[NEW]` cards first (so any `[LINK]` referencing them runs against real files)
   - `[LINK]` items grouped immediately after the item that motivated them (a `[NEW]`'s back-links, an existing missing-link)
   - `[EXPAND]` for 主題卡 after the cards they list
   - `[SECTION?]` / `[CONFLICT?]` after the cards they touch
   - `[UPDATE] _root.md` last

   Per the "Numbered proposal items" convention, prefix each with `[1]`, `[2]`, ...

   ```
   From src/auth/jwt.ts I propose 8 changes — going through them one at a time:

     [1] [NEW]       auth-jwt-flow
     [2] [LINK]      decision-jwt-vs-session ← auth-jwt-flow   (back-link of [1])
     [3] [NEW]       auth-refresh-token
     [4] [EXPAND]    auth-overview — add new sub-cards to 子題導覽
                       (this item also carries the back-links from [1] and [3])
     [5] [LINK]      security-overview → user-session-model   (missing link found during scan)
     [6] [SECTION?]  decision-jwt-vs-session — add 前提與局限
     [7] [CONFLICT?] auth-jwt-flow ↔ decision-jwt-vs-session
     [8] [UPDATE]    _root.md (no change — auth-overview already linked)

   Proceed? (回 y 開始；要調整提案內容或跳過幾項，講一下即可)
   ```

   A `y` here approves **which cards to draft** (the outline / slice), not their content — it is the cheap up-front checkpoint that constrains generation and is the single most effective place to prevent the model from "writing the wrong thing". The user drops / splits / merges / adds here. Approving the outline is **not** approval of any card body — that is reviewed later, as drafts.

4. **Batch-write every approved item as a draft to `wiki/_drafts/` (one generation pass).** Write them **all** in this pass, in dependency order — the user waits exactly once. **Do not touch `cards/` at all in this step.** Every draft carries `status: draft` in frontmatter and ends with the pre-seeded REVIEW template (below), so the user never has to remember or type the markers.
   - `[NEW]` → `wiki/_drafts/NN-<id>.md`: the full card (frontmatter + body), `status: draft` in frontmatter.
   - `[EXPAND]` / `[LINK]` / `[SECTION?]` → `wiki/_drafts/NN-<id>.edit.md`: frontmatter `target: cards/<id>.md` + `type: edit` + `status: draft`; body = the proposed change as a ```diff fenced block **against the current live card**. The live card is left untouched.
   - `[CONFLICT?]` → `wiki/_drafts/NN-<a>__<b>.conflict.md`: frontmatter `status: draft`; body = both sides' claims + the proposed mark.
   - **`NN-` is a zero-padded ordinal** (`01-`, `02-`, …) following the dependency order of the step-3 map — purely so the files sort in review order in Obsidian. It is **not** part of the card id, and is dropped at finalize; for `EDIT`/`CONFLICT?` the real target always comes from the proposal's `target:` frontmatter, never the filename.
   - Use the per-type content formats below as the draft body. Run the self-containment check (below) on every `[NEW]`/`[EXPAND]` body **before** writing the draft.

   **The interface is two marks the user writes, both at the bottom of the file:** a `FB:` line = a feedback note; the `- [ ] OK` checkbox = approval — tick it (`- [x]`) only after you've seen the revised result and you're happy. Reject by deleting the file. Nothing else to learn. (Approval naturally comes **last**, after the revise loop converges — so the tick is the final act, not an up-front gate.) **One mark Claude writes back:** an `RE:` line under a `FB:` — Claude's reply/question when it couldn't cleanly apply that note (see step 5). The user answers it in a `FB:` line; the whole exchange threads in the file, never in chat. **History is kept, not erased:** once Claude addresses a note it marks it `FB✓:` (and a resolved `RE:` becomes `RE✓:`) but leaves the text in place, so the full feedback log stays visible until the card is finalized.

   **Pre-seed this REVIEW block at the end of every draft file** so the marks are already there to fill:
   ```
   <!-- ── REVIEW（finalize 不會把這段寫進正式卡）──
     要改這張 → 在下面 FB: 後面寫（一行一則）
     這張OK   → 勾下面的 checkbox（Obsidian 直接點；或打 x）
     不要這張 → 直接刪掉這個檔
     看到 RE: → 那是我對你 FB 的回問，請在 FB: 回我
     FB✓:/RE✓: → 我已處理過的紀錄（保留著，別刪也不用理）
   ──────────────────────────────────────── -->
   FB:

   - [ ] OK，可以寫進正式卡（看完改好的結果再勾）
   ```
   The checkbox is **live markdown, outside the comment**, so Obsidian renders it as a clickable box; the comment above only carries the instructions.

   Then print the **next step** to the user, in one message (no per-item stop):
   > 草稿都寫好在 `wiki/_drafts/`（共 N 張）。請在編輯器 / Obsidian 看，每張底部已附說明：
   > • 要改 → 在該檔 `FB:` 後面寫　• OK → 勾該檔的 `- [ ] OK` checkbox　• 不要 → 刪檔
   > 弄好就回來說「go」（一個動作：有 `FB:` 的我改、已勾 OK 的寫進正式卡；沒好的留著下輪）。

   **Self-containment check before writing any `[NEW]` / `[EXPAND]` draft (Card splitting Rule 5).** Scan the draft body for: (a) deferral words (詳見 / 詳閱 / 參見 / 參照 / 請參考 / 見 source / 見原始檔 / "see source") used in place of explaining; (b) **any source file linked or `→`-pointed in the body** (e.g. `[…](../../src/…)` or `→ \`src/auth/jwt.ts:1-120\``). If found, **rewrite before displaying**: state the substance in the card, move the source location to the `sources:` frontmatter (provenance), and make sure every body link points card→card. Never show or write a card that defers the reader to a source or uses a source as a navigation target.

   Draft-body content by type (write this as the draft file body — the trailing question line shown in each example is the old walk-through prompt; **omit it** in the draft file):

   **`[NEW]`** — show the complete draft card (frontmatter + body):
   ```
   [1/8] [NEW] auth-jwt-flow

   ---
   id: auth-jwt-flow
   title: JWT-based stateless auth flow
   tags: [auth, jwt]
   links: [auth-overview, decision-jwt-vs-session]
   sources: [src/auth/jwt.ts:1-58]
   created: 2026-05-22
   ---

   ## 摘要
   JWT-based stateless auth flow used by /api routes.

   ## 內容
   [auth-overview](./auth-overview.md) 採 JWT 作為 access token,登入後簽發。
   - refresh 由 [auth-refresh-token](./auth-refresh-token.md) 負責
   - 選型理由見 [decision-jwt-vs-session](./decision-jwt-vs-session.md)

   這張卡片如何？
   ```

   **`[LINK]`** — show what the affected card will gain (frontmatter line + optional inline diff). Used both for back-links of `[NEW]` items and for missing links between existing cards:
   ```
   [2/8] [LINK] decision-jwt-vs-session ← auth-jwt-flow

   target card: decision-jwt-vs-session.md
   frontmatter:
     links: [..., auth-jwt-flow]              # 加入 auth-jwt-flow

   §內容 改寫（line 12 附近）:
   - 此決策影響 JWT 流程設計。
   + 此決策影響 [JWT 流程](./auth-jwt-flow.md)設計。

   這個連結如何？
   ```

   **`[EXPAND]`** — show frontmatter changes and the prose diff:
   ```
   [4/8] [EXPAND] auth-overview

   frontmatter:
     links: [..., auth-jwt-flow, auth-refresh-token]

   在 ## 子題導覽 後插入:
      ## 子題導覽
      - ...(既有條目)
   +  - [auth-jwt-flow](./auth-jwt-flow.md) — JWT 簽發與驗證流程
   +  - [auth-refresh-token](./auth-refresh-token.md) — refresh token 設計

   這樣 expand 如何？
   ```

   **`[SECTION?]`** — show the section and where it goes:
   ```
   [6/8] [SECTION?] decision-jwt-vs-session — add 前提與局限

   在 ## 內容 之後插入:
      ## 前提與局限
      本決策前提是 token 生命週期 < 1hr。
      若改長期 token,需重評 revocation 機制。

   要這樣加嗎？
   ```

   **`[CONFLICT?]`** — show both sides and what would be written if marked; hint possible directions in the question, not as a fixed menu:
   ```
   [7/8] [CONFLICT?] auth-jwt-flow ↔ decision-jwt-vs-session

   auth-jwt-flow: "JWT 適合所有 stateless 場景"
   decision-jwt-vs-session: "JWT 僅限低敏感場景,因 revocation 缺陷"

   如果只是標起來，會做:
     兩張卡 frontmatter 互加 conflicts:
     _meta/conflicts.md 新增: "JWT 適用範圍 vs revocation 缺陷"

   這個怎麼處理？可以只標起來、現在 reconcile 一邊或合併重寫、或判定不算真衝突。
   ```

5. **Process the batch — one action that revises and finalizes, decided per-draft.** There is **no separate "revise" vs "finalize"**: a draft is *done* exactly when its `- [x] OK` box is ticked. When the user says they've reviewed (any of 「go」 / 「處理」 / 「revise」 / 「finalize」 means this), scan **every** file in `wiki/_drafts/` and act on each by its current state:

   - **Has an open `FB:`** (a `FB:` line with text, not yet marked done) → **revise** it: apply the note, then **mark that line `FB✓:` and keep its text** — addressed notes stay as a visible history so the user never loses track of what was asked. Always keep one fresh bare `FB:` line at the bottom for the next note. If the note is ambiguous / infeasible / conflicts with a rule or another card / you disagree → don't guess, drop, or comply blindly: write an `RE:` line under that `FB:` and leave the `FB:` open. When the user answers an `RE:` (in a following `FB:`), resolve it and mark the `RE:` as `RE✓:` (kept as history) too. **Keep the draft in `_drafts/`, leave it unticked** — a revised draft is never written live in the same pass it was revised; the user must see the diff first.
   - **Ticked `- [x]`, with no *open* `FB:`/`RE:` left** (resolved `FB✓:` / `RE✓:` history doesn't count as open) → **finalize** it (the only thing that touches live `cards/`):
     - `[NEW]` → strip the `status` field + the whole REVIEW block (including the `FB✓:`/`RE✓:` history), then move `wiki/_drafts/NN-<id>.md` → `wiki/cards/<id>.md` (**drop the `NN-` prefix**).
     - `[EDIT]` → **re-read the current live card** (resolve from the proposal's `target:` frontmatter, not the filename; it may have changed since the diff was drafted), apply the change to that current content, then delete the proposal. If it no longer fits, **stop and show the mismatch** instead of applying.
     - `[CONFLICT?]` → per the mapping below (mark or reconcile).
     - Then apply the `[LINK]` back-links / missing-links to live cards (the `[NEW]` ones are now real files), and clear the finalized drafts from `_drafts/`.
   - **Ticked but still has an open `FB:`/`RE:`** → **flag, don't write** — 『這張你勾了 OK，但還有未解的 RE:/FB:，確定照現狀寫？』 — never silently overwrite an open thread.
   - **Unticked, no `FB:`** → leave it; the user hasn't decided.

   **The two branches never collide in one pass**: revising means the draft had an open `FB:` (so it isn't ticked-and-clean → not eligible to finalize); finalizing means it was ticked and clean (so there was nothing to revise). Each draft does exactly one of the two per pass. **Never tick a box yourself** — the tick is the user's, given only after they've seen your revision as a **git diff of `wiki/_drafts/`** (only what changed lights up; a NEW draft is read in full once, every revision after is a diff).

   **FB-closure invariant — every `FB:` must end the pass with a visible answer.** A `FB:` line carrying the user's text may **not** be left unchanged: by the end of the pass it is either applied (renamed `FB✓:`, text kept) or replied to (an `RE:` written beneath it). A silently-unchanged `FB:` — no `FB✓:`, no `RE:`, no tick — is the **one outcome the user cannot see**: they can't tell whether you ever read the note. So the pass is **not done** while any such note remains. This is not optional and there is no "the change was too small to mark" exception — applying a note without renaming it to `FB✓:` still leaves the user blind, so the mark IS the work.

   Then run the deterministic guard (it verifies the invariant mechanically — it does not rely on you having remembered):
   ```
   python .claude/skills/project-wiki/scripts/draft_audit.py
   ```
   It lists every unanswered `FB:` (**must be 0**) and every open `RE:` awaiting the user. **If it reports any unanswered FB, you missed one** — handle it, then re-run until unanswered = 0. If the source was an inbox item and ≥1 card was finalized this pass, run `inbox-promote.py` (below).

   **Closure report — paste the guard's output, then account for every note per-draft**, not just totals: for each touched draft, one line saying what happened to each note — `FB✓:`（已照做）/ `RE:`（我回問了什麼）/ finalized / 待決 — so the user sees each note's fate without opening a single file. End with **finalized X**, **revised Y**（再看一次 diff）, **still open Z**（`RE:`/未決）. Loop until `_drafts/` is empty.

6. **Cross-session safety.** Because live `cards/` is touched only when a draft is finalized (ticked + clean), a parallel session (e.g. one running implementation while this one extracts) always sees the **stable, findable, approved** wiki — drafts and edit-proposals live only in `_drafts/` and never shadow a live card. The one real hazard, two sessions finalizing edits to the **same** card, is handled by the finalize branch's "re-read live, then apply, stop on mismatch".

**`[CONFLICT?]` finalize mapping** — map the user's intent to the right write:
   - Mark only ("標起來" / "標一下") → invoke `python .claude/skills/project-wiki/scripts/conflict-mark.py <card-a> <card-b> --description "<one-liner>"`. The script bidirectionally adds the conflict to both cards' `conflicts:` frontmatter and appends to `_meta/conflicts.md`. Do **not** modify either card's prose.
   - Reconcile ("現在處理" / "想 reconcile") → enter a resolution sub-flow: ask whether to (a) keep one side and rewrite the other, (b) reconcile both into one revised wording, or (c) create a new card framing both as valid under different conditions. Show the diff. Re-ask before writing.
   - Not really a conflict / skip → no action.

**Inbox promotion at finalize** — when the source was an inbox item and ≥1 card was finalized, run `python .claude/skills/project-wiki/scripts/inbox-promote.py wiki/_inbox/<filename>`. The script moves the file to `wiki/ref/` and rewrites any card's `sources:` path that referenced the old `_inbox/` location. The inbox file is **never deleted** — it's preserved in `ref/` for traceability.

**Never** edit source files in `src/`, `docs/`, `meetings/`, or `ref/`.

### Workflow 3: `promote` — turn a card into a 主題卡, or create a new 主題卡

**Trigger**: user requests, or `audit` flags that a topic now has > ~5 cards with no 主題卡.

Steps:
1. Identify the cluster of related cards.
2. Choose between:
   - **Expand an existing card** into a 主題卡 (preferred if one card is already broadly about the topic).
   - **Create a new 主題卡** if no good candidate exists.
3. The 主題卡 must have:
   - A definition sentence summarizing the whole subtopic
   - A "子題導覽" section listing all cluster cards with one-line descriptions
   - Inline links to the most important sub-cards woven into a short narrative
4. Update `_root.md` if this is a top-level 主題卡. Propose the change; confirm before writing.

### Workflow 4: `audit` — health check

**Trigger**: user asks "check the wiki" / "what's broken".

**Invocation**: from the project root, run

```bash
python .claude/skills/project-wiki/scripts/audit.py
```

The script runs 10 deterministic checks against `wiki/` and (unless `--no-write` is passed) writes report files to `wiki/_meta/orphans.md`, `wiki/_meta/stale.md`, and `wiki/_meta/conflicts.md`. Exit code is nonzero if any issues found.

After it runs, **Claude reads the stdout output and summarises findings to the user**, then proposes fixes — typically by re-invoking `extract` (which handles new cards + `[LINK]` items), `promote` for 主題卡, or `conflict-mark.py` for marking conflicts. The script itself never auto-fixes.

Checks performed by the script:

1. **Orphans**: cards with zero inbound `frontmatter.links` from any other card. Likely candidates for inline-linking from a 主題卡.
2. **Inline-orphan**: card appears in some `frontmatter.links` but **never** appears as an inline markdown link in any other card's prose. Means: indexed but not narratively woven. Propose where to weave it in.
3. **Dead-end cards**: cards with zero outbound card links (no `frontmatter.links` and no inline `[...](./other.md)`). Suggest related cards to link.
4. **Stale**: source file `mtime` is newer than card `updated` field. Listed in `_meta/stale.md` for human review. Do not auto-update — the card author needs to decide what changed.
5. **Oversized cards**: any card body over ~2000 characters (≈ 500 tokens). Probably violates one-concept-per-card. Suggest split.
6. **Broken links**: an inline `[text](./xyz.md)` or `links: [xyz]` where no `xyz.md` exists in `cards/`.
7. **Single-sided conflicts**: card A has `conflicts: [B]` but card B does not list A. Conflict edges must be bidirectional — propose fixing.
8. **Inbox pending**: list files currently in `wiki/_inbox/` with their age (days since file mtime). Purely informational — does not push the user to process them.
9. **Source-deferral prose**: card bodies containing deferral words (詳見 / 詳閱 / 參見 / 參照 / 請參考·參考 …near a source / `src/` / `docs/` / code or PDF path, "see source / refer to source"). These violate self-containment (Card splitting Rule 5) — the reader is told to go read the source instead of being told what the thing is. Reported as rewrite candidates; the script does not auto-fix. (Deterministic word match — pairs with check 10 and the Claude-side check below.)
10. **Source linked in body**: a source file used as a navigation target in the card body — a markdown link whose target is a source file (`[…](../../src/…)`, code/doc path), or a `→` pointer to a backtick source path. Source belongs in `sources:` frontmatter (provenance); the body links card→card (Rule 5). Triggers on the **shape of the link**, never on the noun "source" — a card discussing 「data source / 資料來源」, or a bare backtick path mentioned in prose (no link, no `→`), is untouched. Reported as rewrite candidates: state the substance, move the location to `sources:`.

**Claude-side check (semantic, not script-driven): missing links.** After the script's deterministic checks, Claude scans the wiki for cards whose prose mentions a concept covered by another existing card — by title, close paraphrase, or strong topical overlap — without being linked to it. Reports these as **missing-link candidates**. Fix path depends on what the user wants:
- For one or two specific links, the user can just tell Claude "幫我把 X 連到 Y" and Claude does the edit directly (no workflow needed for a one-off).
- For a related batch (e.g., all stem from the same source), re-invoke `extract` on that source; the missing connections show up as `[LINK]` items in its walkthrough.

**Claude-side check (semantic): non-self-contained cards.** Checks 9–10 catch deferral *words* and source *links* in the body; Claude reads card bodies for the residual semantic failure neither can see — substance deferred to a source while the prose never says *what* the thing is, even with no trigger word or link (e.g. a card that gestures at "the validation logic" without describing it). Report these as rewrite candidates (Card splitting Rule 5). Fix by stating the substance in the card — directly, or by re-invoking `extract` on the card's source.

**Claude-side check (semantic): duplicated substance across cards.** The opposite smell to missing-links: two or more cards that **restate the same substance** (same reasoning / steps / field list / definition) instead of one owning it and the rest linking (Card splitting Rule 6). Claude reads card bodies and reports each cluster with the duplicated block and a proposed fix — either **extract the shared concept into its own atomic card** (when its title passes the noun-phrase test and ≥2 cards need it) and replace the restatements with links, or **name one owner card** and turn the other copies into a one-sentence orienting reference + link. **Be conservative**: a one-sentence orienting reference is intended and is *not* flagged; only a repeated *paragraph / list / definition* of substance counts (mirror of the missing-links check — same scan, opposite direction). Apply via `extract` (the shared card surfaces as `[NEW]`, the de-duplication as `[EDIT]`/`[LINK]` items) or, for a one-off, a direct edit.

`_meta/conflicts.md` is regenerated on every audit run from current frontmatter: pairs still listed in both sides' `conflicts:` are preserved (along with any human-written disagreement descriptions); pairs no longer mutually claimed are dropped.

### Workflow 5: `slice` — list candidate cards in a source (read-only)

**Trigger**: user wants to see what cards/knowledge points could be cut out of a source, without committing to writing them. Phrasings: 「這份文件能切出哪些知識點」「slice 一下這份」「這份有哪些卡可以做」.

**Shape**: read-only. Produces a proposal map and stops. Writes nothing.

**Input**: one source — a file under `src/`, `docs/`, `meetings/`, or an item under `wiki/_inbox/`.

Steps:

1. Read the source.
2. Run `extract` step 2's candidate-identification: identify N independent concepts per the splitting rules (Rules 1–4 in "Card splitting rules"), and do the light wiki scan from `_root.md` to tag each `NEW` or `EXPAND → <card-id>` (an existing card already covers it).
3. Present the numbered map (title + tag + one-line description), then ask which to write:

   ```
   從 docs/auth-spec.pdf 可以切出這些知識點：
     [1] JWT 簽發流程            (NEW)
     [2] refresh token 設計      (NEW)
     [3] token 撤銷策略          (EXPAND → security-token-rotation)
     [4] 為什麼選 JWT            (NEW，像 decision 卡)
   要寫哪幾張？(挑了就接 extract；或我可以只列不做)
   ```

**Boundary**: `slice` does NOT enumerate `[LINK]` items, propose conflicts/premises, or write any file — those belong to the full `extract` walk-through. `slice` is exactly `extract` steps 1–2's candidate map surfaced as a standalone, stop-early operation. When the user picks cards to write, continue into `extract` from step 3 onward.

### Workflow 6: `relate` — find related cards/docs and where links go (read-only)

**Trigger**: user wants the cards/documents related to a piece of content, and where links should be placed. Phrasings: 「找跟這張卡相關的卡」「這段內容該連去哪」「relate 一下」.

**Shape**: read-only. Advisory only — writes nothing.

**Input**: a piece of content — an existing card id, a draft card, or a concept/snippet of text.

Steps:

1. Traverse the wiki from `_root.md` downward (the same scan as `extract` step 2's link-target search).
2. Collect related cards — same concept / nearby concept / candidate 主題卡 — and related source documents.
3. For each related card, state WHERE the link should go and in which direction(s): frontmatter `links:`, inline in `## 摘要` (definition-level mention), inline in `## 內容` (including a bullet in its list), or a 主題卡's `## 子題導覽`. For each related document, note it goes under `sources:` (provenance — never a body link).
4. Present the grouped suggestions:

   ```
   跟「JWT 簽發流程」相關的：
   卡片：
     - auth-overview            → 掛在它的「子題導覽」(主題卡)，雙向
     - decision-jwt-vs-session  → 摘要內聯一句「依當初決策…」
     - security-token-rotation  → 內容裡放一條 inline 連結
   文件：
     - docs/auth-spec.pdf p.4-6 → 進 sources:
   ```

**Boundary**: `relate` only proposes; it edits no card. (Contrast: `extract`'s `[LINK]` items WRITE after confirmation — `relate` is the advisory-only version.) The user places the links, or asks Claude to apply them as a follow-up edit.

### Workflow 7: `fleet` — capture the current discussion into the inbox

**Trigger**: user wants to turn the current session's discussion into wiki material. Phrasings: 「把這段討論記成閃記」「整理成卡片初稿」「fleet」「把我們討論的整理進 wiki」.

**Disambiguation**: only enter `fleet` when the message mentions 卡片 / 閃記 / inbox / wiki. If it is ambiguous whether the user wants a wiki note or a work log (the `jackli-work-log` skill also reacts to 「把這段討論存起來」「整理一下」), ask first: 「要記成 wiki 閃記，還是寫工作日誌？」

**Shape**: a thin entry adapter. It only writes a fleeting note; it does not extract cards or move files.

Steps:

1. Identify the relevant span of the current discussion. If unclear, confirm with the user which part to capture.
2. Write it to `wiki/_inbox/YYYY-MM-DD-slug.md` as free-form markdown (low friction — no required frontmatter or structure). This file is the originating source for any cards later extracted from it.
3. Show the draft and confirm.
4. Ask 「要現在接著萃取成卡片嗎？」 — on yes, run `extract` (Workflow 2) on the new inbox file (which offers `slice` → walk-through). On no, leave it in `_inbox/` for later.

**Boundary**: `fleet` creates ONLY the inbox file; it moves nothing. The inbox→`ref/` promotion happens at `extract`'s tail (step 6, `inbox-promote.py`), and only when at least one card was written. So `fleet` followed by `extract` with zero cards written leaves the file in `_inbox/`.

## Operating conventions

- **Filenames**: `cards/<id>.md` where `<id>` matches the frontmatter `id`. Use kebab-case, lowercase, ASCII (no spaces, no CJK in filenames — but card titles and content can be any language). Lowercase matters for Linux case-sensitivity.
- **Card IDs are stable**. If you must rename, update all inbound links (frontmatter `links:` AND inline markdown links) across all cards in the same commit / batch.
- **Dates**: ISO format `YYYY-MM-DD`.
- **Source references**: always include exact lines (for code) or pages (for PDFs). `src/foo.ts:42-58`, `docs/spec.pdf` p.4-6.
- **Inline links**: standard CommonMark format `[display text](./other-card.md)`. Use `./` for same-folder cards; `../ref/...` and `../_root.md` for cross-folder. Display text should be the natural prose noun phrase, not the id.
- **No deletions without confirmation**. Even orphan cards stay until the user explicitly says delete. `ref/` items are never deleted by the skill.
- **Numbered proposal items**. Whenever a workflow presents two or more items in a single list (typically the map step of a walk-through), prefix each with `[1]`, `[2]`, `[3]`, ... so the user can reference them by number when responding (e.g. "跳過 4 和 5"). Apply this even when items already have card-ids — the user shouldn't have to retype a long id like `decision-jwt-vs-session`. Numbers are local to one proposal; if you re-propose after some items are handled, renumber from 1.
- **Interpreting natural-language replies in walk-through workflows**. When asking the user about a single proposal (e.g., "這張卡片如何？"), do not present a fixed `(y) / (e) / (s)` menu — interpret the reply by intent:
  - 採納 ("好", "可以", "沒問題", "寫吧", "yes"), **as a reply to the displayed draft** → apply the change as drafted. Approval the user gave *before* the draft was on screen (a map-level "y", a standing 「趕時間」) does not count — show the full content and wait for a fresh reply.
  - 跳過 ("跳過", "不要", "算了", "下一個", "skip") → don't apply; move on
  - 具體修改 ("摘要改成 X", "link 拿掉 Y", "加個 tag Z") → apply the edit, re-display the full updated draft **as a colour diff** (per step 4 "Re-display after an adjustment — colour the change": whole draft inside a ```diff block, only the changed lines marked `-`/`+`), ask again
  - 中止 ("停", "全部不要了", "abort") → stop the workflow; already-applied items stay
  - 提問 / 不確定 ("為什麼這樣寫", "我不太懂") → discuss; do not apply yet
  - 模糊不清 → ask back for clarification, never guess

## When to refuse or defer

- If the user asks to modify a source file (anything in `src/`, `docs/`, `meetings/`, or `wiki/ref/`), refuse — explain that sources are read-only and the wiki is a layer on top, not a replacement.
- If the user asks to mass-import a giant document without splitting, push back: propose how to split it into cards first.
- If `_root.md` doesn't exist yet, before doing anything else, propose creating it with the user.

## Initial setup

If `wiki/` doesn't exist when the skill is invoked:
1. Create `wiki/`, `wiki/cards/`, `wiki/_inbox/`, `wiki/ref/`, `wiki/_meta/`.
2. Create `wiki/_root.md` from the template above, with the project description filled in (ask user).
3. Optionally seed with a few top-level 主題卡 based on what's visible in the project root (e.g. if there's `src/auth/`, propose `auth-overview` as a stub).
