#!/usr/bin/env python3
"""Tests for draft_audit.audit_drafts — the FB-closure check on wiki/_drafts/.

Run: python test_draft_audit.py   (exit 0 = all pass)
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draft_audit import audit_drafts  # noqa: E402

REVIEW_TAIL = (
    "\n<!-- ── REVIEW ──\n"
    "  看到 RE: → 那是我對你 FB 的回問\n"
    "  FB✓:/RE✓: → 已處理過的紀錄\n"
    "── -->\n"
)


def write(dir_: Path, name: str, body: str) -> None:
    (dir_ / name).write_text(body, encoding="utf-8")


def run_case(name: str, files: dict[str, str]):
    with tempfile.TemporaryDirectory() as td:
        drafts = Path(td) / "_drafts"
        drafts.mkdir()
        for fn, body in files.items():
            write(drafts, fn, body)
        return audit_drafts(drafts)


def get(reports, filename):
    for r in reports:
        if r.filename == filename:
            return r
    raise AssertionError(f"no report for {filename}")


def test_unanswered_fb_is_flagged():
    """An FB: with text, no FB✓:, no RE: beneath → the silent-leak case."""
    body = (
        "---\nid: foo\n---\n\n## 摘要\nx\n"
        + REVIEW_TAIL
        + "FB: 這張太長了拆兩張\n\n"
        + "- [ ] OK\n"
    )
    reports = run_case("unanswered", {"01-foo.md": body})
    r = get(reports, "01-foo.md")
    assert len(r.unanswered_fb) == 1, r.unanswered_fb
    assert "拆兩張" in r.unanswered_fb[0][1]
    assert r.open_re == []
    print("PASS test_unanswered_fb_is_flagged")


def test_resolved_fb_is_not_flagged():
    """FB✓: (applied, kept as history) is closed — not a leak."""
    body = (
        "---\nid: foo\n---\n\n## 摘要\nx\n"
        + REVIEW_TAIL
        + "FB✓: 這張太長了拆兩張\nFB:\n\n"
        + "- [x] OK\n"
    )
    reports = run_case("resolved", {"01-foo.md": body})
    r = get(reports, "01-foo.md")
    assert r.unanswered_fb == [], r.unanswered_fb
    assert r.open_re == []
    print("PASS test_resolved_fb_is_not_flagged")


def test_fb_with_re_is_not_a_leak_but_open_thread():
    """FB: answered by an RE: → not a silent leak; it's an open thread on the user."""
    body = (
        "---\nid: foo\n---\n\n## 摘要\nx\n"
        + REVIEW_TAIL
        + "FB: 把 A 改成 B\nRE: A 和 B 矛盾，要哪個？\nFB:\n\n"
        + "- [ ] OK\n"
    )
    reports = run_case("thread", {"01-foo.md": body})
    r = get(reports, "01-foo.md")
    assert r.unanswered_fb == [], r.unanswered_fb
    assert len(r.open_re) == 1, r.open_re
    print("PASS test_fb_with_re_is_not_a_leak_but_open_thread")


def test_bare_fb_placeholder_ignored():
    """The pre-seeded empty FB: line is not a note — ignore it."""
    body = (
        "---\nid: foo\n---\n\n## 摘要\nx\n"
        + REVIEW_TAIL
        + "FB:\n\n- [ ] OK\n"
    )
    reports = run_case("bare", {"01-foo.md": body})
    r = get(reports, "01-foo.md")
    assert r.unanswered_fb == []
    assert r.open_re == []
    print("PASS test_bare_fb_placeholder_ignored")


def test_ticked_flag_reported():
    body = (
        "---\nid: foo\n---\n\n## 摘要\nx\n"
        + REVIEW_TAIL
        + "FB:\n\n- [x] OK\n"
    )
    reports = run_case("ticked", {"01-foo.md": body})
    r = get(reports, "01-foo.md")
    assert r.ticked is True
    print("PASS test_ticked_flag_reported")


def main() -> int:
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
