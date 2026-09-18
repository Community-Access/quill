"""A lossy Save As asks first, and asks before it writes (bad.md F1, P2.11).

The Document Format switcher has warned since it shipped -- it names what will
not survive and lets you stop. Save As reaches the same conversion by another
door and said nothing at all, so the one path that writes a *file* was the
quiet one, and it announced what it had done only afterwards.

One direction is genuinely lossy and it is the one nobody notices until later:
a rich document saved to plain text or Markdown keeps its words and loses its
formatting, while the editing surface stays rich -- so nothing on screen or in
speech says the file on disk is now less than what is in front of you.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame


class _Wrapper:
    def __init__(self, rtf: bytes) -> None:
        self._rtf = rtf

    def get_rtf(self) -> bytes:
        return self._rtf


class _Host:
    """Just enough MainFrame to run the guard."""

    _FLATTENING_SUFFIXES = MainFrame._FLATTENING_SUFFIXES
    _confirm_lossy_save_as = MainFrame._confirm_lossy_save_as

    def __init__(self, *, mode: str, rtf: bytes | None = None, answer: bool = True) -> None:
        self._mode = mode
        self._wrapper = _Wrapper(rtf) if rtf is not None else None
        self._answer = answer
        self.asked: list[tuple[str, list[str]]] = []

    def _current_editor_mode(self) -> str:
        return self._mode

    def _active_richedit(self):
        return self._wrapper

    def _confirm_lossy_format_switch(self, label: str, features: list[str]) -> bool:
        self.asked.append((label, list(features)))
        return self._answer


BOLD_RTF = rb"{\rtf1\ansi {\b bold words} and plain ones}"


def test_a_rich_document_saved_as_text_is_asked_about() -> None:
    host = _Host(mode="rich", rtf=BOLD_RTF)
    assert host._confirm_lossy_save_as(Path("notes.txt")) is True
    assert host.asked and host.asked[0][0] == "plain text"


def test_the_question_names_markdown_when_that_is_the_target() -> None:
    host = _Host(mode="rich", rtf=BOLD_RTF)
    host._confirm_lossy_save_as(Path("notes.md"))
    assert host.asked[0][0] == "Markdown"


def test_declining_stops_the_save() -> None:
    host = _Host(mode="rich", rtf=BOLD_RTF, answer=False)
    assert host._confirm_lossy_save_as(Path("notes.md")) is False


def test_a_markup_document_is_not_asked_about() -> None:
    """Asterisks and hashes are characters, and they all survive."""
    host = _Host(mode="markup")
    assert host._confirm_lossy_save_as(Path("notes.txt")) is True
    assert host.asked == []


def test_saving_rich_as_rich_is_not_asked_about() -> None:
    host = _Host(mode="rich", rtf=BOLD_RTF)
    assert host._confirm_lossy_save_as(Path("notes.rtf")) is True
    assert host._confirm_lossy_save_as(Path("notes.docx")) is True
    assert host.asked == []


def test_converted_rich_is_asked_about_too() -> None:
    """No TOM to read an inventory from is not a reason to go quiet."""
    host = _Host(mode="rich_converted")
    assert host._confirm_lossy_save_as(Path("notes.txt")) is True
    assert host.asked[0][1] == ["formatting"]


def test_a_readback_failure_still_asks() -> None:
    class _Broken(_Wrapper):
        def get_rtf(self) -> bytes:
            raise RuntimeError("the TOM is gone")

    host = _Host(mode="rich", rtf=b"")
    host._wrapper = _Broken(b"")
    assert host._confirm_lossy_save_as(Path("notes.txt")) is True
    assert host.asked[0][1] == ["formatting"]


def test_the_guard_runs_before_the_write() -> None:
    import inspect

    source = inspect.getsource(MainFrame.save_file_as)
    guard = source.index("_confirm_lossy_save_as(target)")
    write = source.index("_write_document_to_disk(self.document, target)")
    assert guard < write, "the question must come before the file is written"
