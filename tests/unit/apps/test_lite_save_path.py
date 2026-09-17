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

#: A character Windows-1252 cannot hold. An em dash is *not* one -- cp1252 has it
#: at 0x97 -- and picking one that happens to encode is how a test for this
#: passes while the bug is still there.
UNENCODABLE = "✓"


@pytest.fixture()
def answers(monkeypatch):
    """Answer the save path's message boxes, and record what they asked."""
    from quill.apps import lite_window_commands as commands
    from quill.apps import lite_window_file as filemod

    asked: list[str] = []
    replies: list[int] = []

    def _ask(message, *_a, **_k):
        asked.append(message)
        return replies.pop(0) if replies else wx.YES

    monkeypatch.setattr(commands, "show_message_box", _ask)
    monkeypatch.setattr(filemod, "show_message_box", _ask)
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


def test_a_recovered_document_keeps_the_encoding_it_came_from(tmp_path) -> None:
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


def test_a_slot_from_an_older_build_reads_as_unknown(tmp_path) -> None:
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
