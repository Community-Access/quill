"""QUILL Lite's clipboard collector: QUILL's, on QUILL's key (QUILLVille, Dean Martineau).

Copy anywhere and it lands at the end of the collecting window; each distinct
copy once; one window at a time. With ``clipboard_collector_saves`` (on by
default) a named document is saved quietly after each clip, with one sentence;
an untitled one is never saved and no window ever opens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.apps import lite_clipboard_collector as collector_mod
from quill.apps.lite_clipboard_collector import DocumentClipboardCollectorMixin
from quill.core.clipboard_collector import (
    COLLECTED,
    COLLECTED_AND_SAVED,
    DEFAULT_DIVIDER,
    collected_but_not_saved,
    disk_changed_reason,
    encoding_reason,
)


class _Control:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.editable = True

    def GetValue(self) -> str:
        return self.text

    def IsEditable(self) -> bool:
        return self.editable

    def SetSelection(self, start: int, end: int) -> None:
        self.sel = (start, end)

    def WriteText(self, text: str) -> None:
        start, end = self.sel
        self.text = self.text[:start] + text + self.text[end:]


class _Timer:
    def __init__(self) -> None:
        self.running = False

    def Start(self, _ms: int) -> None:
        self.running = True

    def Stop(self) -> None:
        self.running = False


class _App:
    pass


class _Window(DocumentClipboardCollectorMixin):
    clipboard = ""

    def __init__(self, app: _App, text: str = "") -> None:
        self.app = app
        self.control = _Control(text)
        self.said: list[str] = []
        self.modified = False
        self._collector_timer = _Timer()  # no wx: the watcher is driven by hand

    def _announce(self, text: str, **_kwargs: Any) -> None:
        self.said.append(text)

    def _clipboard_text(self) -> str:
        return _Window.clipboard

    def _set_modified(self, modified: bool) -> None:
        self.modified = modified


@pytest.fixture(autouse=True)
def _counter(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    from quill.ui import main_frame_clipboard_collector as quill_collector

    counter = [1]
    monkeypatch.setattr(quill_collector, "_clipboard_change_counter", lambda: counter[0])
    _Window.clipboard = ""
    return counter


def test_alt_shift_s_turns_it_on_and_off(_counter: list[int]) -> None:
    window = _Window(_App())
    window.cmd_clipboard_collector()
    assert window.collector_is_on()
    assert window._collector_timer.running
    assert window.said[-1].startswith("Clipboard collector on; anything you copy, in any program")
    window.cmd_clipboard_collector()
    assert not window.collector_is_on()
    assert window.said[-1] == "Clipboard collector off"


def test_a_copy_in_another_program_lands_at_the_end_and_nothing_is_saved(
    _counter: list[int],
) -> None:
    window = _Window(_App(), "notes")
    window.cmd_clipboard_collector()
    _Window.clipboard = "from the browser"
    _counter[0] = 2  # Windows counted a copy
    window._on_collector_tick()
    assert window.control.text == "notes" + DEFAULT_DIVIDER + "from the browser"
    assert window.modified is True  # marked changed, never written to disk
    assert window.said[-1] == "Collected clipboard text"


def test_a_tick_with_nothing_new_does_nothing(_counter: list[int]) -> None:
    window = _Window(_App(), "notes")
    window.cmd_clipboard_collector()
    _Window.clipboard = "already there"
    window._on_collector_tick()  # the counter has not moved
    assert window.control.text == "notes"


def test_each_distinct_copy_is_collected_once(_counter: list[int]) -> None:
    window = _Window(_App())
    window.cmd_clipboard_collector()
    _Window.clipboard = "same"
    for tick in (2, 3):
        _counter[0] = tick
        window._on_collector_tick()
    assert window.control.text == "same"


def test_one_window_at_a_time_and_it_says_it_moved(_counter: list[int]) -> None:
    app = _App()
    first, second = _Window(app), _Window(app)
    first.cmd_clipboard_collector()
    second.cmd_clipboard_collector()
    assert collector_mod.collecting_window(app) is second
    assert not first._collector_timer.running
    assert second.said[-1].startswith("Clipboard collector moved to this document")


def test_a_read_only_window_is_never_written(_counter: list[int]) -> None:
    window = _Window(_App(), "locked")
    window.control.editable = False
    window.cmd_clipboard_collector()
    _Window.clipboard = "text"
    _counter[0] = 2
    window._on_collector_tick()
    assert window.control.text == "locked"


# --------------------------------------------------------------------------- #
# clipboard_collector_saves (2026-10-15): QUILL's setting, on by default.
# The real window stub, so Save's own write and bookkeeping are what run, and
# every window Save could open is made to fail the test if it is reached.
# --------------------------------------------------------------------------- #


class _FakeWxTimer:
    def Start(self, _ms: int) -> None:
        pass

    def Stop(self) -> None:
        pass


def _no_windows(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("a copy made elsewhere must never open a window")


@pytest.fixture
def collecting(lite_window: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Factory: a real-mixin window, collecting, whose clipboard is ``clip[0]``."""
    from quill.apps import lite_window_file as filemod

    monkeypatch.setattr(filemod, "show_message_box", _no_windows)
    # Imported inside its caller, so patched where it is defined.
    monkeypatch.setattr("quill.ui.save_conflict_dialog.ask_save_conflict", _no_windows)

    def make(text: str, clip: list[str], path: Path | None = None) -> Any:
        win = lite_window(text, cursor=0)
        win.cmd_save_as = _no_windows
        win._collector_timer = _FakeWxTimer()  # no wx: the watcher is driven by hand
        win._clipboard_text = lambda: clip[0]
        win.path = path
        if path is not None:
            win._remember_disk_baseline()
        win.cmd_clipboard_collector()
        return win

    return make


def _copy(win: Any, counter: list[int], clip: list[str], text: str) -> None:
    clip[0] = text
    counter[0] += 1  # Windows counted a copy
    win._on_collector_tick()


def test_a_named_document_is_saved_after_every_clip_with_one_sentence(
    collecting: Any, _counter: list[int], tmp_path: Path
) -> None:
    clip = [""]
    target = tmp_path / "notes.txt"
    win = collecting("notes", clip, target)
    said = len(win.announcements)
    _copy(win, _counter, clip, "first")
    _copy(win, _counter, clip, "second")
    on_disk = target.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert on_disk == "notes" + DEFAULT_DIVIDER + "first" + DEFAULT_DIVIDER + "second"
    assert win.announcements[said:] == [COLLECTED_AND_SAVED, COLLECTED_AND_SAVED]
    assert win.modified is False


def test_an_untitled_document_collects_and_no_save_as_opens(
    collecting: Any, _counter: list[int]
) -> None:
    clip = [""]
    win = collecting("notes", clip)
    _copy(win, _counter, clip, "first")
    assert win.path is None
    assert win.modified is True
    assert win.announcements[-1] == COLLECTED


def test_the_setting_off_collects_without_saving(
    collecting: Any, _counter: list[int], tmp_path: Path
) -> None:
    clip = [""]
    target = tmp_path / "notes.txt"
    win = collecting("notes", clip, target)
    win.app.settings.clipboard_collector_saves = False
    _copy(win, _counter, clip, "first")
    assert not target.exists()
    assert win.modified is True
    assert win.announcements[-1] == COLLECTED


def test_a_failed_save_is_spoken_and_collecting_carries_on(
    collecting: Any, _counter: list[int], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps import lite_window_file as filemod

    clip = [""]
    target = tmp_path / "notes.txt"
    win = collecting("notes", clip, target)
    real_write = filemod.write_bytes_atomic

    def _full_disk(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(filemod, "write_bytes_atomic", _full_disk)
    _copy(win, _counter, clip, "first")
    assert win.announcements[-1].startswith("Collected, but not saved. Could not save notes.txt")
    assert win.modified is True
    assert win.collector_is_on()

    monkeypatch.setattr(filemod, "write_bytes_atomic", real_write)
    _copy(win, _counter, clip, "second")
    assert win.announcements[-1] == COLLECTED_AND_SAVED
    assert "second" in target.read_text(encoding="utf-8")


def test_characters_the_encoding_cannot_hold_are_said_not_asked(
    collecting: Any, _counter: list[int], tmp_path: Path
) -> None:
    clip = [""]
    target = tmp_path / "notes.txt"
    win = collecting("notes", clip, target)
    win.encoding = "cp1252"
    _copy(win, _counter, clip, "a tick ✓")
    assert not target.exists()
    assert win.announcements[-1] == collected_but_not_saved(encoding_reason("notes.txt", "cp1252"))


def test_a_file_another_program_changed_is_said_not_overwritten(
    collecting: Any, _counter: list[int], tmp_path: Path
) -> None:
    import os

    clip = [""]
    target = tmp_path / "notes.txt"
    target.write_text("notes", encoding="utf-8")
    os.utime(target, ns=(1_000_000_000, 1_000_000_000))
    win = collecting("notes", clip, target)
    target.write_text("rewritten elsewhere", encoding="utf-8")
    os.utime(target, ns=(2_000_000_000, 2_000_000_000))
    _copy(win, _counter, clip, "first")
    assert target.read_text(encoding="utf-8") == "rewritten elsewhere"
    assert win.announcements[-1] == collected_but_not_saved(disk_changed_reason("notes.txt"))
