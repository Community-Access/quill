"""Next / Previous Indent Change (quill.core.navigation.indent_change_target)."""

from __future__ import annotations

from quill.core.navigation import describe_indent, indent_change_target

CODE = "def f():\n    a = 1\n    b = 2\n\n    if a:\n        c = 3\n    d = 4\ne = 5\n"


def _line(text: str, offset: int | None) -> str:
    assert offset is not None
    end = text.find("\n", offset)
    return text[offset:end]


def test_forward_skips_lines_at_the_same_depth() -> None:
    caret = CODE.index("a = 1")
    target = indent_change_target(CODE, caret, forward=True)
    # "b = 2" and "if a:" share the depth of "a = 1"; the first change is c.
    assert _line(CODE, target) == "c = 3"


def test_forward_lands_on_the_first_non_blank_character() -> None:
    target = indent_change_target(CODE, 0, forward=True)
    assert target == CODE.index("a = 1")


def test_backward_finds_the_line_the_block_came_from() -> None:
    target = indent_change_target(CODE, CODE.index("c = 3"), forward=False)
    assert _line(CODE, target) == "if a:"


def test_blank_lines_are_skipped_and_a_blank_caret_line_takes_the_nearest() -> None:
    blank = CODE.index("\n\n") + 1
    assert _line(CODE, indent_change_target(CODE, blank, forward=True)) == "if a:"
    assert _line(CODE, indent_change_target(CODE, blank, forward=False)) == "b = 2"


def test_nothing_differs_is_none() -> None:
    assert indent_change_target("a\nb\n\nc\n", 0, forward=True) is None
    assert indent_change_target(CODE, 0, forward=False) is None
    assert indent_change_target("", 0, forward=True) is None


def test_a_tab_and_its_width_in_spaces_are_the_same_depth() -> None:
    text = "\tx\n    y\n        z\n"
    assert _line(text, indent_change_target(text, 0, forward=True, tab_size=4)) == "z"
    assert _line(text, indent_change_target(text, 0, forward=True, tab_size=8)) == "y"


def test_yaml_mapping_levels() -> None:
    text = "root:\n  child: 1\n  other:\n    deep: 2\nnext: 3\n"
    assert _line(text, indent_change_target(text, text.index("child"), forward=True)) == "deep: 2"
    assert _line(text, indent_change_target(text, text.index("deep"), forward=True)) == "next: 3"


def test_describe_indent_says_spaces_tabs_or_none() -> None:
    assert describe_indent("    x", 4) == "4 spaces"
    assert describe_indent("\tx", 1) == "1 tab"
    assert describe_indent("\t  x", 2) == "1 tab and 2 spaces"
    assert describe_indent("x\n y", 3) == "1 space"
    assert describe_indent("x", 0) == "no indent"
