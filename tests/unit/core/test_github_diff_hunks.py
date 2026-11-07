"""Exact file-line targets in GitHub's unified PR patch."""

from quill.core.github.diff_hunks import find_line, parse_hunks

PATCH = """@@ -10,3 +10,4 @@ section
 old context
-removed
+added
 unchanged
+last
@@ -30,1 +31,1 @@ second
-old
+new
"""


def test_hunk_line_navigation_uses_file_lines_and_side() -> None:
    hunks = parse_hunks(PATCH)
    assert len(hunks) == 2
    right = find_line(PATCH, 11)
    assert right is not None
    assert right[0][right[1] :].startswith("Added, line 11: added")
    left = find_line(PATCH, 11, side="LEFT")
    assert left is not None
    assert left[0][left[1] :].startswith("Removed, old line 11: removed")
    assert find_line(PATCH, 31)[0].startswith("Hunk: old line 30, new line 31")
    assert find_line(PATCH, 99) is None


def test_malformed_or_missing_patch_never_guesses_a_line() -> None:
    assert find_line("binary content", 12) is None
    assert find_line(PATCH, 0) is None
