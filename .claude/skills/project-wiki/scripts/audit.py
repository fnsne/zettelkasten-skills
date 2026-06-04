#!/usr/bin/env python3
"""Audit a project wiki — run 10 deterministic health checks.

Reports go to stdout. Unless --no-write is passed, also writes:
  wiki/_meta/orphans.md
  wiki/_meta/stale.md
  wiki/_meta/conflicts.md
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import frontmatter as fm  # noqa: E402

OVERSIZED_CHAR_THRESHOLD = 2000  # ~500 tokens for mixed CJK/English

INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(\./([^)]+?)\.md\)")
NAV_SECTION_RE = re.compile(r"^##\s+何時往下追\s*$", re.MULTILINE)

# Source-deferral detection (Card splitting Rule 5): card prose must be
# self-contained, not "go read the source". Strong cues are almost always
# deferrals; the weak cue (參考) is only flagged when a source hint sits on the
# same line, to keep false positives down. This is a word match only — the
# "names nothing specific / whole-file pointer" case is left to the Claude-side
# semantic check documented in SKILL.md.
DEFER_STRONG_RE = re.compile(
    r"(詳見|詳閱|詳情請?[見參]|細節請?[見參]|參見|參照|見\s*原始|見\s*source"
    r"|see\s+(?:the\s+)?source|refer\s+to\s+(?:the\s+)?source)",
    re.IGNORECASE,
)
DEFER_WEAK_RE = re.compile(r"請?參考")
SOURCE_HINT_RE = re.compile(
    r"(source|原始檔|原始碼|原文|程式碼|src/|docs/|meetings/|ref/"
    r"|\.tsx?|\.jsx?|\.py|\.go|\.java|\.pdf)",
    re.IGNORECASE,
)

# Vague-source-pointer detection (Card splitting Rule 5): a body "go deeper"
# pointer must name a precise location, not the whole file. This is structural
# (it reads the referenced file's length), so it triggers on neither the noun
# "source" nor any domain wording — only on the shape of the pointer itself.
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
LINE_RANGE_RE = re.compile(r":\s*(\d+)\s*-\s*(\d+)")
LOCATOR_RE = re.compile(
    r":\s*\d+"                                   # :42 or :42-58
    r"|p\.?\s*\d+|pages?\s+\d+"                   # p.4 / p4 / page 4 / pages 4
    r"|第\s*\d+\s*[-–~]?\s*\d*\s*頁",             # 第4頁 / 第4-6頁
    re.IGNORECASE,
)
CODE_EXT = {
    "ts", "tsx", "js", "jsx", "mjs", "cjs", "py", "go", "java", "rb", "rs",
    "c", "cc", "cpp", "h", "hpp", "cs", "php", "kt", "swift", "scala", "sql",
    "sh", "bash", "yaml", "yml", "json", "toml", "ini", "xml", "html", "css",
    "scss", "vue", "svelte",
}
DOC_EXT = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv", "txt"}
SOURCE_DIR_RE = re.compile(r"(^|/)(src|docs|meetings|ref|app|lib|tests?|internal|pkg|cmd)/")
WHOLE_FILE_MIN_LINES = 40   # below this, "whole file" isn't hard to navigate
WHOLE_FILE_RATIO = 0.9      # a range covering >=90% of the file is effectively whole-file


def _path_ext(path: str) -> str:
    base = path.split(":")[0].split("#")[0].strip()
    m = re.search(r"\.([a-z0-9]+)$", base, re.IGNORECASE)
    return m.group(1).lower() if m else ""


def _is_source_path(path: str) -> bool:
    base = path.split(":")[0].split("#")[0].strip()
    if base.endswith(".md"):          # cards / _root / ref notes are not line-addressable sources
        return False
    ext = _path_ext(base)
    return ext in CODE_EXT or ext in DOC_EXT or bool(SOURCE_DIR_RE.search(base))


def _line_count(fpath: Path) -> int | None:
    try:
        with fpath.open("r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return None


def _is_whole_file(text: str, fpath: Path) -> bool:
    m = LINE_RANGE_RE.search(text)
    if not m or _path_ext(str(fpath)) in DOC_EXT or not fpath.exists():
        return False
    total = _line_count(fpath)
    if not total or total < WHOLE_FILE_MIN_LINES:
        return False
    covered = int(m.group(2)) - int(m.group(1)) + 1
    return covered >= total * WHOLE_FILE_RATIO


def check_vague_source_pointers(cards, wiki_root: Path):
    """Body source pointers that point at a whole file or carry no locator.

    Catches the Rule-5 failure that the word check (check 9) can't see: a
    "go deeper" pointer whose line range spans (almost) the entire file, or a
    link to a source file with no line/page locator at all. Reads the target
    file to judge whole-file coverage, so it never fires on the word "source".
    """
    project_root = wiki_root.parent
    cards_dir = wiki_root / "cards"
    out = []
    seen = set()

    def add(cid, lineno, kind, snippet):
        key = (cid, lineno, kind)
        if key not in seen:
            seen.add(key)
            out.append((cid, lineno, kind, snippet))

    for c in cards:
        for i, raw in enumerate(c.body.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            snippet = line if len(line) <= 60 else line[:57] + "..."

            # Markdown links to a source file are deliberate pointers; by skill
            # convention the line/page locator lives in the link TEXT.
            for m in MD_LINK_RE.finditer(line):
                text, href = m.group(1), m.group(2).split("#")[0].strip()
                if not _is_source_path(href):
                    continue
                fpath = (cards_dir / href).resolve()
                # Located if the line/page sits in the link text OR right next to
                # it on the same line — either way the reader can find the spot.
                if not LOCATOR_RE.search(text) and not LOCATOR_RE.search(line):
                    add(c.id, i, "no-locator", snippet)
                elif _is_whole_file(text, fpath):
                    add(c.id, i, "whole-file", snippet)

            # Backtick paths: flag whole-file ranges always; flag a locator-less
            # path only when the line is a nav pointer (has the → arrow), so
            # casual inline mentions like `config/app.yaml` are left alone.
            for m in BACKTICK_RE.finditer(line):
                span = m.group(1).strip()
                if not _is_source_path(span):
                    continue
                fpath = (project_root / span.split(":")[0].strip()).resolve()
                if LOCATOR_RE.search(span):
                    if _is_whole_file(span, fpath):
                        add(c.id, i, "whole-file", snippet)
                elif "→" in line:
                    add(c.id, i, "no-locator", snippet)
    return out


def inline_targets(body: str) -> set[str]:
    return {m.group(2) for m in INLINE_LINK_RE.finditer(body)}


def check_orphans(cards):
    inbound: dict[str, set[str]] = {c.id: set() for c in cards}
    for c in cards:
        for target in c.frontmatter.get("links") or []:
            if target in inbound:
                inbound[target].add(c.id)
    return [cid for cid, refs in inbound.items() if not refs]


def check_inline_orphans(cards):
    inline_seen: dict[str, set[str]] = {c.id: set() for c in cards}
    fm_seen: dict[str, bool] = {c.id: False for c in cards}
    for c in cards:
        for t in inline_targets(c.body):
            if t in inline_seen:
                inline_seen[t].add(c.id)
        for t in c.frontmatter.get("links") or []:
            if t in fm_seen:
                fm_seen[t] = True
    return [cid for cid, in_fm in fm_seen.items() if in_fm and not inline_seen[cid]]


def check_dead_ends(cards):
    out = []
    for c in cards:
        has_links = bool(c.frontmatter.get("links")) or bool(inline_targets(c.body))
        has_nav = bool(NAV_SECTION_RE.search(c.body))
        if not has_links and not has_nav:
            out.append(c.id)
    return out


def _as_date(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError:
            return None
    return None


def check_stale(cards, project_root: Path):
    out = []
    for c in cards:
        updated = _as_date(c.frontmatter.get("updated"))
        if not updated:
            continue
        for src in c.frontmatter.get("sources") or []:
            sp = project_root / src.get("path", "")
            if not sp.exists():
                continue
            src_date = datetime.fromtimestamp(sp.stat().st_mtime).date()
            if src_date > updated:
                out.append((c.id, str(src.get("path")), src_date.isoformat()))
    return out


def check_oversized(cards):
    return [(c.id, len(c.body)) for c in cards if len(c.body) > OVERSIZED_CHAR_THRESHOLD]


def check_broken_links(cards):
    valid = {c.id for c in cards}
    out = []
    for c in cards:
        for t in c.frontmatter.get("links") or []:
            if t not in valid:
                out.append((c.id, f"frontmatter.links → {t}"))
        for t in inline_targets(c.body):
            if t not in valid:
                out.append((c.id, f"inline link → {t}.md"))
    return out


def check_conflicts(cards):
    cmap: dict[str, set[str]] = {
        c.id: set(c.frontmatter.get("conflicts") or []) for c in cards
    }
    single_sided = []
    valid_pairs: set[tuple[str, str]] = set()
    for a, partners in cmap.items():
        for b in partners:
            if b not in cmap:
                single_sided.append((a, f"references missing card '{b}'"))
            elif a not in cmap[b]:
                single_sided.append((a, f"'{b}' does not list '{a}' back"))
            else:
                valid_pairs.add(tuple(sorted([a, b])))
    return single_sided, sorted(valid_pairs)


def check_source_deferral(cards):
    """Card prose that defers substance to a source instead of stating it.

    Flags lines using a strong deferral cue (詳見/參見/參照/see source…), or the
    weak cue 參考 when a source hint is on the same line. Skips headings, the
    sources/links frontmatter is not in body so not scanned.
    """
    out = []
    for c in cards:
        for i, raw in enumerate(c.body.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            hit = None
            if DEFER_STRONG_RE.search(line):
                hit = DEFER_STRONG_RE.search(line).group(0)
            elif DEFER_WEAK_RE.search(line) and SOURCE_HINT_RE.search(line):
                hit = DEFER_WEAK_RE.search(line).group(0)
            if hit:
                snippet = line if len(line) <= 60 else line[:57] + "..."
                out.append((c.id, i, hit, snippet))
    return out


def check_inbox(wiki_root: Path):
    inbox = wiki_root / "_inbox"
    if not inbox.is_dir():
        return []
    now = time.time()
    out = []
    for p in sorted(inbox.glob("*.md")):
        age = int((now - p.stat().st_mtime) / 86400)
        out.append((p.name, age))
    return out


def write_orphans_md(wiki_root: Path, items):
    target = wiki_root / "_meta" / "orphans.md"
    target.parent.mkdir(exist_ok=True)
    lines = ["# Orphan cards", "", f"Updated: {date.today().isoformat()}", "",
             "Cards with zero inbound `frontmatter.links` references.", ""]
    lines += [f"- {c}" for c in items] if items else ["_(none)_"]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stale_md(wiki_root: Path, items):
    target = wiki_root / "_meta" / "stale.md"
    target.parent.mkdir(exist_ok=True)
    lines = ["# Stale cards", "", f"Updated: {date.today().isoformat()}", "",
             "Cards whose source files have changed since the card was last `updated:`.", ""]
    if items:
        lines += [f"- `{cid}` — source `{src}` modified {d}" for cid, src, d in items]
    else:
        lines += ["_(none)_"]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_conflicts_md(wiki_root: Path, valid_pairs):
    """Sync _meta/conflicts.md from current frontmatter, preserving descriptions."""
    target = wiki_root / "_meta" / "conflicts.md"
    target.parent.mkdir(exist_ok=True)

    existing: dict[tuple[str, str], str] = {}
    if target.exists():
        for line in target.read_text(encoding="utf-8").splitlines():
            m = re.match(r"-\s+`([^`]+)`\s+↔\s+`([^`]+)`\s*(?:—\s*(.+))?", line)
            if m:
                a, b, desc = m.group(1), m.group(2), (m.group(3) or "").strip()
                existing[tuple(sorted([a, b]))] = desc

    lines = ["# Conflicts", "", f"Updated: {date.today().isoformat()}", "",
             "Pairs of cards with opposing claims. Edit the description after `—` to summarise the disagreement.", ""]
    if valid_pairs:
        for pair in valid_pairs:
            desc = existing.get(pair, "(describe the disagreement)")
            lines.append(f"- `{pair[0]}` ↔ `{pair[1]}` — {desc}")
    else:
        lines += ["_(none)_"]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _section(num: int, title: str, items, render):
    print(f"\n{num}. {title} ({len(items)})")
    if not items:
        print("   (none)")
        return
    for it in items:
        print(f"   - {render(it)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a project wiki")
    ap.add_argument("--wiki", type=Path, default=None, help="Path to wiki/ root")
    ap.add_argument("--no-write", action="store_true", help="Skip writing _meta/*.md reports")
    args = ap.parse_args()

    wiki_root = args.wiki.resolve() if args.wiki else fm.find_wiki_root()
    project_root = wiki_root.parent
    cards = fm.list_cards(wiki_root)

    if not cards:
        print(f"No cards found in {wiki_root}/cards/", file=sys.stderr)
        return 1

    print(f"=== Wiki audit ({len(cards)} cards in {wiki_root}) ===")

    orphans = check_orphans(cards)
    inline_orphans = check_inline_orphans(cards)
    dead_ends = check_dead_ends(cards)
    stale = check_stale(cards, project_root)
    oversized = check_oversized(cards)
    broken = check_broken_links(cards)
    single_sided, valid_pairs = check_conflicts(cards)
    inbox = check_inbox(wiki_root)
    deferrals = check_source_deferral(cards)
    vague_ptrs = check_vague_source_pointers(cards, wiki_root)

    _section(1, "Orphans", orphans, lambda x: x)
    _section(2, "Inline-orphan (in frontmatter.links but never as inline link)",
             inline_orphans, lambda x: x)
    _section(3, "Dead-end cards (no outbound links, no 何時往下追)",
             dead_ends, lambda x: x)
    _section(4, "Stale (source mtime > card updated)",
             stale, lambda t: f"{t[0]} — source {t[1]} modified {t[2]}")
    _section(5, f"Oversized cards (body > {OVERSIZED_CHAR_THRESHOLD} chars)",
             oversized, lambda t: f"{t[0]} ({t[1]} chars)")
    _section(6, "Broken links", broken, lambda t: f"{t[0]}: {t[1]}")
    _section(7, "Single-sided conflicts", single_sided, lambda t: f"{t[0]}: {t[1]}")
    _section(8, "Inbox pending", inbox, lambda t: f"{t[0]} ({t[1]} days old)")
    _section(9, "Source-deferral prose (Rule 5: state the substance, don't say 詳見/參考 source)",
             deferrals, lambda t: f"{t[0]} line {t[1]} — 「{t[2]}」: {t[3]}")
    _section(10, "Vague source pointers (Rule 5: name a precise location, not the whole file)",
             vague_ptrs, lambda t: f"{t[0]} line {t[1]} — {t[2]}: {t[3]}")

    if not args.no_write:
        write_orphans_md(wiki_root, orphans)
        write_stale_md(wiki_root, stale)
        write_conflicts_md(wiki_root, valid_pairs)
        print(f"\nReports written to {wiki_root}/_meta/{{orphans,stale,conflicts}}.md")

    total_issues = (len(orphans) + len(inline_orphans) + len(dead_ends) + len(stale)
                    + len(oversized) + len(broken) + len(single_sided) + len(deferrals)
                    + len(vague_ptrs))
    return 1 if total_issues else 0


if __name__ == "__main__":
    sys.exit(main())
