"""Toggle Task Done's core: which boxes change, and what is said."""

from __future__ import annotations

from quill.core.task_lists import is_task_line, task_item_html, toggle_tasks

DOC = "# Plan\n- [ ] one\n- [x] two\n+ [ ] three\n1. [ ] four\n2) [X] five\n\nNot a task\n"


def _apply(text: str, start: int, end: int) -> tuple[str, str]:
    result = toggle_tasks(text, start, end)
    assert result is not None
    return text[: result.start] + result.text + text[result.end :], result.announcement


def test_every_marker_counts() -> None:
    for line in ("- [ ] a", "* [x] b", "+ [ ] c", "1. [ ] d", "12) [X] e", "    - [ ] nested"):
        assert is_task_line(line), line
    for line in ("- [] a", "- [y] a", "[ ] a", "-[ ] a", "Not a task"):
        assert not is_task_line(line), line


def test_one_line_flips_and_the_list_is_counted() -> None:
    text, said = _apply(DOC, DOC.index("one"), DOC.index("one"))
    assert "- [x] one" in text
    assert said == "Checked: one. 3 of 5 tasks complete."
    text, said = _apply(text, text.index("one"), text.index("one"))
    assert text == DOC
    assert said == "Unchecked: one. 2 of 5 tasks complete."


def test_a_selection_ticks_the_group_unless_all_are_done() -> None:
    text, said = _apply(DOC, 0, len(DOC))
    assert text.count("[ ]") == 0
    assert said == "Checked 3 tasks. 5 of 5 tasks complete."
    text, said = _apply(text, 0, len(text))
    assert text.count("[x]") + text.count("[X]") == 0
    assert said == "Unchecked 5 tasks. 0 of 5 tasks complete."


def test_only_the_boxes_change() -> None:
    result = toggle_tasks(DOC, DOC.index("one"), DOC.index("one"))
    assert result is not None and (result.end - result.start, result.text) == (1, "x")


def test_not_a_task_is_none() -> None:
    assert toggle_tasks(DOC, len(DOC) - 3, len(DOC) - 3) is None


def test_a_task_renders_as_a_labelled_read_only_check_box() -> None:
    html = task_item_html("[x] Write the <em>tests</em>")
    assert html == (
        '<label class="task"><input type="checkbox" disabled checked> '
        "Write the <em>tests</em></label>"
    )
    assert task_item_html("[ ] open").startswith(
        '<label class="task"><input type="checkbox" disabled>'
    )
    assert task_item_html("ordinary item") is None
