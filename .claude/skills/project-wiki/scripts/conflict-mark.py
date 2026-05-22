#!/usr/bin/env python3
"""Mark a bidirectional conflict between two cards.

Adds each card's id to the other's `conflicts:` frontmatter (idempotent),
and appends the pair to wiki/_meta/conflicts.md with a description.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import frontmatter as fm  # noqa: E402


def add_conflict(card: fm.Card, other_id: str) -> bool:
    """Add other_id to card.conflicts. Returns True if changed."""
    existing = list(card.frontmatter.get("conflicts") or [])
    if other_id in existing:
        return False
    existing.append(other_id)
    existing.sort()
    card.frontmatter["conflicts"] = existing
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Mark a bidirectional conflict between two cards")
    ap.add_argument("card_a", help="First card id (e.g. auth-jwt-flow)")
    ap.add_argument("card_b", help="Second card id (e.g. decision-jwt-vs-session)")
    ap.add_argument("--description", "-d", default="(describe the disagreement)",
                    help="One-line summary of the disagreement, recorded in _meta/conflicts.md")
    ap.add_argument("--wiki", type=Path, default=None, help="Path to wiki/ root")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = ap.parse_args()

    if args.card_a == args.card_b:
        print("ERROR: a card cannot conflict with itself", file=sys.stderr)
        return 2

    wiki_root = args.wiki.resolve() if args.wiki else fm.find_wiki_root()
    cards_dir = wiki_root / "cards"

    path_a = cards_dir / f"{args.card_a}.md"
    path_b = cards_dir / f"{args.card_b}.md"
    for p in (path_a, path_b):
        if not p.exists():
            print(f"ERROR: card not found: {p}", file=sys.stderr)
            return 1

    card_a = fm.parse_card(path_a)
    card_b = fm.parse_card(path_b)

    changed_a = add_conflict(card_a, args.card_b)
    changed_b = add_conflict(card_b, args.card_a)

    pair = tuple(sorted([args.card_a, args.card_b]))
    meta_path = wiki_root / "_meta" / "conflicts.md"
    new_line = f"- `{pair[0]}` ↔ `{pair[1]}` — {args.description}"

    meta_changed = False
    meta_content = ""
    if meta_path.exists():
        meta_content = meta_path.read_text(encoding="utf-8")
        already_listed = any(
            line.strip().startswith(f"- `{pair[0]}` ↔ `{pair[1]}`")
            or line.strip().startswith(f"- `{pair[1]}` ↔ `{pair[0]}`")
            for line in meta_content.splitlines()
        )
        if not already_listed:
            meta_content = meta_content.rstrip() + "\n" + new_line + "\n"
            meta_changed = True
    else:
        meta_content = (
            f"# Conflicts\n\nUpdated: {date.today().isoformat()}\n\n"
            "Pairs of cards with opposing claims. Edit the description after `—` to summarise the disagreement.\n\n"
            + new_line + "\n"
        )
        meta_changed = True

    print(f"card_a ({args.card_a}): {'updated conflicts:' if changed_a else 'already lists'} {args.card_b}")
    print(f"card_b ({args.card_b}): {'updated conflicts:' if changed_b else 'already lists'} {args.card_a}")
    print(f"_meta/conflicts.md: {'appended' if meta_changed else 'pair already listed'}")

    if args.dry_run:
        print("\n(dry-run; no files written)")
        return 0

    if changed_a:
        fm.write_card(card_a)
    if changed_b:
        fm.write_card(card_b)
    if meta_changed:
        meta_path.parent.mkdir(exist_ok=True)
        meta_path.write_text(meta_content, encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
