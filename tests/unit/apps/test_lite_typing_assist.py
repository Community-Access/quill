"""QUILL Lite's Enter-in-a-list and AutoCorrect, through the window's own key handlers.

The same rules QUILL runs (quill/core/list_continuation.py, quill/core/autocorrect.py),
reached the way the real window reaches them: ``_on_key_down`` for Enter and
``_on_char`` for the space, on the shipped mixins over the fake control, whose
undo stack treats a select-and-write as one step exactly as the native control
does. QUILL's twin is tests/unit/ui/test_main_frame_typing_assist.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.abbreviations import AbbreviationLibrary
from quill.core.autocorrect import set_correction, stop_correction
from tests.wx_session import patch_call_after


class _Key:
    def __init__(self, code: int) -> None:
        self.code = code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self.code

    def GetUnicodeKey(self) -> int:
        return self.code

    def ControlDown(self) -> bool:
        return False

    def ShiftDown(self) -> bool:
        return False

    def AltDown(self) -> bool:
        return False

    def Skip(self) -> None:
        self.skipped = True


@pytest.fixture(autouse=True)
def _no_call_after(monkeypatch: pytest.MonkeyPatch) -> None:
    """The abbreviation check is posted after the keystroke; nothing here wants it."""
    patch_call_after(monkeypatch, lambda *_a, **_k: None)


def _enter(win: Any) -> _Key:
    event = _Key(wx.WXK_RETURN)
    win._on_key_down(event)
    if event.skipped:
        win.control.WriteText("\n")  # what the control does with a skipped Enter
    return event


def _space(win: Any) -> _Key:
    win.schedule_live_spell_check = lambda: None  # a wx.Timer; not this test's subject
    event = _Key(32)
    win._on_char(event)
    if event.skipped:
        win.control.WriteText(" ")
    return event


def _on(win: Any, library: AbbreviationLibrary | None = None) -> Any:
    win.app.settings.autocorrect_misspellings = True
    win.app.abbreviations = library or AbbreviationLibrary(version=2, abbreviations=[])
    return win


# -- Enter in a list ---------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "after"),
    [("1. one", "1. one\n2. "), ("1) one", "1) one\n2) "), ("    - deep", "    - deep\n    - ")],
)
def test_enter_continues_a_markdown_list(lite_window, text: str, after: str) -> None:
    win = lite_window(text, cursor=len(text), name="notes.md")
    _enter(win)
    assert win.control.GetValue() == after
    assert win.control.GetInsertionPoint() == len(after)
    assert win.announcements[-1] == "Continued list item"


def test_a_split_and_its_renumbering_are_one_undo_step(lite_window) -> None:
    text = "1. bread milk\n2. eggs"
    win = lite_window(text, cursor=len("1. bread"), name="notes.md")
    _enter(win)
    assert win.control.GetValue() == "1. bread\n2. milk\n3. eggs"
    win.cmd_undo()
    assert win.control.GetValue() == text
    assert not win.control.CanUndo()


def test_enter_on_an_empty_item_ends_the_list(lite_window) -> None:
    win = lite_window("- a\n- ", cursor=6, name="notes.md")
    _enter(win)
    assert win.control.GetValue() == "- a\n"
    assert win.announcements[-1] == "Exited list"


def test_an_ordinary_enter_does_not_read_the_document(lite_window) -> None:
    """The cheap look at the line comes first, so typing prose costs no buffer read."""
    win = lite_window("Dear Sam,", cursor=9, name="notes.md")
    win.control.value_reads = 0
    assert _enter(win).skipped
    assert win.control.value_reads == 0


def test_plain_text_waits_for_the_setting(lite_window) -> None:
    win = lite_window("1. one", cursor=6, name="notes.txt")
    assert _enter(win).skipped
    assert win.control.GetValue() == "1. one\n"

    win = lite_window("1. one", cursor=6, name="notes.txt")
    win.app.settings.continue_lists_in_plain_text = True
    _enter(win)
    assert win.control.GetValue() == "1. one\n2. "


def test_code_and_rich_text_are_never_continued(lite_window) -> None:
    win = lite_window("1. step", cursor=7, name="steps.py")
    win.app.settings.continue_lists_in_plain_text = True
    assert _enter(win).skipped

    rich = lite_window("- a", cursor=3, mode="rich")
    rich.app.settings.continue_lists_in_plain_text = True
    assert _enter(rich).skipped


def test_markdown_follows_the_markdown_area(lite_window) -> None:
    win = lite_window("- a", cursor=3, name="notes.md")
    win.app.feature_enabled = lambda area: area != "markup"
    assert _enter(win).skipped


# -- AutoCorrect ------------------------------------------------------------------- #


def test_off_by_default(lite_window) -> None:
    win = lite_window("teh", cursor=3, name="notes.txt")
    _space(win)
    assert win.control.GetValue() == "teh "


def test_the_area_is_the_master_switch(lite_window) -> None:
    win = _on(lite_window("teh", cursor=3, name="notes.txt"))
    win.app.feature_enabled = lambda area: area != "autoformat"
    _space(win)
    assert win.control.GetValue() == "teh "


def test_a_space_corrects_as_one_undo_step_with_a_sound_and_the_word(lite_window) -> None:
    win = _on(lite_window("I saw teh", cursor=9, name="notes.txt"))
    assert not _space(win).skipped
    assert win.control.GetValue() == "I saw the "
    assert win.announcements[-1] == "Corrected to the"
    assert "word_corrected" in win.cues
    win.cmd_undo()
    assert win.control.GetValue() == "I saw teh"


def test_undo_then_space_keeps_what_you_typed(lite_window) -> None:
    win = _on(lite_window("Recieve", cursor=7, name="notes.txt"))
    _space(win)
    assert win.control.GetValue() == "Receive "
    win.cmd_undo()
    _space(win)
    assert win.control.GetValue() == "Recieve "
    win.control.WriteText("recieve")
    _space(win)
    assert win.control.GetValue() == "Recieve recieve "


def test_enter_corrects_then_continues_the_list(lite_window) -> None:
    win = _on(lite_window("- teh", cursor=5, name="notes.md"))
    _enter(win)
    assert win.control.GetValue() == "- the\n- "


@pytest.mark.parametrize(
    "text", ["go to teh.example.com", "write to adress@example.com", "WIERD", "`teh` x teh_y"]
)
def test_addresses_identifiers_and_capitals_are_left_alone(lite_window, text: str) -> None:
    win = _on(lite_window(text, cursor=len(text), name="notes.md"))
    _space(win)
    assert win.control.GetValue() == text + " "


@pytest.mark.parametrize("name", ["main.py", "settings.json", "config.yml", "page.html"])
def test_never_in_code_or_configuration(lite_window, name: str) -> None:
    win = _on(lite_window("teh", cursor=3, name=name))
    _space(win)
    assert win.control.GetValue() == "teh "


def test_your_entries_overrides_and_stops(lite_window) -> None:
    library = AbbreviationLibrary(version=2, abbreviations=[])
    set_correction(library, "qill", "QUILL")
    set_correction(library, "teh", "tea")
    stop_correction(library, "recieve")
    win = _on(lite_window("qill", cursor=4, name="notes.txt"), library)
    _space(win)
    win.control.WriteText("teh")
    _space(win)
    win.control.WriteText("recieve")
    _space(win)
    assert win.control.GetValue() == "QUILL tea recieve "


def test_the_built_in_list_works_with_abbreviations_switched_off(lite_window) -> None:
    win = lite_window("teh", cursor=3, name="notes.txt")
    win.app.settings.autocorrect_misspellings = True
    win.app.abbreviations = None
    _space(win)
    assert win.control.GetValue() == "the "


def test_autocorrect_entries_edits_and_saves_through_the_app(lite_window, monkeypatch) -> None:
    import quill.ui.autocorrect_entries_dialog as dialog_module
    import quill.ui.dialog_contract as contract

    saved: list[bool] = []

    class _Dialog:
        def __init__(self, _parent: Any, library: AbbreviationLibrary, **_k: Any) -> None:
            self.dialog = object()
            self.changed = True
            set_correction(library, "qill", "QUILL")

        def close(self) -> None:
            return None

    monkeypatch.setattr(dialog_module, "AutocorrectEntriesDialog", _Dialog)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: wx.ID_CANCEL)
    win = _on(lite_window("", cursor=0, name="notes.txt"))
    win.app.save_autocorrect_library = lambda: saved.append(True)
    win.cmd_autocorrect_entries()
    assert saved == [True]
    assert win.status_messages[-1] == "AutoCorrect entries saved"
    assert win.control.focused


def test_the_service_reads_and_writes_the_one_abbreviation_file(tmp_path: Path) -> None:
    """With abbreviations off, corrections still load -- and save to the same file."""
    from quill.apps.lite_services import LiteServicesMixin
    from quill.core.abbreviations_store import load_abbreviation_library

    class _App(LiteServicesMixin):
        def __init__(self) -> None:
            from quill.core.lite.settings import Settings

            self.settings = Settings()
            self.data_dir = tmp_path
            self.abbreviations = None

        def feature_enabled(self, area: str) -> bool:
            return area != "abbreviations"

    app = _App()
    library = app.autocorrect_library()
    assert isinstance(library, AbbreviationLibrary)
    set_correction(library, "qill", "QUILL")
    app.save_autocorrect_library()
    again = load_abbreviation_library(tmp_path)
    assert any(entry.abbreviation == "qill" for entry in again.abbreviations)
    assert app.autocorrect_library() is not library  # re-read after the save
