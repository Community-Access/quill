"""FUX-16 in QUILL Lite: a failed open or save is a next step, not an OK box.

Both were "Could not open notes.txt." followed by the exception's text, with
OK only; a failed save never said the text was still there. Now the sentence
is plain and says what was kept, the default button is Retry, Choose Another
File or Save As, and the error is behind Copy Details.
"""

from __future__ import annotations

import errno
from pathlib import Path
from typing import Any

import pytest

from quill.apps import lite_window_failures as lwf


class _Window:
    def __init__(self) -> None:
        self.opened = 0
        self.saved_as = 0
        self.cues = 0

    def cmd_open(self) -> None:
        self.opened += 1

    def cmd_save_as(self) -> None:
        self.saved_as += 1

    def _cue_error(self) -> None:
        self.cues += 1

    def _announce(self, _text: str) -> None:
        pass


def _answer(monkeypatch: pytest.MonkeyPatch, chosen: bool) -> list[tuple[str, dict[str, Any]]]:
    import quill.ui.next_step_box as box

    asked: list[tuple[str, dict[str, Any]]] = []

    def show(_parent: Any, message: str, _caption: str, **kwargs: Any) -> bool:
        asked.append((message, kwargs))
        return chosen

    monkeypatch.setattr(box, "show_next_step", show)
    return asked


def test_a_locked_file_offers_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _answer(monkeypatch, True)
    window = _Window()
    retried: list[int] = []
    error = PermissionError(errno.EACCES, "Permission denied", "C:/notes.txt")
    assert lwf.report_open_failure(
        window, Path("C:/notes.txt"), error, retry=lambda: retried.append(1)
    )
    message, kwargs = asked[0]
    assert message.startswith("Could not open notes.txt.")
    assert "another program" in message
    assert "Errno" not in message
    assert "PermissionError" in kwargs["details"]
    assert kwargs["next_label"] == "&Retry"
    assert retried == [1]
    assert window.cues == 1


def test_without_a_retry_it_offers_choose_another_file(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _answer(monkeypatch, True)
    window = _Window()
    lwf.report_open_failure(window, Path("C:/notes.txt"), OSError(errno.EIO, "I/O"))
    assert asked[0][1]["next_label"] == "Choose Another &File..."
    assert window.opened == 1


def test_a_failed_save_says_the_text_is_kept_and_offers_save_as(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = _answer(monkeypatch, True)
    window = _Window()
    lwf.report_save_failure(window, Path("C:/notes.txt"), OSError(errno.ENOSPC, "No space"))
    message, kwargs = asked[0]
    assert "The disk is full." in message
    assert "your text is still open and unsaved" in message
    assert "QUILL Lite" in message
    assert kwargs["next_label"] == "Save &As..."
    assert window.saved_as == 1


def test_close_on_a_failed_save_does_nothing_else(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, False)
    window = _Window()
    assert not lwf.report_save_failure(window, Path("C:/notes.txt"), RuntimeError("boom"))
    assert window.saved_as == 0


def test_rich_text_unavailable_keeps_its_authored_words(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui.richedit_rtf_surface import RichEditRtfError

    asked = _answer(monkeypatch, False)
    error = RichEditRtfError("Rich text needs the Windows Rich Edit control.")
    lwf.report_open_failure(_Window(), Path("C:/a.rtf"), error)
    assert "Rich text needs the Windows Rich Edit control." in asked[0][0]
