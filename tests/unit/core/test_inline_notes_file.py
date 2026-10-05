"""Notes written into the file: the form, the escaping, and the round trip."""

from __future__ import annotations

import pytest

from quill.core.browser_preview import render_preview_body
from quill.core.inline_notes_file import (
    escape_note_text,
    format_note_comment,
    insert_file_note,
    mark_notes_for_render,
    parse_file_notes,
    remove_all_file_notes,
    remove_file_note,
    replace_file_note,
    unescape_note_text,
)

DOC = (
    "# Plan\n\nBack up the uploads folder\nbefore the move.\n\n"
    "- [ ] Write the tests\n- [ ] Ship it\n\n```\ncode\n```\nAfter.\n"
)


def _add(text: str, at: int, note: str, kind: str = "markdown") -> str:
    offset, insertion = insert_file_note(text, at, note, kind)
    return text[:offset] + insertion + text[offset:]


@pytest.mark.parametrize(
    "note",
    ["plain", "a -- b", "ends with -", "-->", "&#45; literal", "a & b", "x--!>y", "---"],
)
def test_any_text_round_trips_and_never_contains_a_double_hyphen(note: str) -> None:
    escaped = escape_note_text(note)
    assert "--" not in escaped and not escaped.endswith("-")
    assert unescape_note_text(escaped) == note
    text = _add(DOC, DOC.index("Back"), note)
    assert [n.text for n in parse_file_notes(text)] == [note]


def test_a_note_goes_after_the_paragraph_it_is_on() -> None:
    text = _add(DOC, DOC.index("Back"), "check")
    assert "before the move.\n<!-- quill-note: check -->\n\n- [ ]" in text
    (note,) = parse_file_notes(text)
    assert note.anchor == "Back up the uploads folder\nbefore the move."


def test_a_note_on_a_list_item_is_indented_into_the_item() -> None:
    text = _add(DOC, DOC.index("Write the"), "first")
    assert "- [ ] Write the tests\n  <!-- quill-note: first -->\n- [ ] Ship it" in text
    assert parse_file_notes(text)[0].anchor == "- [ ] Write the tests"


def test_a_note_on_code_goes_after_the_fence_and_examples_in_code_are_ignored() -> None:
    text = DOC.replace("code\n", "code\n<!-- quill-note: an example, not a note -->\n")
    assert parse_file_notes(text) == []
    text = _add(text, text.index("code"), "real")
    assert "```\n<!-- quill-note: real -->\nAfter." in text
    assert [n.text for n in parse_file_notes(text)] == ["real"]


def test_a_second_note_on_the_same_text_keeps_the_order() -> None:
    text = _add(DOC, DOC.index("Back"), "one")
    text = _add(text, text.index("Back"), "two")
    assert [n.text for n in parse_file_notes(text)] == ["one", "two"]


def test_notes_survive_editing_near_them_and_a_save_and_reopen(tmp_path) -> None:
    text = _add(DOC, DOC.index("Ship"), "careful")
    text = text.replace("Ship it", "Ship it on Friday").replace("# Plan", "# The plan")
    path = tmp_path / "plan.md"
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    reopened = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    (note,) = parse_file_notes(reopened)
    assert note.text == "careful"
    assert note.anchor == "- [ ] Ship it on Friday"


def test_edit_and_remove_leave_the_rest_of_the_document_alone() -> None:
    text = _add(DOC, DOC.index("Back"), "old")
    (note,) = parse_file_notes(text)
    start, end, replacement = replace_file_note(text, note, "new\nlines")
    edited = text[:start] + replacement + text[end:]
    assert [n.text for n in parse_file_notes(edited)] == ["new\nlines"]
    assert remove_file_note(edited, parse_file_notes(edited)[0]) == DOC
    assert remove_all_file_notes(_add(_add(DOC, 0, "a"), 40, "b")) == (DOC, 2)


def test_html_documents_take_notes_after_the_line() -> None:
    page = "<p>One</p>\n<p>Two</p>\n"
    text = _add(page, 3, "on one", "html")
    assert text == "<p>One</p>\n<!-- quill-note: on one -->\n<p>Two</p>\n"
    assert parse_file_notes(text, "html")[0].anchor == "<p>One</p>"


def test_other_tools_see_a_comment_and_a_rendered_page_shows_nothing() -> None:
    text = _add(DOC, DOC.index("Back"), "private review")
    assert format_note_comment("private review") in text
    page = render_preview_body(text, "markdown")
    assert "private review" not in page and "quill-note" not in page
    shown = mark_notes_for_render(text, "markdown", True)
    assert '<aside class="quill-note" aria-label="Note">' in render_preview_body(shown, "markdown")
    assert "private review" in render_preview_body(text, "markdown", notes=True)


def test_a_comment_that_is_not_ours_is_left_alone() -> None:
    text = "Para\n<!-- a comment -->\n<!-- quill-note: ok --> trailing text\n"
    assert parse_file_notes(text) == []
