#!/usr/bin/env python3
"""Audit wiki/_drafts/ for FB (feedback) closure.

Deterministic guard for the extract/fleet `go` pass. Its job is to catch the
one failure the prose rules can't guarantee on their own: a user's `FB:` note
that got neither applied (→ `FB✓:`) nor replied to (an `RE:` beneath it), so it
silently sits unanswered and the user can't tell whether Claude saw it.

Marks (all written at the bottom of a draft, one note per line):
  FB:   <text>   an OPEN feedback note the user wrote — needs Claude to either
                 apply it (rename to FB✓:) or reply under it (RE:)
  FB✓:  <text>   Claude addressed it; kept as visible history (closed)
  RE:   <text>   Claude's reply/question, OPEN, awaiting the user's next FB:
  RE✓:  <text>   a resolved RE:, kept as history (closed)
  - [ ] / - [x] OK   approval checkbox

Reports, per draft file:
  unanswered_fb  — OPEN `FB:` with text and no `RE:`/`RE✓:` beneath it → the leak
  open_re        — OPEN `RE:` awaiting the user (informational, not a leak)
  ticked         — whether the OK box is checked

Exit code: 1 if any unanswered FB exists (the invariant the `go` pass must
restore to zero), else 0. Reports go to stdout; nothing is written.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
try:
    import frontmatter as fm  # noqa: E402
except Exception:  # pragma: no cover - lib is optional for --drafts usage
    fm = None

FB_OPEN_RE = re.compile(r"^FB:\s*(.*)$")
FB_DONE_RE = re.compile(r"^FB✓:")   # FB✓:
RE_OPEN_RE = re.compile(r"^RE:\s*(.*)$")
RE_DONE_RE = re.compile(r"^RE✓:")   # RE✓:
CHECKBOX_RE = re.compile(r"^-\s*\[( |x|X)\]")


class DraftReport:
    def __init__(self, filename: str):
        self.filename = filename
        self.unanswered_fb: list[tuple[int, str]] = []   # (lineno, text)
        self.open_re: list[tuple[int, str]] = []          # (lineno, text)
        self.ticked = False

    @property
    def has_leak(self) -> bool:
        return bool(self.unanswered_fb)


def _is_block_boundary(stripped: str) -> bool:
    """A new FB mark or the checkbox ends the current FB's reply span."""
    return bool(
        FB_OPEN_RE.match(stripped)
        or FB_DONE_RE.match(stripped)
        or CHECKBOX_RE.match(stripped)
    )


def audit_draft_text(filename: str, text: str) -> DraftReport:
    r = DraftReport(filename)
    lines = text.splitlines()

    # Strip HTML-comment spans (the REVIEW template's instructions mention the
    # marks in prose; they must not be parsed as real notes).
    in_comment = False
    logical: list[tuple[int, str]] = []  # (1-based lineno, stripped)
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if in_comment:
            if "-->" in s:
                in_comment = False
            continue
        if "<!--" in s and "-->" not in s:
            in_comment = True
            continue
        if "<!--" in s and "-->" in s:
            continue
        logical.append((i, s))

    for idx, (lineno, s) in enumerate(logical):
        if CHECKBOX_RE.match(s):
            r.ticked = r.ticked or s[s.index("[") + 1].lower() == "x"
            continue

        m = FB_OPEN_RE.match(s)
        if m and not FB_DONE_RE.match(s):
            note = m.group(1).strip()
            if not note:
                continue  # bare placeholder FB:
            # Scan the reply span: from the next line until the next block
            # boundary, looking for any RE:/RE✓:.
            answered = False
            for _, s2 in logical[idx + 1:]:
                if _is_block_boundary(s2):
                    break
                if RE_OPEN_RE.match(s2) or RE_DONE_RE.match(s2):
                    answered = True
                    break
            if not answered:
                r.unanswered_fb.append((lineno, note))
            continue

        m = RE_OPEN_RE.match(s)
        if m and not RE_DONE_RE.match(s):
            reply = m.group(1).strip()
            if reply:
                r.open_re.append((lineno, reply))

    return r


def audit_drafts(drafts_dir: Path) -> list[DraftReport]:
    if not drafts_dir.is_dir():
        return []
    out = []
    for p in sorted(drafts_dir.glob("*.md")):
        out.append(audit_draft_text(p.name, p.read_text(encoding="utf-8")))
    return out


def _find_drafts_dir(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    if fm is not None:
        try:
            return fm.find_wiki_root() / "_drafts"
        except Exception:
            return None
    return None


def main() -> int:
    try:  # marks like FB✓: and 「」 must survive a non-UTF-8 console (Windows cp950)
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Audit wiki/_drafts/ for FB closure")
    ap.add_argument("--drafts", type=Path, default=None,
                    help="Path to wiki/_drafts/ (default: auto-locate via wiki root)")
    args = ap.parse_args()

    drafts = _find_drafts_dir(args.drafts)
    if drafts is None or not drafts.is_dir():
        print("No wiki/_drafts/ found — nothing to audit.")
        return 0

    reports = audit_drafts(drafts)
    if not reports:
        print(f"=== Draft FB audit: {drafts} — no drafts ===")
        return 0

    leaks = [r for r in reports if r.has_leak]
    open_threads = [r for r in reports if r.open_re]

    print(f"=== Draft FB audit ({len(reports)} drafts in {drafts}) ===\n")
    print(f"Unanswered FB (must be 0 after `go`): {sum(len(r.unanswered_fb) for r in leaks)}")
    for r in leaks:
        for lineno, note in r.unanswered_fb:
            print(f"   ✗ {r.filename}:{lineno} — 「{note}」  (no FB✓: / no RE:)")

    print(f"\nOpen RE awaiting user: {sum(len(r.open_re) for r in open_threads)}")
    for r in open_threads:
        for lineno, reply in r.open_re:
            print(f"   … {r.filename}:{lineno} — RE: 「{reply}」")

    ticked_open = [r for r in reports if r.ticked and (r.has_leak or r.open_re)]
    if ticked_open:
        print("\nTicked OK but still has an open thread:")
        for r in ticked_open:
            print(f"   ! {r.filename}")

    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
