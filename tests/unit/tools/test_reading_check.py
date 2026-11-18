"""The guides' reading grade and tutorials' promised time (EdSharp's checks)."""

from __future__ import annotations

from quill.tools import reading_check


def test_the_live_tree_passes() -> None:
    assert reading_check.problems() == []


def test_plain_words_grade_lower_than_long_ones() -> None:
    plain = "Open the file. Read the line. Save it now. " * 10
    hard = (
        "Consequently, institutional accessibility considerations necessitate "
        "comprehensive organizational documentation methodologies. " * 10
    )
    assert reading_check.grade(plain) < 5 < reading_check.grade(hard)
    assert reading_check.grade("Too short.") == 0.0


def test_code_tables_and_keys_are_not_prose() -> None:
    markdown = (
        "# Title\n\n| a | b |\n\n```\nlong_identifier_names()\n```\n\n"
        "Press `Ctrl+Alt+Shift+F1` now."
    )
    assert reading_check._prose(markdown) == "Press   now."


def test_a_new_hard_chapter_or_long_tutorial_fails(monkeypatch) -> None:
    monkeypatch.setattr(reading_check, "chapter_grades", lambda: {"docs/new.md": 11.0})
    monkeypatch.setattr(reading_check, "tutorial_minutes", lambda: {"quill:x": (4, 9.0)})
    found = reading_check.problems({"chapters_over_target": {}, "tutorials_over_time": {}})
    assert found == [
        "docs/new.md: reading grade 11.0, over the target of 9.0.",
        "quill:x: about 9.0 minutes to do, but it promises 4.",
    ]
    listed = {
        "chapters_over_target": {"docs/new.md": 10.4},
        "tutorials_over_time": {"quill:x": 9.0},
    }
    assert reading_check.problems(listed) == [
        "docs/new.md: reading grade 11.0, harder than its 10.4."
    ]
