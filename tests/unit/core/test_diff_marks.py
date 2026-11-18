"""Kelly Ford's four ways of marking a diff line (quill.core.diff_marks)."""

from __future__ import annotations

import pytest

from quill.core import diff_marks as d

PATCH = """diff --git a/src/app.py b/src/app.py
index 1..2 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,4 +10,4 @@ def main():
 keep
-old one
-old two
+new one
+new two

\\ No newline at end of file
"""


def test_the_four_styles_and_their_labels() -> None:
    assert d.STYLES == ("words", "short", "symbols", "changed")
    assert set(d.LABELS) == set(d.STYLES)
    assert d.LABELS["changed"] == "Diff symbols with changed lines (!-, !+, +, -, =)"
    assert d.is_symbol_style("symbols") and d.is_symbol_style("changed")
    assert not d.is_symbol_style("short")
    assert d.style_or_default("nonsense") == "words"


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("words", ["Unchanged: a", "Removed: b", "Added: B", "Unchanged: blank line"]),
        ("short", ["Same a", "Del b", "Add B", "Same blank line"]),
        ("symbols", ["= a", "- b", "+ B", "= blank line"]),
        ("changed", ["= a", "!- b", "!+ B", "= blank line"]),
    ],
)
def test_each_style_marks_first(style: str, expected: list[str]) -> None:
    assert d.render_lines([" a", "-b", "+B", " "], style) == expected


def test_changed_style_pairs_runs_and_keeps_leftovers() -> None:
    out = d.render_lines(["-o1", "-o2", "-o3", "+n1", "+n2"], "changed")
    assert out == ["!- o1", "!+ n1", "!- o2", "!+ n2", "- o3"]
    lonely = d.render_lines(["+only"], "changed")
    assert lonely == ["+ only"]


def test_a_note_stays_after_its_line() -> None:
    out = d.render_lines(["-x", "\\ No newline at end of file", "+y"], "changed")
    assert out == ["!- x", "Note: No newline at end of file", "!+ y"]


def test_parse_and_where() -> None:
    hunks = d.parse_unified(PATCH)
    assert len(hunks) == 1
    assert (hunks[0].added, hunks[0].removed) == (2, 2)
    assert d.where(hunks[0]) == "Lines 10 to 13:"
    assert d.where(d.Hunk(5, 5, ["+x"])) == "At line 5:"
    assert d.where(d.Hunk(0, 0, ["+x"])) == "A change:"


def test_a_removed_line_starting_with_dashes_is_still_removed() -> None:
    hunks = d.parse_unified("@@ -1,1 +1,1 @@\n--- not a header\n+++ nor this\n")
    assert hunks[0].lines == ["--- not a header", "+++ nor this"]


def test_render_unified_summarises_each_file() -> None:
    out = d.render_unified(PATCH, "short")
    assert out.startswith("src/app.py: modified, 2 lines added, 2 removed.")
    assert "Lines 10 to 13:" in out
    assert "Del old one" in out and "Add new two" in out
    assert d.render_unified("", "words") == "No differences."


def test_render_texts_names_both_sides() -> None:
    out = d.render_texts("a\nb\n", "a\nc\n", "theirs", "mine", style="words")
    assert out.splitlines()[0] == "Comparing mine with theirs: 1 line added, 1 removed, in 1 place."
    assert "Removed: b" in out and "Added: c" in out
    assert d.render_texts("same", "same", "x", "y") == "y and x are the same."


def test_render_replacement_pairs_old_with_new() -> None:
    assert d.render_replacement(["b"], ["B"], "changed") == ["!- b", "!+ B"]


def test_the_mit_notice_and_credit_travel_with_the_code() -> None:
    doc = d.__doc__ or ""
    assert "Kelly Ford" in doc
    assert "MIT License" in doc
    assert "Permission is hereby granted" in doc
