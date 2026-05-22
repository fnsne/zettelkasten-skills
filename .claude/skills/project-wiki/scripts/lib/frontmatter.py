"""Shared helpers for parsing markdown cards with YAML frontmatter."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: This script requires PyYAML.\n"
        "  Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)


_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


@dataclass
class Card:
    path: Path
    frontmatter: dict = field(default_factory=dict)
    body: str = ""

    @property
    def id(self) -> str:
        return self.frontmatter.get("id") or self.path.stem


def parse_card(path: Path) -> Card:
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return Card(path=path, frontmatter={}, body=text)
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"WARN: YAML parse failed for {path}: {e}", file=sys.stderr)
        fm = {}
    return Card(path=path, frontmatter=fm, body=m.group(2))


def write_card(card: Card) -> None:
    fm_text = yaml.safe_dump(
        card.frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()
    card.path.write_text(
        f"---\n{fm_text}\n---\n{card.body}",
        encoding="utf-8",
    )


def list_cards(wiki_root: Path) -> list[Card]:
    cards_dir = wiki_root / "cards"
    if not cards_dir.is_dir():
        return []
    return [parse_card(p) for p in sorted(cards_dir.glob("*.md"))]


def find_wiki_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) looking for a `wiki/` directory."""
    p = (start or Path.cwd()).resolve()
    while True:
        candidate = p / "wiki"
        if candidate.is_dir():
            return candidate
        if p == p.parent:
            break
        p = p.parent
    print(
        "ERROR: Could not find a `wiki/` directory by walking up from cwd.\n"
        "  Pass --wiki <path> explicitly, or run from inside a project.",
        file=sys.stderr,
    )
    sys.exit(1)
