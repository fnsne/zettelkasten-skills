# project-wiki Entry Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `slice`, `relate`, and `fleet` workflows to the single `project-wiki` skill so card creation has clean entry points (file vs current discussion) over a shared, read-only judgement core — without creating any new skill.

**Architecture:** All changes are prose edits to one file, `.claude/skills/project-wiki/SKILL.md`. `slice` and `relate` are described as standalone read-only operations whose canonical rules already live in `extract` step 2 (no duplication — the new sections reference them). `fleet` is a thin entry adapter that writes a `_inbox/` note and hands off to the existing `extract` (which already owns inbox→ref promotion). The frontmatter `description` gains the new trigger phrasings plus a `jackli-work-log` disambiguation clause. One optional README touch-up follows.

**Tech Stack:** Markdown + YAML frontmatter. Verification via `grep` and a PyYAML frontmatter parse (PyYAML is already a skill dependency).

---

## File Structure

- **Modify:** `.claude/skills/project-wiki/SKILL.md`
  - frontmatter `description` (Task 1)
  - `## Workflows` intro line (Task 2)
  - three new workflow sections appended after Workflow 4 / before `## Operating conventions` (Tasks 3–5)
  - `extract` step 2 lead note (Task 6)
- **Modify (optional):** `README.md` — Features list (Task 7)

No script changes. `audit.py`, `conflict-mark.py`, `inbox-promote.py` are untouched (design out-of-scope).

Reusable verification snippet (referred to as **FM-CHECK** below):

```bash
python3 -c "
import yaml
t=open('.claude/skills/project-wiki/SKILL.md').read()
fm=t.split('---',2)[1]
d=yaml.safe_load(fm)
assert 'name' in d and 'description' in d, 'missing keys'
print('frontmatter OK:', d['name'])
"
```

---

### Task 1: Extend the skill `description` with new triggers + work-log disambiguation

**Files:**
- Modify: `.claude/skills/project-wiki/SKILL.md:3`

- [ ] **Step 1: Edit the description — add slice/relate/fleet triggers**

Replace this exact substring inside the `description:` line:

```
promote a card into a 主題卡 (hub card), audit wiki health, drop fleeting material into the inbox, or query the wiki to answer a project question.
```

with:

```
promote a card into a 主題卡 (hub card), audit wiki health, drop fleeting material into the inbox, slice a source into candidate cards, find the cards related to a piece of content, capture the current discussion into the inbox as a fleeting note, or query the wiki to answer a project question.
```

- [ ] **Step 2: Edit the description — add the disambiguation clause**

Replace this exact substring (end of the trigger sentence) inside the same `description:` line:

```
or when the user asks Claude to "find", "look up", or "summarize" something from project documentation.
```

with:

```
or when the user asks Claude to "find", "look up", or "summarize" something from project documentation. When the user asks to save or organise the current discussion and mentions card/閃記/inbox/wiki, this skill's `fleet` workflow applies; if it is ambiguous whether they want a wiki note or a work log, ask which first.
```

- [ ] **Step 3: Verify the frontmatter still parses and contains the new triggers**

Run **FM-CHECK** (above). Expected: `frontmatter OK: project-wiki`.

Then run:

```bash
grep -c "slice a source into candidate cards\|capture the current discussion into the inbox\|fleet` workflow applies" .claude/skills/project-wiki/SKILL.md
```

Expected: prints `1` (the description line matches all three patterns — grep counts the single line once per pattern set; if it prints `0`, the edits did not land).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/project-wiki/SKILL.md
git commit -m "SKILL: add slice/relate/fleet triggers + work-log disambiguation to description"
```

---

### Task 2: Update the `## Workflows` intro to seven workflows + grouping

**Files:**
- Modify: `.claude/skills/project-wiki/SKILL.md:202`

- [ ] **Step 1: Replace the intro sentence**

Replace this exact line:

```
The skill has four workflows. Always announce which one is running, and always run them semi-automatically (propose → confirm → write). Link maintenance is **not** a separate workflow — it's folded into `extract` as `[LINK]` items and surfaced by `audit` as missing-link findings.
```

with:

```
The skill has seven workflows. Always announce which one is running, and always run them semi-automatically (propose → confirm → write). They group as: **entry adapters** (`extract` from a source file, `fleet` from the current discussion) that funnel into a shared card pipeline; **read-only judgement steps** (`slice`, `relate`) that can be invoked standalone and are also called inside that pipeline; plus `query`, `promote`, and `audit`. Link maintenance is **not** a separate workflow — it's folded into `extract` as `[LINK]` items and surfaced by `audit` as missing-link findings.
```

- [ ] **Step 2: Verify**

```bash
grep -n "The skill has seven workflows" .claude/skills/project-wiki/SKILL.md
```

Expected: one match near line 202.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/project-wiki/SKILL.md
git commit -m "SKILL: update workflow count to seven with entry/judgement grouping"
```

---

### Task 3: Add Workflow 5 `slice` (read-only candidate map)

**Files:**
- Modify: `.claude/skills/project-wiki/SKILL.md` (insert before `## Operating conventions`)

- [ ] **Step 1: Insert the `slice` section**

Find the line `## Operating conventions` and insert the following block immediately **before** it (leave one blank line above and below):

````
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

````

- [ ] **Step 2: Verify**

```bash
grep -n "Workflow 5: \`slice\`" .claude/skills/project-wiki/SKILL.md
grep -c "read-only" .claude/skills/project-wiki/SKILL.md
```

Expected: the heading matches once; `read-only` count increases (≥ the count before this task).

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/project-wiki/SKILL.md
git commit -m "SKILL: add Workflow 5 slice — read-only candidate map from a source"
```

---

### Task 4: Add Workflow 6 `relate` (read-only related-cards + placement)

**Files:**
- Modify: `.claude/skills/project-wiki/SKILL.md` (insert directly after the `slice` section from Task 3)

- [ ] **Step 1: Insert the `relate` section**

Insert the following block immediately **after** the `slice` section's closing `**Boundary**:` paragraph and **before** `## Operating conventions`:

````
### Workflow 6: `relate` — find related cards/docs and where links go (read-only)

**Trigger**: user wants the cards/documents related to a piece of content, and where links should be placed. Phrasings: 「找跟這張卡相關的卡」「這段內容該連去哪」「relate 一下」.

**Shape**: read-only. Advisory only — writes nothing.

**Input**: a piece of content — an existing card id, a draft card, or a concept/snippet of text.

Steps:

1. Traverse the wiki from `_root.md` downward (the same scan as `extract` step 2's link-target search).
2. Collect related cards — same concept / nearby concept / candidate 主題卡 — and related source documents.
3. For each related card, state WHERE the link should go and in which direction(s): frontmatter `links:`, inline in `## 摘要` (definition-level mention), `## 何時往下追` (navigation hint), or a 主題卡's `## 子題導覽`. For each related document, note it goes under `sources:`.
4. Present the grouped suggestions:

   ```
   跟「JWT 簽發流程」相關的：
   卡片：
     - auth-overview            → 掛在它的「子題導覽」(主題卡)，雙向
     - decision-jwt-vs-session  → 摘要內聯一句「依當初決策…」
     - security-token-rotation  → 「何時往下追」放一條
   文件：
     - docs/auth-spec.pdf p.4-6 → 進 sources:
   ```

**Boundary**: `relate` only proposes; it edits no card. (Contrast: `extract`'s `[LINK]` items WRITE after confirmation — `relate` is the advisory-only version.) The user places the links, or asks Claude to apply them as a follow-up edit.

````

- [ ] **Step 2: Verify**

```bash
grep -n "Workflow 6: \`relate\`" .claude/skills/project-wiki/SKILL.md
```

Expected: one match, located after the Workflow 5 heading.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/project-wiki/SKILL.md
git commit -m "SKILL: add Workflow 6 relate — read-only related-cards and link placement"
```

---

### Task 5: Add Workflow 7 `fleet` (session → inbox entry adapter)

**Files:**
- Modify: `.claude/skills/project-wiki/SKILL.md` (insert directly after the `relate` section from Task 4)

- [ ] **Step 1: Insert the `fleet` section**

Insert the following block immediately **after** the `relate` section's closing `**Boundary**:` paragraph and **before** `## Operating conventions`:

````
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

````

- [ ] **Step 2: Verify**

```bash
grep -n "Workflow 7: \`fleet\`" .claude/skills/project-wiki/SKILL.md
grep -c "要記成 wiki 閃記，還是寫工作日誌" .claude/skills/project-wiki/SKILL.md
```

Expected: heading matches once; disambiguation line count is `1`.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/project-wiki/SKILL.md
git commit -m "SKILL: add Workflow 7 fleet — capture current discussion into inbox"
```

---

### Task 6: Reframe `extract` step 2 to name `slice`/`relate` as its standalone versions

**Files:**
- Modify: `.claude/skills/project-wiki/SKILL.md:230` (the step 2 paragraph)

- [ ] **Step 1: Add the cross-reference note**

Replace this exact sentence at the start of step 2:

```
2. **Identify candidates and scan the wiki.** Identify N independent concepts following the splitting rules. For each, traverse the wiki from `_root.md` to find:
```

with:

```
2. **Identify candidates and scan the wiki.** Identify N independent concepts following the splitting rules. *(This candidate-identification + NEW/EXPAND scan is the canonical home of the **`slice`** procedure, Workflow 5; the link-target scan in this step is the canonical home of **`relate`**, Workflow 6. Both can also be invoked standalone and read-only — `extract` runs them and then writes.)* For each, traverse the wiki from `_root.md` to find:
```

- [ ] **Step 2: Verify**

```bash
grep -c "canonical home of the \*\*\`slice\`\*\* procedure" .claude/skills/project-wiki/SKILL.md
```

Expected: `1`.

- [ ] **Step 3: Verify all seven workflow headings are present and ordered**

```bash
grep -n "^### Workflow [1-7]:" .claude/skills/project-wiki/SKILL.md
```

Expected: seven lines, Workflow 1 through 7, in ascending order (query, extract, promote, audit, slice, relate, fleet).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/project-wiki/SKILL.md
git commit -m "SKILL: name slice/relate as extract step 2's standalone read-only versions"
```

---

### Task 7 (optional): Note the new entry points in README Features

**Files:**
- Modify: `README.md`

Skip this task if you want to keep README changes out of this branch. It is a user-facing nicety only.

- [ ] **Step 1: Add a Features bullet**

In `README.md`, under the `## Features` list, after the existing `- **Inbox for fleeting notes** — ...` bullet, add:

```
- **Multiple entry points** — extract from a source file, or `fleet` the current discussion into the inbox; plus standalone read-only `slice` (what cards a source yields) and `relate` (which cards/docs a piece of content connects to)
```

- [ ] **Step 2: Verify**

```bash
grep -c "Multiple entry points" README.md
```

Expected: `1`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "README: note slice/relate/fleet entry points in Features"
```

---

## Self-Review

**Spec coverage** (checked against `docs/superpowers/specs/2026-06-01-wiki-entry-workflows-design.md`):

- "no new skill" → all edits are inside the one `project-wiki/SKILL.md` (Tasks 1–6). ✔
- `slice` spec (trigger / read-only / input / NEW-EXPAND map / boundary) → Task 3. ✔
- `relate` spec (trigger / read-only / input / placement annotations / boundary) → Task 4. ✔
- `fleet` spec (trigger / disambiguation / inbox write / handoff / no-move boundary) → Task 5. ✔
- extract minimal reframe (name slice/relate, walk-through & tail unchanged) → Task 6. ✔
- description triggers + work-log disambiguation → Task 1. ✔
- "seven workflows" count/grouping → Task 2. ✔
- SKILL.md size note → addressed by referencing extract for shared rules instead of duplicating (no separate task needed; nothing here warrants a `references/` split yet). ✔
- Out of scope (query/promote/audit/scripts unchanged; no proactive detection; no "jot" entry) → no tasks touch them. ✔

**Placeholder scan:** no TBD/TODO; every edit step contains the exact old/new text and every verify step an exact command + expected output. ✔

**Type/name consistency:** workflow numbering is additive (existing 1–4 unchanged; new 5/6/7 appended) — Task 6 step 3 asserts the full 1–7 ordering. The names `slice`, `relate`, `fleet` are used identically across the description (Task 1), intro (Task 2), their own sections (Tasks 3–5), and the extract note (Task 6). ✔
