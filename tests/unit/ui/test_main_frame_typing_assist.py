"""QUILL's Enter-in-a-list and AutoCorrect paths (quill/ui/main_frame_typing_assist.py).

Driven through the real key handlers -- ``_on_editor_key_down`` for Enter and
``_on_editor_char_hook`` for the space -- on a MainFrame built without wx, the
way tests/unit/ui/test_main_frame_navigation.py builds one. The editor stub
keeps an undo stack with the native control's rule (selecting a span and
writing over it is one step), so "one Ctrl+Z" is asserted, not assumed. The
native control's half of that rule is pinned by test_main_frame_undo_atomic.py.

QUILL Lite's twin is tests/unit/apps/test_lite_typing_assist.py; the rules
themselves are tests/unit/core/test_list_continuation.py and test_autocorrect.py.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.a11y_regions import RegionTracker
from quill.core.abbreviations import AbbreviationLibrary
from quill.core.autocorrect import set_correction
from quill.core.document import Document
from quill.core.locations import LocationRing
from quill.ui.main_frame import MainFrame

RETURN, SPACE = 13, 32


@pytest.fixture(autouse=True)
def _isolated_quill_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


class _Editor:
    """Text, caret, selection and the native control's undo rule."""

    def __init__(self, text: str, caret: int) -> None:
        self._text = text
        self._caret = caret
        self._sel = (caret, caret)
        self.undo_stack: list[tuple[str, int]] = []

    def GetValue(self) -> str:
        return self._text

    def GetRange(self, start: int, end: int) -> str:
        return self._text[max(0, start) : max(0, end)]

    def GetInsertionPoint(self) -> int:
        return self._caret

    def SetInsertionPoint(self, value: int) -> None:
        self._caret = value
        self._sel = (value, value)

    def GetSelection(self) -> tuple[int, int]:
        return self._sel

    def SetSelection(self, start: int, end: int) -> None:
        self._sel = (start, end)
        self._caret = end

    def WriteText(self, value: str) -> None:
        start, end = self._sel
        self.undo_stack.append((self._text, self._caret))
        self._text = self._text[:start] + value + self._text[end:]
        self.SetInsertionPoint(start + len(value))

    def ChangeValue(self, value: str) -> None:
        self._text = value

    def CanUndo(self) -> bool:
        return bool(self.undo_stack)

    def Undo(self) -> None:
        self._text, self._caret = self.undo_stack.pop()
        self._sel = (self._caret, self._caret)

    def SetFocus(self) -> None:
        return None


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


def _frame(text: str, caret: int | None = None, *, name: str = "note.md", **settings: object):
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(path=Path(name) if name else None, text=text)
    frame.editor = _Editor(text, len(text) if caret is None else caret)
    frame.statusbar = SimpleNamespace(SetStatusText=lambda *_a: None, SetFocus=lambda: None)
    frame.frame = SimpleNamespace(SetTitle=lambda *_a: None, SetFocus=lambda: None)
    frame._location_ring = LocationRing()
    frame._region_tracker = RegionTracker()
    frame._active_region = "Editor"
    frame._status_message = "Ready"
    frame._overwrite_mode = False
    frame._insert_key_down = False
    frame._extend_selection_mode = False
    frame._extend_selection_anchor = None
    frame._document_tabs = [SimpleNamespace(editor=frame.editor, document=frame.document)]
    frame._active_tab_index = 0
    frame._abbreviation_expansion_guard = False
    frame._abbreviation_library = AbbreviationLibrary(version=2, abbreviations=[])
    frame._tab_inserts_literal = False
    frame._wx = SimpleNamespace(
        WXK_INSERT=45, WXK_F8=119, WXK_RETURN=13, WXK_NUMPAD_ENTER=370, WXK_TAB=9, WXK_ESCAPE=27
    )
    base = {
        "persistent_undo": False,
        "browse_mode_preload_cache": False,
        "status_bar_order": ["message"],
        "status_bar_hidden": [],
        "title_bar_path_mode": "name",
        "dirty_title_style": "text",
        "continue_lists_in_plain_text": False,
        "autocorrect_misspellings": False,
    }
    base.update(settings)
    frame.settings = SimpleNamespace(**base)
    frame.spoken = []
    frame.cues = []
    frame._announce = lambda message, **_k: frame.spoken.append(message)
    frame.cue_typing_assist = lambda kind: frame.cues.append(kind)
    frame._maybe_describe_key = lambda _event: False
    return frame


def _press_enter(frame: MainFrame) -> _Key:
    event = _Key(RETURN)
    frame._on_editor_char_hook(event)  # AutoCorrect sees Enter first...
    if event.skipped:
        event.skipped = False
        frame._on_editor_key_down(event)  # ...then list continuation
    return event


def _type_space(frame: MainFrame) -> _Key:
    event = _Key(SPACE)
    frame._on_editor_char_hook(event)
    if event.skipped:  # the control would type it
        frame.editor.WriteText(" ")
    return event


# -- Enter in a list -------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "after"),
    [("1. one", "1. one\n2. "), ("1) one", "1) one\n2) "), ("  - nested", "  - nested\n  - ")],
)
def test_enter_continues_a_markdown_list(text: str, after: str) -> None:
    frame = _frame(text)
    _press_enter(frame)
    assert frame.editor.GetValue() == after
    assert frame.editor.GetInsertionPoint() == len(after)
    assert frame._status_message == "Continued list item"


def test_enter_mid_item_splits_and_renumbers_as_one_undo_step() -> None:
    text = "1. bread milk\n2. eggs"
    frame = _frame(text, caret=len("1. bread"))
    _press_enter(frame)
    assert frame.editor.GetValue() == "1. bread\n2. milk\n3. eggs"
    assert frame._status_message == "Continued list item, renumbered 1 item below"
    frame.editor.Undo()
    assert frame.editor.GetValue() == text
    assert not frame.editor.CanUndo()


def test_enter_on_an_empty_item_ends_the_list() -> None:
    frame = _frame("1. one\n2. ")
    _press_enter(frame)
    assert frame.editor.GetValue() == "1. one\n"
    assert frame._status_message == "Exited list"


def test_plain_text_waits_for_the_setting() -> None:
    off = _frame("1. one", name="notes.txt")
    event = _press_enter(off)
    assert event.skipped  # the control's own new line
    assert off.editor.GetValue() == "1. one"

    on = _frame("1. one", name="notes.txt", continue_lists_in_plain_text=True)
    _press_enter(on)
    assert on.editor.GetValue() == "1. one\n2. "


def test_an_untitled_document_is_plain_text() -> None:
    frame = _frame("- a", name="", continue_lists_in_plain_text=True)
    _press_enter(frame)
    assert frame.editor.GetValue() == "- a\n- "


def test_code_and_configuration_are_never_continued() -> None:
    frame = _frame("1. step", name="build.py", continue_lists_in_plain_text=True)
    assert _press_enter(frame).skipped
    assert frame.editor.GetValue() == "1. step"


def test_rich_text_keeps_its_own_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame("- a", name="letter.rtf", continue_lists_in_plain_text=True)
    frame._current_editor_mode = lambda: "rich"
    assert _press_enter(frame).skipped
    assert frame.editor.GetValue() == "- a"


# -- AutoCorrect ----------------------------------------------------------------- #


def test_off_by_default() -> None:
    frame = _frame("I saw teh", name="notes.txt")
    _type_space(frame)
    assert frame.editor.GetValue() == "I saw teh "


def test_a_space_corrects_the_word_as_one_undo_step_and_says_so() -> None:
    frame = _frame("I saw teh", name="notes.txt", autocorrect_misspellings=True)
    event = _type_space(frame)
    assert not event.skipped  # the space went in with the correction
    assert frame.editor.GetValue() == "I saw the "
    assert frame.spoken[-1] == "Corrected to the"
    assert frame.cues == ["autocorrect"]
    frame.editor.Undo()
    assert frame.editor.GetValue() == "I saw teh"


def test_undo_then_space_keeps_the_typed_word_from_then_on() -> None:
    frame = _frame("Teh", name="notes.txt", autocorrect_misspellings=True)
    _type_space(frame)
    assert frame.editor.GetValue() == "The "
    frame.editor.Undo()
    _type_space(frame)
    assert frame.editor.GetValue() == "Teh "
    assert frame._status_message == "Kept Teh as you typed it"
    frame.editor.WriteText("and teh")
    _type_space(frame)
    assert frame.editor.GetValue() == "Teh and teh "  # declined for this window


def test_enter_corrects_and_then_continues_the_list() -> None:
    frame = _frame("- recieve", autocorrect_misspellings=True)
    _press_enter(frame)
    assert frame.editor.GetValue() == "- receive\n- "


def test_trailing_punctuation_stays_where_it_was() -> None:
    frame = _frame("(teh,", name="notes.txt", autocorrect_misspellings=True)
    _type_space(frame)
    assert frame.editor.GetValue() == "(the, "


@pytest.mark.parametrize(
    "text",
    ["see teh.example.com", "mail adress@example.com", "x `teh", "TEH", "```\nteh"],
)
def test_addresses_code_and_capitals_are_left_alone(text: str) -> None:
    frame = _frame(text, name="notes.md", autocorrect_misspellings=True)
    _type_space(frame)
    assert frame.editor.GetValue() == text + " "


@pytest.mark.parametrize("name", ["main.py", "settings.json", "config.yaml", "app.ini"])
def test_never_in_code_or_configuration(name: str) -> None:
    frame = _frame("teh", name=name, autocorrect_misspellings=True)
    _type_space(frame)
    assert frame.editor.GetValue() == "teh "


def test_your_own_entries_and_stopped_built_ins() -> None:
    frame = _frame("qill", name="notes.txt", autocorrect_misspellings=True)
    set_correction(frame._abbreviation_library, "qill", "QUILL")
    _type_space(frame)
    assert frame.editor.GetValue() == "QUILL "

    from quill.core.autocorrect import stop_correction

    frame = _frame("teh", name="notes.txt", autocorrect_misspellings=True)
    stop_correction(frame._abbreviation_library, "teh")
    _type_space(frame)
    assert frame.editor.GetValue() == "teh "


def test_autocorrect_entries_saves_through_the_abbreviation_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The window edits the library; the command writes it to abbreviations.json."""
    import quill.ui.autocorrect_entries_dialog as dialog_module
    from quill.core.abbreviations import load_abbreviation_library

    class _Dialog:
        def __init__(self, _parent, library, **_kwargs) -> None:
            self.dialog = object()
            self.changed = True
            set_correction(library, "qill", "QUILL")

        def close(self) -> None:
            return None

    monkeypatch.setattr(dialog_module, "AutocorrectEntriesDialog", _Dialog)
    frame = _frame("", name="notes.txt")
    shown: list[str] = []
    frame._show_modal_dialog = lambda _dialog, label: shown.append(label)
    frame.open_autocorrect_entries()
    assert shown == ["AutoCorrect Entries"]
    assert frame._status_message == "AutoCorrect entries saved"
    saved = load_abbreviation_library(tmp_path)
    assert [entry.abbreviation for entry in saved.abbreviations if entry.category] == ["qill"]


def test_the_command_is_registered_on_its_key() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["format.autocorrect_entries"] == "Alt+Shift+9"


def test_enter_with_word_prediction_open_is_left_to_the_prediction() -> None:
    frame = _frame("teh", name="notes.txt", autocorrect_misspellings=True)
    frame._intellisense_popup = SimpleNamespace(is_visible=lambda: True)
    assert frame._maybe_autocorrect_char(_Key(RETURN)) is False
    assert frame.editor.GetValue() == "teh"
