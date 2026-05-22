# project-wiki

A [Claude Code](https://claude.com/claude-code) skill for building and maintaining a Zettelkasten-style project wiki — atomic markdown cards that cross-reference each other Wikipedia-style and reference (but never modify) source files like code, PDFs, and meeting notes.

The wiki is designed to be **read primarily by Claude** to answer your project questions with far fewer tokens than scanning source files; humans can also browse it through any standard markdown viewer (VS Code, GitHub, GitLab, Obsidian).

## Features

- **Atomic, linkable cards** — one concept per card, cross-references via standard CommonMark markdown links
- **Source files stay read-only** — cards reference paths + line/page numbers; your code, docs, and meeting notes are never edited
- **Inbox for fleeting notes** — drop captures into `wiki/_inbox/`, Claude helps turn them into cards later; processed items are preserved in `wiki/ref/`
- **Conflict tracking** — when two cards make opposing claims, mark a bidirectional conflict and surface it on audit
- **Premise tracking for decisions** — optional `## 前提與局限` section records the assumptions a decision rests on
- **Health checks via script** — `audit.py` runs 8 deterministic checks (orphans, broken links, stale sources, etc.) without burning LLM tokens
- **Semi-automatic** — every change is proposed and confirmed; nothing is silently mass-edited

## Installation

### Project-level (recommended)

Drop this skill into the project where you want the wiki:

```bash
# From your project root
mkdir -p .claude/skills
git clone https://github.com/<your-user>/zettelkasten-skills.git .claude/skills/zettelkasten-skills
```

Or copy just the skill directory:

```bash
mkdir -p .claude/skills/project-wiki
cp -r /path/to/zettelkasten-skills/.claude/skills/project-wiki/* .claude/skills/project-wiki/
```

### Global (across all projects)

Install once under `~/.claude/skills/`:

```bash
git clone https://github.com/<your-user>/zettelkasten-skills.git ~/.claude/skills/zettelkasten-skills
```

### Script dependencies

The deterministic helper scripts (`audit.py`, `conflict-mark.py`, `inbox-promote.py`) require **PyYAML**:

```bash
pip install pyyaml
```

That's the only external dependency. Everything else uses Python's standard library.

## Initialization

From your project root, ask Claude:

> 幫我在這個專案建立 project wiki

or in English:

> Initialize a project wiki here

Claude will:

1. Create `wiki/` with `cards/`, `_inbox/`, `ref/`, `_meta/` subfolders
2. Create `wiki/_root.md` as the single entry point (after asking you for a one-sentence project description)
3. Optionally propose initial hub cards based on what it sees in `src/`, `docs/`, `meetings/`

Manual setup, if you prefer:

```bash
mkdir -p wiki/{cards,_inbox,ref,_meta}
# Then create wiki/_root.md following the template in SKILL.md
```

## Usage

### Natural-language driven (the usual way)

The skill recognises these intents in conversation with Claude:

| When you say... | Claude runs... |
|---|---|
| "幫我萃取 `docs/auth-spec.pdf`" | `extract` — read source, propose cards, write after confirmation |
| "把這段想法加到 inbox" | Create `wiki/_inbox/<date>-<slug>.md` |
| "處理一下 inbox" | List pending items, then extract from each |
| "找找 `auth-overview` 應該連到哪些卡" | `link` — propose missing connections |
| "auth 這幾張該有個 hub" | `promote` — turn one card into a hub, or create a new one |
| "JWT 是怎麼設計的？" | `query` — traverse cards to find the answer |
| "check 一下 wiki" | `audit` — run health checks (runs `audit.py`, near-zero token cost) |

### Direct script invocation

The deterministic operations can also be invoked from the shell:

```bash
# Audit (writes _meta/orphans.md, _meta/stale.md, _meta/conflicts.md)
python .claude/skills/project-wiki/scripts/audit.py

# Mark a bidirectional conflict between two cards
python .claude/skills/project-wiki/scripts/conflict-mark.py \
  auth-jwt-flow decision-jwt-vs-session \
  --description "JWT 適用範圍 vs revocation 缺陷"

# Promote an inbox file to ref/ after extraction
python .claude/skills/project-wiki/scripts/inbox-promote.py \
  wiki/_inbox/2026-05-22-jwt-想法.md
```

All scripts support `--help`, `--dry-run`, and `--wiki <path>` (for non-default wiki locations).

## Project structure produced by the skill

```
your-project/
├── src/                # your code (read-only by skill)
├── docs/               # your design docs / PDFs (read-only)
├── meetings/           # meeting notes (read-only)
└── wiki/               # everything the skill creates lives here
    ├── _root.md        # the one fixed entry point
    ├── _inbox/         # fleeting material awaiting processing
    ├── cards/          # all cards, flat structure
    ├── ref/            # post-inbox source material, read-only after move
    └── _meta/          # audit outputs (orphans, stale, conflicts)
```

See [`SKILL.md`](./.claude/skills/project-wiki/SKILL.md) for the full specification: card format, link conventions, workflow steps, splitting rules, and operating principles.

## Examples

[`.claude/skills/project-wiki/examples/wiki/`](./.claude/skills/project-wiki/examples/wiki/) contains a small sample wiki with a `_root.md` and three cards demonstrating the format, link style, and a hub pattern.
