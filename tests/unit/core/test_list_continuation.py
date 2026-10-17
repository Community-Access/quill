"""Enter in a list: both markers, depth, splits, the exit, renumbering, and when.

The rules both editors run (quill/core/list_continuation.py). The editors'
own Enter paths are tested in tests/unit/ui/test_main_frame_typing_assist.py
and tests/unit/apps/test_lite_typing_assist.py; this file is the behaviour.
"""

from __future__ import annotations

import pytest

from quill.core.format_ops import continue_markdown_list as reexported
from quill.core.list_continuation import (
    MarkdownListContinuation,
    continuation_message,
    continue_markdown_list,
    list_continuation_allowed,
)


def _enter(text: str, caret: int | None = None) -> MarkdownListContinuation:
    result = continue_markdown_list(text, len(text) if caret is None else caret)
    assert result is not None
    return result


def test_format_ops_still_exports_the_same_function() -> None:
    assert reexported is continue_markdown_list


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("1. first", "1. first\n2. "),
        ("1) first", "1) first\n2) "),
        ("9. ninth", "9. ninth\n10. "),
        ("- item", "- item\n- "),
        ("* item", "* item\n* "),
        ("+ item", "+ item\n+ "),
        ("- [x] done", "- [x] done\n- [ ] "),
        ("3. [ ] task", "3. [ ] task\n4. [ ] "),
    ],
)
def test_the_next_marker_follows_the_kind_of_list(line: str, expected: str) -> None:
    result = _enter(line)
    assert result.text == expected
    assert result.caret == len(expected)
    assert result.exited_list is False


def test_indentation_is_kept_so_a_nested_item_continues_at_its_own_depth() -> None:
    text = "1. outer\n    1) inner"
    result = _enter(text)
    assert result.text == "1. outer\n    1) inner\n    2) "


def test_enter_in_the_middle_of_an_item_splits_it_and_drops_the_spaces() -> None:
    text = "1. bread and milk"
    caret = text.index(" and")
    result = _enter(text, caret)
    assert result.text == "1. bread\n2. and milk"
    assert result.caret == len("1. bread\n2. ")


def test_an_empty_item_ends_the_list_and_keeps_its_line() -> None:
    """The line's newline used to go with the marker, joining the next line on."""
    text = "1. one\n2. \nAfter"
    result = _enter(text, text.index("\nAfter"))
    assert result.exited_list is True
    assert result.text == "1. one\n\nAfter"
    assert result.caret == len("1. one\n")


def test_an_empty_nested_item_keeps_its_indentation() -> None:
    result = _enter("- a\n    - ")
    assert result.text == "- a\n    "
    assert result.exited_list is True


def test_a_new_numbered_item_renumbers_the_ones_below() -> None:
    text = "1. a\n2. b\n3. c"
    result = _enter(text, len("1. a"))
    assert result.text == "1. a\n2. \n3. b\n4. c"
    assert result.renumbered == 2
    assert continuation_message(result) == "Continued list item, renumbered 2 items below"


def test_renumbering_passes_over_nested_lines_and_stops_at_numbering_of_your_own() -> None:
    text = "1. a\n2. b\n    - detail\n3. c\n7. seven"
    result = _enter(text, len("1. a"))
    assert result.text == "1. a\n2. \n3. b\n    - detail\n4. c\n7. seven"
    assert result.renumbered == 2


def test_renumbering_stops_at_a_blank_line_and_ignores_the_other_separator() -> None:
    text = "1. a\n2) b"
    assert _enter(text, len("1. a")).text == "1. a\n2. \n2) b"
    text = "1. a\n\n2. b"
    assert _enter(text, len("1. a")).text == "1. a\n2. \n\n2. b"


def test_a_caret_inside_the_marker_leaves_enter_alone() -> None:
    assert continue_markdown_list("12. item", 1) is None


def test_a_line_that_is_not_a_list_leaves_enter_alone() -> None:
    assert continue_markdown_list("Dear Sam,", 9) is None
    assert continue_markdown_list("1.5 litres", 10) is None


def test_the_messages_both_editors_speak() -> None:
    assert continuation_message(_enter("- a")) == "Continued list item"
    assert continuation_message(_enter("- ")) == "Exited list"
    one = _enter("1. a\n2. b", len("1. a"))
    assert continuation_message(one) == "Continued list item, renumbered 1 item below"


# -- when ------------------------------------------------------------------ #


def test_markdown_always_continues() -> None:
    assert list_continuation_allowed("markdown", "notes.md", rich=False, plain_text_enabled=False)


def test_plain_text_only_with_the_setting() -> None:
    assert not list_continuation_allowed("plain", "notes.txt", rich=False, plain_text_enabled=False)
    assert list_continuation_allowed("plain", "notes.txt", rich=False, plain_text_enabled=True)
    assert list_continuation_allowed("plain", None, rich=False, plain_text_enabled=True)


@pytest.mark.parametrize("name", ["setup.py", "config.json", "app.ini", "data.csv", "x.yaml"])
def test_never_in_code_or_configuration_whatever_the_setting(name: str) -> None:
    assert not list_continuation_allowed("plain", name, rich=False, plain_text_enabled=True)


def test_never_in_rich_text_or_html() -> None:
    assert not list_continuation_allowed("markdown", "a.md", rich=True, plain_text_enabled=True)
    assert not list_continuation_allowed("plain", "a.rtf", rich=True, plain_text_enabled=True)
    assert not list_continuation_allowed("html", "a.html", rich=False, plain_text_enabled=True)
    assert not list_continuation_allowed("yaml", "a.yml", rich=False, plain_text_enabled=True)
