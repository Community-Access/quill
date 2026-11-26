"""Exiting QUILL Transcribe while a recording is being transcribed (FUX-05).

The Transcribe a Recording queue lives in memory. File > Exit, or closing the
window with close-to-tray off, used to end the transcription and every waiting
recording with no question and no word afterwards. Now the exit asks, naming
the recording and how many wait, and what is kept and what is not.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps import transcribe  # noqa: E402
from quill.apps.transcribe import QuillTranscribeFrame  # noqa: E402
from quill.ui import app_shell  # noqa: E402

RUNNING = "chapter3.wav, 40 percent done. 2 more recordings waiting."


def _frame(monkeypatch: pytest.MonkeyPatch, *, running: str, answer: int) -> Any:
    frame = object.__new__(QuillTranscribeFrame)
    frame._dictation = SimpleNamespace(held_count=0, held_on_disk=False)
    frame._exit_requested = False
    frame._settings = SimpleNamespace(close_to_tray=False)
    frame.asked = []
    frame.exited = []

    def box(message: str, *_a: Any, **_k: Any) -> int:
        frame.asked.append(message)
        return answer

    frame._show_message_box = box
    monkeypatch.setattr(QuillTranscribeFrame, "_transcribing", staticmethod(lambda: running))
    monkeypatch.setattr(
        app_shell.AppShellFrame, "_exit_application", lambda self: self.exited.append(True)
    )
    return frame


def test_exit_while_transcribing_asks_and_no_stays(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(monkeypatch, running=RUNNING, answer=wx.NO)
    frame._exit_application()
    assert frame.exited == []
    assert frame.asked == [transcribe.exit_transcribing_question(RUNNING)]
    question = frame.asked[0]
    assert question.startswith("Transcribing chapter3.wav, 40 percent done. 2 more")
    assert "finished stay in Notifications" in question
    assert "recordings themselves are not changed" in question


def test_exit_while_transcribing_after_yes_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(monkeypatch, running=RUNNING, answer=wx.YES)
    frame._exit_application()
    assert frame.exited == [True]


def test_nothing_running_exits_without_a_question(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(monkeypatch, running="", answer=wx.NO)
    frame._exit_application()
    assert frame.exited == [True] and frame.asked == []


def test_closing_the_window_while_transcribing_goes_through_the_question(
    monkeypatch: pytest.MonkeyPatch, wx_call_after: Any
) -> None:
    frame = _frame(monkeypatch, running=RUNNING, answer=wx.NO)
    later: list[Any] = []
    wx_call_after(lambda fn, *a: later.append(fn))

    class Close:
        vetoed = skipped = False

        def CanVeto(self) -> bool:  # noqa: N802 - wx API
            return True

        def Veto(self) -> None:  # noqa: N802 - wx API
            self.vetoed = True

        def Skip(self) -> None:  # noqa: N802 - wx API
            self.skipped = True

    event = Close()
    frame._on_close(event)
    assert event.vetoed and not event.skipped
    assert later == [frame._exit_application]
