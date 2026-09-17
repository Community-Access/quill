"""The QUILL capabilities QuillLite was missing, and had promised.

Each of these is a "Tier 1" row in bad.md 4.2 -- a thing the small editor
already claimed to be able to do, or already had every part of except the one
that joins them up. A link in a Markdown document, a numbered list, a comment in
a `.py`: none of them is a big feature, and every one of them is the reason
somebody goes and opens a different editor.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Insert Link (Ctrl+K)
# --------------------------------------------------------------------------- #


def test_a_link_in_markdown_is_markdown(lite_window, lite_dialogs) -> None:
    win = lite_window("see here\n", cursor=4, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.control.SetSelection(4, 8)
    lite_dialogs.answer("ask_link", ("here", "https://example.org"))
    win.cmd_insert_link()
    assert win.control.GetValue() == "see [here](https://example.org)\n"
    assert win.announcements[-1] == "Inserted link to https://example.org"


def test_a_link_in_html_is_html(lite_window, lite_dialogs) -> None:
    win = lite_window("<p>see here</p>\n", cursor=7, mode="plain")
    win.set_document_language("html", announce=False)
    win.control.SetSelection(7, 11)
    lite_dialogs.answer("ask_link", ("here", "https://example.org"))
    win.cmd_insert_link()
    assert '<a href="https://example.org">here</a>' in win.control.GetValue()


def test_the_selection_is_offered_as_the_display_text(lite_window, lite_dialogs) -> None:
    """The commonest way to make a link is to select the words first, and a box
    that arrives already holding them saves retyping something the reader would
    then have to check."""
    win = lite_window("see here\n", cursor=4, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.control.SetSelection(4, 8)
    lite_dialogs.answer("ask_link", ("here", "https://example.org"))
    win.cmd_insert_link()
    assert lite_dialogs.kwargs_for("ask_link")["text"] == "here"


def test_cancelling_the_link_inserts_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("see here\n", cursor=4, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.cmd_insert_link()
    assert win.control.GetValue() == "see here\n"


def test_an_address_left_at_the_placeholder_inserts_nothing(lite_window, lite_dialogs) -> None:
    """OK on an untouched dialog is a cancel somebody pressed the wrong key for,
    and a bare `https://` in the document is not what they meant."""
    win = lite_window("see here\n", cursor=4, mode="plain")
    win.set_document_language("markdown", announce=False)
    lite_dialogs.answer("ask_link", ("here", "https://"))
    win.cmd_insert_link()
    assert win.control.GetValue() == "see here\n"
    assert "nothing was inserted" in win.announcements[-1]


def test_a_link_in_a_plain_document_says_what_to_do(lite_window, lite_dialogs) -> None:
    win = lite_window("see here\n", cursor=4, mode="plain")
    win.set_document_language("plain", announce=False)
    win.cmd_insert_link()
    assert "Markdown or HTML" in win.announcements[-1]
    assert lite_dialogs.names() == []


# --------------------------------------------------------------------------- #
# Toggle Line Comment (Ctrl+/)
# --------------------------------------------------------------------------- #


def test_commenting_uses_the_prefix_the_file_name_asks_for(lite_window, tmp_path) -> None:
    win = lite_window("value = 1\nother = 2\n", cursor=0, mode="plain")
    win.path = tmp_path / "script.py"
    win.control.SetSelection(0, 19)
    win.cmd_toggle_line_comment()
    assert win.control.GetValue() == "# value = 1\n# other = 2\n"
    assert win.announcements[-1] == "Commented 2 lines"


def test_commenting_again_brings_the_lines_back(lite_window, tmp_path) -> None:
    win = lite_window("value = 1\n", cursor=0, mode="plain")
    win.path = tmp_path / "script.py"
    win.cmd_toggle_line_comment()
    win.cmd_toggle_line_comment()
    assert win.control.GetValue() == "value = 1\n"
    assert win.announcements[-1] == "Uncommented 1 line"


def test_a_sql_file_gets_sql_comments(lite_window, tmp_path) -> None:
    win = lite_window("select 1\n", cursor=0, mode="plain")
    win.path = tmp_path / "query.sql"
    win.cmd_toggle_line_comment()
    assert win.control.GetValue().startswith("-- ")


def test_commenting_is_refused_in_rich_text(lite_window) -> None:
    win = lite_window("value = 1\n", cursor=0, mode="rich")
    win.cmd_toggle_line_comment()
    assert "plain text" in win.announcements[-1]
    assert win.control.GetValue() == "value = 1\n"


# --------------------------------------------------------------------------- #
# The list-style ring in a Markdown document
# --------------------------------------------------------------------------- #


def test_the_ring_marks_bullets_then_numbers_then_neither(lite_window) -> None:
    win = lite_window("one\ntwo\nthree\n", cursor=0, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.control.SetSelection(0, 13)

    win.cmd_cycle_list_style()
    assert win.control.GetValue() == "- one\n- two\n- three\n"
    assert win.announcements[-1] == "Bulleted list"

    win.control.SetSelection(0, 19)
    win.cmd_cycle_list_style()
    assert win.control.GetValue() == "1. one\n2. two\n3. three\n"
    assert win.announcements[-1] == "Numbered list"

    win.control.SetSelection(0, 22)
    win.cmd_cycle_list_style()
    assert win.control.GetValue() == "one\ntwo\nthree\n"
    assert win.announcements[-1] == "Not a list"


def test_the_ring_touches_only_the_lines_you_chose(lite_window) -> None:
    """QUILL's list-off rewrote the entire buffer, which removed every other
    list in the file and cleared the undo stack with them (bad.md R2)."""
    win = lite_window("- keep\n\none\ntwo\n", cursor=0, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.control.SetSelection(8, 15)
    win.cmd_cycle_list_style()
    assert win.control.GetValue() == "- keep\n\n- one\n- two\n"


def test_with_no_selection_the_ring_takes_the_caret_line(lite_window) -> None:
    win = lite_window("one\ntwo\n", cursor=5, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.cmd_cycle_list_style()
    assert win.control.GetValue() == "one\n- two\n"


def test_the_ring_says_so_in_an_html_document(lite_window) -> None:
    """``<ul>`` needs a wrapper as well as per-item tags, and half of one is a
    document that will not render."""
    win = lite_window("one\ntwo\n", cursor=0, mode="plain")
    win.set_document_language("html", announce=False)
    win.cmd_cycle_list_style()
    assert win.control.GetValue() == "one\ntwo\n"
    assert "formatting" in win.announcements[-1].lower()
