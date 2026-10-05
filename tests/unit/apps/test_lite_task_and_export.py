"""Toggle Task Done and Export as HTML in QUILL Lite: QUILL's shared commands.

Each handler is called (GATE-LITE-COVER). The check is one edit, so Ctrl+Z takes
it back; the export writes a whole page and leaves the document as it was.
"""

from __future__ import annotations

import wx

DOC = "Plan\n- [ ] Write the tests\n- [x] Read the plan\n* [ ] Ship it\n\nDone.\n"


def test_toggle_ticks_the_caret_line_and_says_the_count(lite_window) -> None:
    win = lite_window(DOC, cursor=DOC.index("Write"))

    win.cmd_toggle_task_done()

    assert "- [x] Write the tests" in win.control.GetValue()
    assert win.announcements[-1] == "Checked: Write the tests. 2 of 3 tasks complete."
    assert win.modified is True
    assert win.control.GetInsertionPoint() == DOC.index("Write"), "the caret stays"
    win.control.Undo()
    assert win.control.GetValue() == DOC


def test_toggle_unticks_and_handles_a_selection(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(DOC.index("- [ ] Write"), DOC.index("Ship it"))

    win.cmd_toggle_task_done()
    assert win.control.GetValue().count("[x]") == 3
    assert win.announcements[-1] == "Checked 2 tasks. 3 of 3 tasks complete."

    win.cmd_toggle_task_done()
    assert "[x]" not in win.control.GetValue()


def test_toggle_on_a_line_that_is_not_a_task_changes_nothing(lite_window) -> None:
    win = lite_window(DOC, cursor=DOC.index("Done."))
    win.cmd_toggle_task_done()
    assert win.control.GetValue() == DOC
    assert win.announcements[-1] == "Not a task line"


def test_export_html_writes_a_page_and_keeps_the_document(
    lite_window, fake_wx_dialog, tmp_path
) -> None:
    text = "# Plan\n\n- [x] Done ~~old~~\n<!-- quill-note: private review -->\n"
    win = lite_window(text, cursor=0)
    win._language_override = "markdown"
    target = tmp_path / "plan"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(target))
    asked: list[str] = []
    win._host_ask_yes_no = lambda m, _c: asked.append(m) or False

    win.cmd_export_html()

    page = (tmp_path / "plan.html").read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert '<html lang="en">' in page and "<title>Untitled</title>" in page
    assert '<input type="checkbox" disabled checked>' in page
    assert "<del>old</del>" in page
    assert "private review" not in page, "notes stay out unless asked for"
    assert asked == [
        "This document has 1 note written into it. Include them in the page, marked as notes?"
    ]
    assert win.control.GetValue() == text
    assert win.announcements[-1] == "Exported plan.html"


def test_export_html_can_include_notes(lite_window, fake_wx_dialog, tmp_path) -> None:
    win = lite_window("Para\n<!-- quill-note: keep -->\n", cursor=0)
    win._language_override = "markdown"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(tmp_path / "p.html"))
    win._host_ask_yes_no = lambda _m, _c: True
    win.cmd_export_html()
    page = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert '<aside class="quill-note" aria-label="Note">' in page


def test_export_html_cancelled(lite_window, fake_wx_dialog) -> None:
    win = lite_window(DOC, cursor=0)
    fake_wx_dialog("FileDialog", wx.ID_CANCEL)
    win.cmd_export_html()
    assert win.announcements[-1] == "Export cancelled"
