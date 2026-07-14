"""Regression test for :class:`_EditorHostServices` (Quillin host adapter).

``set_status`` previously called ``self._frame._set_status_text(...)``, a
method that has never existed on ``MainFrame`` (the real method is
``_set_status``). Any Quillin calling ``host.set_status(...)`` crashed with
``AttributeError: 'MainFrame' object has no attribute '_set_status_text'``.
"""

from __future__ import annotations

from quill.ui.main_frame_quillins_host import _EditorHostServices


class _FakeFrame:
    def __init__(self) -> None:
        self.status_messages: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status_messages.append(message)


def test_set_status_forwards_to_frame_set_status() -> None:
    frame = _FakeFrame()
    host = _EditorHostServices(frame)

    host.set_status("3 matches found")

    assert frame.status_messages == ["3 matches found"]
