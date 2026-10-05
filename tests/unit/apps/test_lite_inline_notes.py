"""Inline notes in QUILL Lite: QUILL's six commands, shared, on QUILL's chords.

Every handler is *called* here (GATE-LITE-COVER): Add, Next, Previous, Speak,
Delete and List, for both kinds of note -- the private sidecar, and the note
written into a Markdown file as a ``quill-note`` comment, which is an ordinary
edit and so goes through the undo stack.
"""

from __future__ import annotations

import json

import pytest
import wx

from quill.core.inline_notes_file import parse_file_notes

DOC = "# Plan\n\nBack up the uploads folder.\n\n- [ ] Write the tests\n- [ ] Ship it\n"


def _markdown(win) -> None:
    win._language_override = "markdown"


@pytest.fixture
def note_dialog(monkeypatch):
    """Answer the note dialog: ``answers`` is a list of (action, text, in_file)."""
    calls: list[dict] = []
    answers: list[tuple[str, str, bool]] = []

    def fake(_wx, _parent, _show, **kwargs):
        calls.append(kwargs)
        return answers.pop(0) if answers else ("cancel", "", False)

    monkeypatch.setattr("quill.ui.inline_note_dialog.show_inline_note_dialog", fake)
    return calls, answers


def test_add_a_private_note_on_the_caret_line(lite_window, note_dialog) -> None:
    calls, answers = note_dialog
    win = lite_window(DOC, cursor=DOC.index("Back up"))
    answers.append(("save", "And the database.", False))

    win.cmd_add_inline_note()

    assert calls[0]["note_on"] == "Back up the uploads folder."
    assert win.control.GetValue() == DOC, "a private note never touches the file"
    assert [n.text for n in win._inline_notes] == ["And the database."]
    assert win.announcements[-1] == "Inline note added."


def test_add_a_note_into_a_markdown_file_is_an_edit(lite_window, note_dialog) -> None:
    calls, answers = note_dialog
    win = lite_window(DOC, cursor=DOC.index("Write the tests"))
    _markdown(win)
    answers.append(("save", "Use -- the real data.", True))

    win.cmd_add_inline_note()

    assert calls[0]["in_file_available"] is True
    text = win.control.GetValue()
    assert "  <!-- quill-note: Use -&#45; the real data. -->\n- [ ] Ship it" in text
    notes = parse_file_notes(text)
    assert [n.text for n in notes] == ["Use -- the real data."]
    assert win.modified is True
    win.control.Undo()
    assert win.control.GetValue() == DOC, "Ctrl+Z takes the note back"


def test_the_setting_decides_the_check_box_until_the_document_chooses(
    lite_window, note_dialog
) -> None:
    calls, answers = note_dialog
    win = lite_window(DOC, cursor=0)
    _markdown(win)
    win.app.settings.inline_notes_in_file = True
    answers.append(("save", "x", False))
    win.cmd_add_inline_note()
    assert calls[0]["in_file"] is True
    win.cmd_add_inline_note()  # cancelled: the document's last choice holds
    assert calls[1]["in_file"] is False
    assert win.announcements[-1] == "Add inline note cancelled"


def test_plain_documents_cannot_take_notes_in_the_file(lite_window, note_dialog) -> None:
    calls, answers = note_dialog
    win = lite_window(DOC, cursor=0)
    answers.append(("save", "kept private", True))
    win.cmd_add_inline_note()
    assert calls[0]["in_file_available"] is False
    assert win.control.GetValue() == DOC
    assert len(win._inline_notes) == 1


def _with_both_kinds(lite_window):
    text = DOC.replace("folder.\n", "folder.\n<!-- quill-note: in the file -->\n")
    win = lite_window(text, cursor=0)
    _markdown(win)
    from quill.core.inline_notes import make_inline_note

    start = text.index("Ship it")
    win._inline_notes = [make_inline_note("private one", text, start, start + 7)]
    return win, text


def test_next_and_previous_walk_both_kinds_and_wrap(lite_window) -> None:
    win, text = _with_both_kinds(lite_window)

    win.cmd_next_inline_note()
    assert win.control.GetInsertionPoint() == text.index("Back up")
    assert win.announcements[-1] == "Inline note 1 of 2: in the file"
    win.cmd_next_inline_note()
    assert win.announcements[-1] == "Inline note 2 of 2: private one"
    win.cmd_next_inline_note()
    assert win.announcements[-1].startswith("Inline note 1 of 2"), "wraps"
    win.cmd_previous_inline_note()
    assert win.announcements[-1] == "Inline note 2 of 2: private one"


def test_no_notes_is_said_plainly(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    for command in (
        lambda w: w.cmd_next_inline_note(),
        lambda w: w.cmd_previous_inline_note(),
        lambda w: w.cmd_speak_inline_note(),
        lambda w: w.cmd_delete_inline_note(),
        lambda w: w.cmd_list_inline_notes(),
    ):
        command(win)
        assert win.announcements[-1] == "No inline notes in this document"


def test_speak_says_the_note_and_twice_edits_it(lite_window, note_dialog) -> None:
    calls, answers = note_dialog
    win, text = _with_both_kinds(lite_window)
    win.control.SetInsertionPoint(text.index("Back up") + 2)

    win.cmd_speak_inline_note()
    assert win.announcements[-1] == "Inline note: in the file"
    answers.append(("save", "changed", False))
    win.cmd_speak_inline_note()
    assert calls[-1]["title"] == "Edit Inline Note"
    assert [n.text for n in parse_file_notes(win.control.GetValue())] == ["changed"]
    assert win.announcements[-1] == "Inline note updated."


def test_delete_asks_and_no_keeps_the_note(lite_window, monkeypatch) -> None:
    win, text = _with_both_kinds(lite_window)
    win.control.SetInsertionPoint(text.index("Back up"))
    asked: list[str] = []
    monkeypatch.setattr(win, "_host_ask_yes_no", lambda m, _c: asked.append(m) or False)

    win.cmd_delete_inline_note()
    assert 'Delete the note "in the file"?' in asked[0]
    assert win.control.GetValue() == text

    monkeypatch.setattr(win, "_host_ask_yes_no", lambda _m, _c: True)
    win.cmd_delete_inline_note()
    assert "quill-note" not in win.control.GetValue()
    assert win.announcements[-1] == "Inline note deleted."


def test_list_goes_to_the_chosen_note(lite_window, monkeypatch) -> None:
    win, text = _with_both_kinds(lite_window)
    seen: dict = {}

    def fake_list(_wx, _parent, _show, host):
        rows = host.rows()
        seen["rows"] = [(r.text, r.line, r.kind_label()) for r in rows]
        return rows[1]

    monkeypatch.setattr("quill.ui.inline_notes_list_dialog.show_inline_notes_list", fake_list)
    win.cmd_list_inline_notes()

    assert seen["rows"] == [("in the file", 3, "In the file"), ("private one", 7, "Private")]
    assert win.control.GetInsertionPoint() == text.index("Ship it")


def test_list_remove_all_copy_and_export(lite_window, monkeypatch, fake_wx_dialog, tmp_path):
    win, _text = _with_both_kinds(lite_window)
    target = tmp_path / "notes.json"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(target), GetFilterIndex=1)
    monkeypatch.setattr(win, "_host_ask_yes_no", lambda _m, _c: True)

    def fake_list(_wx, _parent, _show, host):
        rows = host.rows()
        host.copy_all(rows)
        host.export(rows)
        assert host.remove_all() == 2
        assert host.rows() == []
        return None

    monkeypatch.setattr("quill.ui.inline_notes_list_dialog.show_inline_notes_list", fake_list)
    win.cmd_list_inline_notes()

    assert 'Note 1, line 3, on "Back up the uploads folder."' in win.control.clipboard
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert [n["note"] for n in payload["notes"]] == ["in the file", "private one"]
    assert "quill-note" not in win.control.GetValue()
    assert win._inline_notes == []
    assert "2 notes removed" in win.announcements


def test_an_orphaned_note_is_listed_last_and_cannot_be_gone_to(lite_window, monkeypatch):
    from quill.core.inline_notes import InlineNote

    win = lite_window(DOC, cursor=0)
    win._inline_notes = [InlineNote("x", "orphan", "NOT HERE", "", "", 0, 0)]

    def fake_list(_wx, _parent, _show, host):
        rows = host.rows()
        assert rows[0].on_label() == "the text it was on is gone"
        return rows[0]

    monkeypatch.setattr("quill.ui.inline_notes_list_dialog.show_inline_notes_list", fake_list)
    win.cmd_list_inline_notes()
    assert win.announcements[-1] == "Nothing to go to: the text it was on is gone."


def test_private_notes_persist_per_file(lite_window, note_dialog, tmp_path) -> None:
    _calls, answers = note_dialog
    win = lite_window(DOC, cursor=0)
    win.path = tmp_path / "plan.md"
    answers.append(("save", "remember me", False))
    win.cmd_add_inline_note()

    again = lite_window(DOC, cursor=0)
    again.path = tmp_path / "plan.md"
    again.cmd_speak_inline_note()
    assert again.announcements[-1] == "Inline note: remember me"
