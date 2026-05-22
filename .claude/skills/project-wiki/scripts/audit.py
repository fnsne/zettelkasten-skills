#!/usr/bin/env python3
"""Audit a project wiki — run 8 deterministic health checks.

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

    if not args.no_write:
        write_orphans_md(wiki_root, orphans)
        write_stale_md(wiki_root, stale)
        write_conflicts_md(wiki_root, valid_pairs)
        print(f"\nReports written to {wiki_root}/_meta/{{orphans,stale,conflicts}}.md")

    total_issues = (len(orphans) + len(inline_orphans) + len(dead_ends) + len(stale)
                    + len(oversized) + len(broken) + len(single_sided))
    return 1 if total_issues else 0


if __name__ == "__main__":
    sys.exit(main())
