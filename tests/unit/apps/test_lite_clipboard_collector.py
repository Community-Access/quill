"""QUILL Lite's clipboard collector: QUILL's, on QUILL's key (QUILLVille, Dean Martineau).

Copy anywhere and it lands at the end of the collecting window; each distinct
copy once; nothing is saved; one window at a time.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.apps import lite_clipboard_collector as collector_mod
from quill.apps.lite_clipboard_collector import DocumentClipboardCollectorMixin
from quill.core.clipboard_collector import DEFAULT_DIVIDER


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
