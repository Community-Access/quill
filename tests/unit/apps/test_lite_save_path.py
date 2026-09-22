"""What a failed save must not cost, and what a silent one must not lose.

Four Broken rows of bad.md section 6, and they share a shape: the app did the
irreversible half first and the checkable half second. Save As converted the
*window* and then tried the file; recovery adopted a slot's own encoding and then
wrote the document back in it; a failed restore claimed the path before it knew
whether it had anything; and a character the encoding could not hold became a
question mark with nothing said.

The tests are about order and about what is said. Every one of them describes a
moment where the user is told everything went well.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.io.rtf import markdown_to_rtf

#: A character Windows-1252 cannot hold. An em dash is *not* one -- cp1252 has it
#: at 0x97 -- and picking one that happens to encode is how a test for this
#: passes while the bug is still there.
UNENCODABLE = "✓"


@pytest.fixture()
def answers(monkeypatch):
    """Answer the save path's message boxes, and record what they asked."""
    from quill.apps import lite_window_commands as commands
    from quill.apps import lite_window_file as filemod
    from quill.apps import lite_window_mode as modemod

    asked: list[str] = []
    replies: list[int] = []

    def _ask(message, *_a, **_k):
        asked.append(message)
        return replies.pop(0) if replies else wx.YES

    monkeypatch.setattr(commands, "show_message_box", _ask)
    monkeypatch.setattr(filemod, "show_message_box", _ask)
    # Patched where it was imported, not where it is defined: the mode switch
    # asks its own question, and a test that reached the real one would open a
    # message box in CI (tests/unit/apps/conftest.py, DialogRecorder).
    monkeypatch.setattr(modemod, "show_message_box", _ask)
    return {"asked": asked, "replies": replies}


# --------------------------------------------------------------------------- #
# F3. Characters the encoding cannot hold
# --------------------------------------------------------------------------- #


def test_a_character_the_encoding_cannot_hold_is_named_before_the_write(
    lite_window, answers, tmp_path
) -> None:
    win = lite_window(f"a tick: {UNENCODABLE}", cursor=0)
    win.encoding = "cp1252"
    win.path = tmp_path / "notes.txt"
    answers["replies"].append(wx.YES)

    assert win.save() is True
    assert "1 character cannot be saved as Windows-1252 (ANSI)" in answers["asked"][0]
    assert win.encoding == "utf-8", "Yes means save it as UTF-8 from now on"
    assert UNENCODABLE in (tmp_path / "notes.txt").read_text(encoding="utf-8")


def test_saying_no_saves_as_asked_and_loses_them_knowingly(lite_window, answers, tmp_path) -> None:
    win = lite_window(f"a tick: {UNENCODABLE}", cursor=0)
    win.encoding = "cp1252"
    win.path = tmp_path / "notes.txt"
    answers["replies"].append(wx.NO)

    assert win.save() is True
    assert win.encoding == "cp1252"
    assert UNENCODABLE not in (tmp_path / "notes.txt").read_bytes().decode("cp1252")


def test_cancelling_writes_nothing_at_all(lite_window, answers, tmp_path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("what was there before", encoding="cp1252")
    win = lite_window(f"a tick: {UNENCODABLE}", cursor=0)
    win.encoding = "cp1252"
    win.path = target
    answers["replies"].append(wx.CANCEL)

    assert win.save() is False
    assert target.read_text(encoding="cp1252") == "what was there before"
    assert win.announcements[-1] == "Save cancelled"


def test_a_document_that_fits_is_never_asked_about(lite_window, answers, tmp_path) -> None:
    win = lite_window("plain ascii", cursor=0)
    win.encoding = "cp1252"
    win.path = tmp_path / "notes.txt"
    assert win.save() is True
    assert answers["asked"] == []


def test_the_core_names_the_characters_that_will_not_fit() -> None:
    from quill.core.lite.textfile import unencodable_characters

    assert unencodable_characters("plain", "cp1252") == []
    assert unencodable_characters(f"a{UNENCODABLE}b{UNENCODABLE}", "cp1252") == [UNENCODABLE]
    assert unencodable_characters(f"a{UNENCODABLE}", "utf-8") == []


# --------------------------------------------------------------------------- #
# F1. Save As converts the file, not the window
# --------------------------------------------------------------------------- #


def test_a_failed_flatten_leaves_the_rich_document_alone(
    lite_window, answers, fake_wx_dialog, tmp_path
) -> None:
    """The heart of F1: the window used to be flattened *before* the write, and
    ChangeValue is off the undo stack -- so a locked file or a full disk cost
    the formatting and left the flat text sitting under the .rtf name."""
    win = lite_window("formatted words", cursor=0, mode="rich")
    win.path = tmp_path / "notes.rtf"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(tmp_path / "notes.txt"))
    answers["replies"].append(wx.YES)  # yes, flatten

    def _explode(*_a, **_k):
        raise OSError("the disk is full")

    from quill.apps import lite_window_file as filemod

    original = filemod.write_bytes_atomic
    filemod.write_bytes_atomic = _explode
    try:
        assert win.cmd_save_as() is False
    finally:
        filemod.write_bytes_atomic = original

    assert win.editor.mode == "rich", "a failed save must not flatten the window"
    assert win.path == tmp_path / "notes.rtf", "nor rename it"


def test_a_good_flatten_writes_the_file_then_changes_the_window(
    lite_window, answers, fake_wx_dialog, tmp_path
) -> None:
    win = lite_window("formatted words", cursor=0, mode="rich")
    win.path = tmp_path / "notes.rtf"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(tmp_path / "notes.txt"))
    answers["replies"].append(wx.YES)

    assert win.cmd_save_as() is True
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "formatted words"
    assert win.editor.mode == "plain"
    assert win.path == tmp_path / "notes.txt"


def test_a_failed_markdown_conversion_leaves_the_html_in_the_window(
    lite_window, answers, fake_wx_dialog, tmp_path
) -> None:
    html = "<h1>Title</h1>\n<p>body</p>\n"
    win = lite_window(html, cursor=0)
    win.path = tmp_path / "page.html"
    win.set_document_language("html", announce=False)
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(tmp_path / "page.md"))

    def _explode(*_a, **_k):
        raise OSError("the file is locked")

    from quill.apps import lite_window_file as filemod

    original = filemod.write_bytes_atomic
    filemod.write_bytes_atomic = _explode
    try:
        assert win.cmd_save_as() is False
    finally:
        filemod.write_bytes_atomic = original

    assert win.control.GetValue() == html
    assert win.path == tmp_path / "page.html"


def test_a_good_markdown_conversion_writes_markdown_and_updates_the_window(
    lite_window, answers, fake_wx_dialog, tmp_path
) -> None:
    win = lite_window("<h1>Title</h1>\n<p>body</p>\n", cursor=0)
    win.path = tmp_path / "page.html"
    win.set_document_language("html", announce=False)
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(tmp_path / "page.md"))

    assert win.cmd_save_as() is True
    written = (tmp_path / "page.md").read_text(encoding="utf-8")
    assert written.startswith("# Title")
    assert win.control.GetValue() == written
    assert win.announcements[-1] == "Converted HTML to Markdown"


def test_html_that_converts_to_nothing_is_saved_unchanged(lite_window) -> None:
    """Saving the HTML under a .md name is the silent-wrong-file case, so the
    planner says "nothing to convert" and the buffer is written as it stands."""
    win = lite_window("<!-- only a comment -->", cursor=0)
    win.set_document_language("html", announce=False)
    assert win.plan_markdown_conversion(Path("page.md")) is None


# --------------------------------------------------------------------------- #
# F2 and F9. Recovery
# --------------------------------------------------------------------------- #


def test_a_recovered_document_keeps_the_encoding_it_came_from(
    tmp_path, lite_recovery_store
) -> None:
    """The slot is always UTF-8 with LF, because a copy of unsaved work has to
    hold whatever was typed. The window used to adopt *that*, so a cp1252/CRLF
    file recovered after a crash was saved back as UTF-8/LF (bad.md F2)."""
    from quill.core.lite import recovery

    slot = recovery.new_slot("plain", str(tmp_path / "notes.txt"))
    slot.content_path.write_bytes(b"body")
    slot.encoding = "cp1252"
    slot.newline = "\r\n"
    recovery.write_meta(slot)

    back = recovery.pending(slot.meta_path.parent)
    found = [one for one in back if one.slot_id == slot.slot_id]
    assert found and found[0].encoding == "cp1252"
    assert found[0].newline == "\r\n"


def test_a_slot_from_an_older_build_reads_as_unknown(tmp_path, lite_recovery_store) -> None:
    """Empty, not wrong: the window then falls through to what the bytes say,
    which is exactly what it did before."""
    from quill.core.lite import recovery

    slot = recovery.new_slot("plain", "")
    slot.content_path.write_bytes(b"body")
    recovery.write_meta(slot)
    meta = slot.meta_path.read_text(encoding="utf-8").replace('"encoding": "", ', "")
    slot.meta_path.write_text(meta, encoding="utf-8")

    back = [one for one in recovery.pending(slot.meta_path.parent) if one.slot_id == slot.slot_id]
    assert back and back[0].encoding == ""


# --------------------------------------------------------------------------- #
# R6 -- Switch Document Mode converted nothing, in either direction
# --------------------------------------------------------------------------- #


def test_leaving_rich_text_turns_the_formatting_into_markdown(lite_window, answers) -> None:
    """It used to take GetValue() -- the characters -- and call that the answer.

    An afternoon of headings and bold became a wall of unmarked text, announced
    as "Plain text mode" (bad.md R6). QUILL has converted through
    ``quill.io.rtf`` since 0.9.0-beta3 and QuillLite may never be behind it.
    """
    win = lite_window("", cursor=0, mode="rich")
    win.editor.set_rtf(markdown_to_rtf("# Title\n\nSome **bold** text.\n").encode("utf-8"))

    win.switch_mode("plain")

    assert win.editor.mode == "plain"
    assert "# Title" in win.control.GetValue()
    assert "**bold**" in win.control.GetValue()
    assert win.announcements[-1] == "Plain text mode"


def test_the_document_is_called_markdown_once_it_holds_markdown(lite_window, answers) -> None:
    """The Format cell reads the language, and a buffer full of ## that the cell
    calls plain text is the cell lying about the one thing it is for."""
    win = lite_window("", cursor=0, mode="rich")
    win.editor.set_rtf(markdown_to_rtf("# Title\n").encode("utf-8"))
    win.switch_mode("plain")
    assert win.document_language() == "markdown"


def test_declining_the_switch_out_of_rich_changes_nothing(lite_window, answers) -> None:
    """Planned first, applied second -- the order the save path learned in F1."""
    win = lite_window("", cursor=0, mode="rich")
    win.editor.set_rtf(markdown_to_rtf("# Title\n").encode("utf-8"))
    before = win.control.GetValue()
    answers["replies"].append(wx.NO)

    win.switch_mode("plain")

    assert win.editor.mode == "rich"
    assert win.control.GetValue() == before


def test_the_warning_names_what_plain_text_cannot_carry(lite_window, answers) -> None:
    """QUILL's honest-fidelity gate: say what will be lost before losing it."""
    win = lite_window("", cursor=0, mode="rich")
    win.editor.rtf_bytes = rb"{\rtf1\ansi \trowd\cell a table\par}"

    win.switch_mode("plain")

    assert any("tables" in asked for asked in answers["asked"])


def test_a_markdown_document_becomes_real_formatting(lite_window, answers) -> None:
    """``## Title`` used to sit in a rich document as two hash marks and a space:
    the document said it was rich text and nothing in it was."""
    win = lite_window("## Title\n\nSome **bold** text.\n", cursor=0, name="notes.md")

    win.switch_mode("rich")

    assert win.editor.mode == "rich"
    assert any(call[0] == "set_rtf" for call in win.editor.calls)


def test_a_plain_text_file_is_not_read_as_markup(lite_window, answers) -> None:
    """The asymmetry, and it is the honest one: markup can always be read as
    text, but the asterisks in a shopping list are not bold."""
    win = lite_window("buy 2 * 3 eggs\n", cursor=0, name="list.txt")

    win.switch_mode("rich")

    assert win.editor.mode == "rich"
    assert not any(call[0] == "set_rtf" for call in win.editor.calls)
    assert win.control.GetValue() == "buy 2 * 3 eggs\n"


def test_a_mode_switch_keeps_the_name_and_proposes_the_right_one(lite_window, answers) -> None:
    """It used to set ``self.path = None``: safe, and unhelpful. The person still
    has a file open and now Ctrl+S asks them to find it again with nothing
    proposed. QUILL keeps the name and retargets the suffix."""
    win = lite_window("hello\n", cursor=0, name="notes.txt")

    win.switch_mode("rich")

    assert win.path is not None and win.path.name == "notes.txt"
    assert win.proposed_name_for_mode() == "notes.rtf"


def test_save_after_a_mode_switch_goes_through_save_as(lite_window, answers, monkeypatch) -> None:
    """Save proposes; it never writes RTF bytes into a file called .txt."""
    win = lite_window("hello\n", cursor=0, name="notes.txt")
    win.switch_mode("rich")

    asked_for_a_name: list[bool] = []
    monkeypatch.setattr(
        type(win), "cmd_save_as", lambda self: (asked_for_a_name.append(True), True)[1]
    )

    assert win.save() is True
    assert asked_for_a_name == [True]
