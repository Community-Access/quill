r"""QUILL's Delete and Backspace keys make a sound, as QUILL Lite's now do.

Reported against QUILL Lite -- "the delete key does not play a sound, or I do not
hear one" -- and true of both editors for the same reason: the earcon lived in
the delete *command*, the command is the menu item, and the key goes straight
into the control. A capability the small product has and the editor does not is
exactly backwards, so both got it in the same change.
"""

from __future__ import annotations

import pytest

from quill.core.sound_events import SoundEvent
from quill.ui.main_frame_cues import CueMixin


class _Wx:
    WXK_DELETE = 127
    WXK_BACK = 8


class _Editor:
    def __init__(self, text: str, caret: int, *, editable: bool = True) -> None:
        self._text = text
        self._caret = caret
        self._editable = editable
        self.selection = (caret, caret)

    def IsEditable(self) -> bool:  # noqa: N802 - wx API shape
        return self._editable

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802 - wx API shape
        return self.selection

    def GetLastPosition(self) -> int:  # noqa: N802 - wx API shape
        return len(self._text)


class _Frame(CueMixin):
    def __init__(self, editor: _Editor) -> None:
        self._wx = _Wx()
        self.editor = editor
        self.cues: list[str] = []
        self.spoken: list[str] = []

    def cue(self, event: str) -> None:
        self.cues.append(event)

    def action(self, event: str, message: str) -> None:  # pragma: no cover - must not run
        self.spoken.append(message)


class _KeyEvent:
    def __init__(self, code: int) -> None:
        self._code = code

    def GetKeyCode(self) -> int:  # noqa: N802 - wx API shape
        return self._code


def _press(frame: _Frame, code: int) -> None:
    frame.cue_deletion_key(_KeyEvent(code))


def test_the_delete_key_sounds() -> None:
    frame = _Frame(_Editor("something to delete", 0))
    _press(frame, _Wx.WXK_DELETE)
    assert frame.cues == [SoundEvent.TEXT_DELETED]


def test_the_backspace_key_sounds() -> None:
    frame = _Frame(_Editor("something to delete", 4))
    frame.editor.selection = (4, 4)
    _press(frame, _Wx.WXK_BACK)
    assert frame.cues == [SoundEvent.TEXT_DELETED]


def test_a_selection_sounds_from_either_key() -> None:
    frame = _Frame(_Editor("something to delete", 0))
    frame.editor.selection = (0, 9)
    _press(frame, _Wx.WXK_BACK)
    assert frame.cues == [SoundEvent.TEXT_DELETED]


def test_delete_at_the_end_of_the_document_is_silent() -> None:
    """A tone claiming something went when nothing did is worse than none."""
    text = "all of it"
    frame = _Frame(_Editor(text, len(text)))
    frame.editor.selection = (len(text), len(text))
    _press(frame, _Wx.WXK_DELETE)
    assert frame.cues == []


def test_backspace_at_the_start_of_the_document_is_silent() -> None:
    frame = _Frame(_Editor("all of it", 0))
    _press(frame, _Wx.WXK_BACK)
    assert frame.cues == []


def test_a_read_only_document_is_silent() -> None:
    frame = _Frame(_Editor("locked", 0, editable=False))
    _press(frame, _Wx.WXK_DELETE)
    assert frame.cues == []


@pytest.mark.parametrize("code", [65, 13, 9])
def test_other_keys_are_left_alone(code: int) -> None:
    frame = _Frame(_Editor("something", 0))
    _press(frame, code)
    assert frame.cues == []


def test_nothing_is_spoken_for_a_keystroke() -> None:
    """GATE-13: the reader already says the character that went."""
    frame = _Frame(_Editor("something to delete", 0))
    _press(frame, _Wx.WXK_DELETE)
    assert frame.spoken == []


def test_an_editor_that_cannot_answer_is_silent_rather_than_fatal() -> None:
    """A cue must never be able to stop a key from deleting."""

    class _Broken:
        def IsEditable(self) -> bool:  # noqa: N802 - wx API shape
            raise RuntimeError("wrapped C/C++ object has been deleted")

    frame = _Frame(_Broken())  # type: ignore[arg-type]
    _press(frame, _Wx.WXK_DELETE)
    assert frame.cues == []
