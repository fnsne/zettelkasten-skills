#!/usr/bin/env python3
"""Move a processed inbox file from wiki/_inbox/ to wiki/ref/.

After extraction, run this with the inbox file path. The script:
  1. Moves the file to wiki/ref/<same-name>.md
  2. Scans all cards in wiki/cards/ and rewrites any `sources:` paths
     that pointed at the old _inbox location to the new ref/ location.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import frontmatter as fm  # noqa: E402


def update_sources(card: fm.Card, old_rel: str, new_rel: str) -> bool:
    """Rewrite `sources[*].path` entries matching old_rel. Returns True if changed."""
    sources = card.frontmatter.get("sources")
    if not isinstance(sources, list):
        return False
    changed = False
    for src in sources:
        if isinstance(src, dict) and src.get("path") == old_rel:
            src["path"] = new_rel
            changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote an inbox file to ref/ (read-only source)")
    ap.add_argument("inbox_file", type=Path,
                    help="Path to the inbox file (e.g. wiki/_inbox/2026-05-22-jwt-想法.md)")
    ap.add_argument("--wiki", type=Path, default=None, help="Path to wiki/ root")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = ap.parse_args()

    inbox_path = args.inbox_file.resolve()
    if not inbox_path.exists():
        print(f"ERROR: file not found: {inbox_path}", file=sys.stderr)
        return 1

    wiki_root = args.wiki.resolve() if args.wiki else fm.find_wiki_root()
    project_root = wiki_root.parent

    inbox_dir = wiki_root / "_inbox"
    if inbox_dir not in inbox_path.parents:
        print(f"ERROR: {inbox_path} is not inside {inbox_dir}", file=sys.stderr)
        return 1

    ref_dir = wiki_root / "ref"
    new_path = ref_dir / inbox_path.name
    if new_path.exists():
        print(f"ERROR: destination already exists: {new_path}", file=sys.stderr)
        return 1

    old_rel = str(inbox_path.relative_to(project_root)).replace("\\", "/")
    new_rel = str(new_path.relative_to(project_root)).replace("\\", "/")

    affected: list[fm.Card] = []
    for card in fm.list_cards(wiki_root):
        if update_sources(card, old_rel, new_rel):
            affected.append(card)

    print(f"Move: {old_rel}  →  {new_rel}")
    print(f"Cards with `sources:` updated: {len(affected)}")
    for c in affected:
        print(f"  - {c.id}")

    if args.dry_run:
        print("\n(dry-run; no files written)")
        return 0

    ref_dir.mkdir(exist_ok=True)
    inbox_path.rename(new_path)
    for c in affected:
        fm.write_card(c)

    return 0


if __name__ == "__main__":
    sys.exit(main())
