"""The clipboard family, four ways it lied (bad.md P1.19: C3, C4, C5, C6).

C3 -- a label and a pin are two things a person told the tray, and every write
path went through one constructor that kept neither. Overwriting a pinned slot
also said nothing, which made the pin protection against exactly one operation
and decoration everywhere else.

C4 -- the collector called ``save_file()`` on every collected clip whenever the
document had a path, driven by a 750 ms poll, so copying anything in any
program wrote to disk and spoke twice. Its three refusals were silent, which is
how a working feature comes to look broken.

C5 -- the first press of a tray slot waited out the 400 ms multi-press window
before pasting, so a fast typist's next characters landed *before* the paste.
The module docstring said "Single press -- paste immediately" the whole time.

C6 -- the two editors documented opposite facts about ``Replace`` and undo.
``test_main_frame_undo_atomic.py`` settles it against real wx controls; these
tests check that both editors now go through the one mechanism that matches.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quill.core.copy_tray import CopyTray
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.main_frame_copy_tray import CopyTrayMixin
from quill.ui.main_frame_power_tools import PowerToolsActionsMixin

REPO = Path(__file__).resolve().parents[3]


# ----------------------------------------------------------------- C3


def test_editing_a_slot_keeps_its_name_and_its_pin(tmp_path: Path) -> None:
    tray = CopyTray(tmp_path)
    tray.copy_to(3, "first")
    tray.set_label(3, "address")
    tray.pin_slot(3)

    tray.copy_to(3, "second")

    slot = tray.slot(3)
    assert slot.text == "second"
    assert slot.label == "address"
    assert slot.pinned is True


class _TrayHost(CopyTrayMixin):
    """The surface the tray commands actually touch."""

    def __init__(self, tmp_path: Path, *, selection: tuple[int, int] = (0, 5)) -> None:
        self._copy_tray_instance = CopyTray(tmp_path)
        self.frame = None
        self.announced: list[str] = []
        self.status: list[str] = []
        self.editor = _FakeEditor("hello world", selection)

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.status.append(message)

    def _update_paste_tray_labels(self) -> None:
        pass

    def _refresh_statusbar(self) -> None:
        pass

    def _replace_document_text(self, text: str) -> None:
        self.editor.SetValue(text)

    document = None


class _FakeEditor:
    def __init__(self, text: str, selection: tuple[int, int]) -> None:
        self._text = text
        self._selection = selection

    def GetValue(self) -> str:
        return self._text

    def SetValue(self, text: str) -> None:
        self._text = text

    def GetSelection(self) -> tuple[int, int]:
        return self._selection

    def GetInsertionPoint(self) -> int:
        return self._selection[0]

    def SetInsertionPoint(self, position: int) -> None:
        self._selection = (position, position)

    def SetSelection(self, start: int, end: int) -> None:
        self._selection = (start, end)

    def WriteText(self, text: str) -> None:
        start, end = self._selection
        self._text = self._text[:start] + text + self._text[end:]
        self._selection = (start + len(text), start + len(text))


def test_overwriting_a_pinned_slot_says_it_was_pinned(tmp_path: Path) -> None:
    host = _TrayHost(tmp_path)
    host._tray().copy_to(4, "keep me")
    host._tray().pin_slot(4)

    host.copy_to_tray_slot_number(4)

    assert any("pinned" in line for line in host.announced), host.announced


def test_overwriting_an_unpinned_slot_says_nothing_about_pins(tmp_path: Path) -> None:
    host = _TrayHost(tmp_path)
    host._tray().copy_to(4, "ordinary")

    host.copy_to_tray_slot_number(4)

    assert not any("pinned" in line for line in host.announced), host.announced


def test_a_chooser_row_names_the_label_and_the_pin(tmp_path: Path) -> None:
    tray = CopyTray(tmp_path)
    tray.copy_to(2, "the quick brown fox")
    tray.set_label(2, "opener")
    tray.pin_slot(2)

    row = CopyTrayMixin._tray_choice_row(tray, 2)

    assert "opener" in row
    assert "pinned" in row
    assert CopyTrayMixin._tray_choice_row(tray, 1) == "Slot 1: empty"


# ----------------------------------------------------------------- C5


def test_the_first_press_pastes_before_the_window_closes(tmp_path: Path) -> None:
    """The whole bug: the paste used to happen 400 ms after the key."""
    host = _TrayHost(tmp_path, selection=(0, 0))
    host._tray().copy_to(1, "PASTED")
    host.editor = _FakeEditor("", (0, 0))
    host.document = _FakeDocument()
    import quill.ui.main_frame_copy_tray as module

    original = module.wx.CallLater
    module.wx.CallLater = lambda *args, **kwargs: _FakeTimer()
    try:
        host.paste_from_tray_slot(1)
    finally:
        module.wx.CallLater = original

    # Nothing has fired the timer, and the text is already in the document.
    assert host.editor.GetValue() == "PASTED"


def test_a_second_press_peeks_and_does_not_paste_again(tmp_path: Path) -> None:
    host = _TrayHost(tmp_path, selection=(0, 0))
    host._tray().copy_to(1, "PASTED")
    host.editor = _FakeEditor("", (0, 0))
    host.document = _FakeDocument()

    import quill.ui.main_frame_copy_tray as module

    original = module.wx.CallLater
    module.wx.CallLater = lambda *args, **kwargs: _FakeTimer()
    try:
        host.paste_from_tray_slot(1)
        host.paste_from_tray_slot(1)
        # The window closing must not paste a second time.
        host._fire_tray_action_with_count(1, 2)
    finally:
        module.wx.CallLater = original

    assert host.editor.GetValue() == "PASTED"
    assert any("PASTED" in line for line in host.announced), host.announced


class _FakeTimer:
    def Stop(self) -> None:
        pass


class _FakeDocument:
    def __init__(self) -> None:
        self.text = ""
        self.path = None

    def set_text(self, text: str) -> None:
        self.text = text


# ----------------------------------------------------------------- C4


class _CollectorHost(PowerToolsActionsMixin):
    def __init__(self, *, clip: str, read_only: bool = False, path: object = "x.txt") -> None:
        self._clip = clip
        self._read_only = read_only
        self.editor = _FakeEditor("", (0, 0))
        self.document = _FakeDocument()
        self.document.path = path
        self.status: list[str] = []
        self.saves = 0

    def _document_is_read_only(self) -> bool:
        return self._read_only

    def _power_tools_clipboard_text(self) -> str:
        return self._clip

    def _replace_document_text(self, text: str) -> None:
        self.editor.SetValue(text)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def save_file(self) -> None:  # pragma: no cover - must never be reached
        self.saves += 1


def test_collecting_does_not_write_the_file() -> None:
    host = _CollectorHost(clip="copied text")
    host.collect_clipboard_now()
    assert host.editor.GetValue() == "copied text"
    assert host.saves == 0
    assert host.status == ["Collected clipboard text"]


def test_an_asked_for_collection_says_why_it_refused() -> None:
    assert _refusal(_CollectorHost(clip="")) == 1
    assert _refusal(_CollectorHost(clip="text", read_only=True)) == 1

    repeat = _CollectorHost(clip="same")
    repeat.collect_clipboard_now()
    repeat.status.clear()
    repeat.collect_clipboard_now()
    assert len(repeat.status) == 1


def test_the_background_watcher_refuses_in_silence() -> None:
    host = _CollectorHost(clip="")
    host.collect_clipboard_now(announce_refusals=False)
    assert host.status == []


def _refusal(host: _CollectorHost) -> int:
    host.collect_clipboard_now()
    return len(host.status)


# ----------------------------------------------------------------- C6


def test_the_shared_helper_selects_and_writes_rather_than_replacing() -> None:
    editor = _FakeEditor("hello world", (0, 0))
    replace_as_one_undo(editor, 0, 5, "goodbye")
    assert editor.GetValue() == "goodbye world"


@pytest.mark.parametrize(
    "module_path",
    [
        "quill/ui/main_frame.py",
        "quill/ui/main_frame_rich_paragraph.py",
        "quill/apps/lite_window_clipboard.py",
        "quill/apps/lite_window_lines.py",
    ],
)
def test_the_four_one_undo_sites_import_the_one_mechanism(module_path: str) -> None:
    """Each of the four sites bad.md C6 named now shares one story."""
    source = (REPO / module_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "quill.ui.atomic_edit"
        and any(alias.name == "replace_as_one_undo" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert imported, f"{module_path} does not use the shared one-undo helper"
