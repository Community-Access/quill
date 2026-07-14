"""PR diff rendering through QUILL's compare engine (wx-free view-model)."""

from __future__ import annotations

from quill.core.github.items_provider import GitHubPullFile
from quill.ui.github_items_view import pull_diff_file_label, render_pull_file_diff


def test_file_label_carries_status_counts_and_rename() -> None:
    label = pull_diff_file_label(
        GitHubPullFile(
            filename="new.py",
            status="renamed",
            additions=3,
            deletions=1,
            previous_filename="old.py",
        )
    )
    assert label == "renamed: new.py (was old.py)  +3 -1"


def test_render_uses_the_compare_engines_spoken_walk() -> None:
    base = "alpha\nbravo\ncharlie\n"
    head = "alpha\nbravo two\ncharlie\ndelta\n"
    out = render_pull_file_diff("notes.md", base, head, base_label="main", head_label="this PR")
    # The Compare Documents voice: numbered differences with locations.
    assert "2 differences" in out
    assert "Difference 1 of 2." in out
    assert "line 2" in out
    # Both sides are labeled the screen-reader-friendly way.
    assert "main: bravo" in out
    assert "this PR: bravo two" in out
    # The word-level change is described, not just dumped.
    assert "changed" in out or "added" in out


def test_added_and_deleted_files_are_stated_plainly() -> None:
    added = render_pull_file_diff("new.py", "", "one\ntwo\n")
    assert "new file with 2 lines" in added
    assert "one" in added  # the content is still readable
    deleted = render_pull_file_diff("gone.py", "a\nb\nc\n", "")
    assert "file deleted (3 lines removed)" in deleted


def test_identical_content_reports_no_differences() -> None:
    out = render_pull_file_diff("same.py", "x\n", "x\n")
    assert "no text differences" in out
