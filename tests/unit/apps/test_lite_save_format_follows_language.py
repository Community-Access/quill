"""Save As offers the document under the kind the document says it is.

The report: "I was in markdown mode, pressed Ctrl+S, and it offered to save a
text file." It did -- the proposed name was always ``Untitled.txt`` and the type
list always opened on "Text files (*.txt)", both of which ignored the one thing
the person had just told the app about this document. wx appends the selected
row's extension to a name typed without one, so the list's opening row is not
decoration: it decides what the file is called.

The named-document case is deliberately *not* here. A ``notes.txt`` somebody has
switched to Markdown keeps saving to ``notes.txt`` on Ctrl+S, because plain text
is a perfectly good container for Markdown and a Ctrl+S that suddenly opens a
dialog is a worse surprise than the one this fixes.
"""

from __future__ import annotations

import wx


def _save_as_with_recorded_dialog(win, fake_wx_dialog, target):
    """Run Save As against a recording dialog; return (kwargs, filter indexes)."""
    chosen: list[int] = []
    dialog = fake_wx_dialog(
        "FileDialog",
        wx.ID_OK,
        GetPath=str(target),
        SetFilterIndex=chosen.append,
    )
    win.cmd_save_as()
    return dialog.constructed[-1][1], chosen


def test_an_untitled_markdown_document_is_offered_as_markdown(
    lite_window, fake_wx_dialog, tmp_path
) -> None:
    win = lite_window("# Heading 1\n\nbody\n", cursor=0)
    win.set_document_language("markdown", announce=False)

    kwargs, chosen = _save_as_with_recorded_dialog(win, fake_wx_dialog, tmp_path / "notes.md")

    assert kwargs["defaultFile"] == "Untitled.md"
    assert chosen == [1], "the Markdown row of SAVE_WILDCARD_PLAIN"


def test_an_untitled_plain_document_is_still_offered_as_text(
    lite_window, fake_wx_dialog, tmp_path
) -> None:
    win = lite_window("just a note\n", cursor=0)

    kwargs, chosen = _save_as_with_recorded_dialog(win, fake_wx_dialog, tmp_path / "notes.txt")

    assert kwargs["defaultFile"] == "Untitled.txt"
    assert chosen == [0]


def test_an_untitled_html_document_is_offered_under_its_own_extension(
    lite_window, fake_wx_dialog, tmp_path
) -> None:
    """HTML lands on "All files" rather than a row of its own: QuillLite has no
    Markdown-to-HTML writer, so an HTML row would be a promise it cannot keep.
    The name is the part that was wrong, and the name is fixed."""
    win = lite_window("<h1>Title</h1>\n", cursor=0)
    win.set_document_language("html", announce=False)

    kwargs, chosen = _save_as_with_recorded_dialog(win, fake_wx_dialog, tmp_path / "page.html")

    assert kwargs["defaultFile"] == "Untitled.html"
    assert chosen == [3]


def test_a_rich_document_is_unaffected(lite_window, fake_wx_dialog, tmp_path) -> None:
    """The rich type list is a different list, and .rtf is already its first row."""
    win = lite_window("formatted words", cursor=0, mode="rich")

    kwargs, chosen = _save_as_with_recorded_dialog(win, fake_wx_dialog, tmp_path / "notes.rtf")

    assert kwargs["defaultFile"] == "Untitled.rtf"
    assert chosen == [], "nothing to preselect; the rich wildcard leads with .rtf"


def test_a_named_document_keeps_its_name(lite_window, fake_wx_dialog, tmp_path) -> None:
    win = lite_window("# Heading 1\n", cursor=0)
    win.path = tmp_path / "notes.txt"
    win.set_document_language("markdown", announce=False)

    kwargs, chosen = _save_as_with_recorded_dialog(win, fake_wx_dialog, tmp_path / "notes.txt")

    assert kwargs["defaultFile"] == "notes.txt", "Save As renames nothing on its own"
    assert chosen == [1], "but the type list still opens where the document lives"
