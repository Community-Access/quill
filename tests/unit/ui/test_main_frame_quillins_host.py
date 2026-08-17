"""Regression tests for :class:`_EditorHostServices` (Quillin host adapter).

Two bugs live here, both on ``set_status``:

1. It once called ``self._frame._set_status_text(...)``, a method that has never
   existed on ``MainFrame`` (the real method is ``_set_status``), so any Quillin
   calling ``host.set_status(...)`` crashed with ``AttributeError``.
2. Fixed to ``_set_status``, it then *spoke* -- ``_set_status`` announces. A
   Quillin refreshing a status cell was hijacking the screen reader, which is
   how Status Scribe's word count reached a user who had its "speak count after
   save" preference switched off. ``set_status`` now routes to
   ``_set_status_quiet``; ``announce`` is the only way a Quillin speaks.

Both services also marshal onto the UI thread: Quillin event handlers run in
daemon threads (``main_frame_quillins._run_quillin_event_handler_async``) and
both frame methods repaint the status bar.
"""

from __future__ import annotations

from typing import Any

from quill.ui.main_frame_quillins_host import _EditorHostServices


class _FakeFrame:
    def __init__(self, wx: Any = None) -> None:
        self.status_messages: list[str] = []
        self.quiet_messages: list[str] = []
        self.announced: list[str] = []
        self._wx = wx

    def _set_status(self, message: str) -> None:
        self.status_messages.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.quiet_messages.append(message)

    def _announce(self, message: str) -> None:
        self.announced.append(message)


class _FakeWx:
    """Records ``CallAfter`` marshalling instead of needing a real event loop."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, tuple[Any, ...]]] = []

    def CallAfter(self, func: Any, *args: Any) -> None:  # noqa: N802 - wx spelling
        self.calls.append((func, args))
        func(*args)


def test_set_status_updates_the_bar_without_speaking() -> None:
    frame = _FakeFrame()
    host = _EditorHostServices(frame)

    host.set_status("3 matches found")

    assert frame.quiet_messages == ["3 matches found"]
    assert frame.status_messages == [], (
        "set_status must not reach _set_status, which announces -- a Quillin "
        "updating a status cell must not speak over the screen reader"
    )
    assert frame.announced == []


def test_set_status_falls_back_when_the_frame_has_no_quiet_variant() -> None:
    """Non-MainFrame hosts (standalone shells) have no ``_set_status_quiet``."""

    class _QuietlessFrame:
        def __init__(self) -> None:
            self.status_messages: list[str] = []

        def _set_status(self, message: str) -> None:
            self.status_messages.append(message)

    frame = _QuietlessFrame()
    host = _EditorHostServices(frame)

    host.set_status("3 matches found")

    assert frame.status_messages == ["3 matches found"]


def test_announce_still_speaks() -> None:
    frame = _FakeFrame()
    host = _EditorHostServices(frame)

    host.announce("Saved. 386 words.")

    assert frame.announced == ["Saved. 386 words."]


def test_ui_touching_services_marshal_onto_the_ui_thread() -> None:
    wx = _FakeWx()
    frame = _FakeFrame(wx=wx)
    host = _EditorHostServices(frame)

    host.set_status("counting")
    host.announce("done")

    assert [args for _func, args in wx.calls] == [("counting",), ("done",)], (
        "Quillin handlers run in daemon threads; both services repaint the "
        "status bar and must hop back through wx.CallAfter"
    )
    assert frame.quiet_messages == ["counting"]
    assert frame.announced == ["done"]
