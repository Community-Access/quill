"""A PDF's page break is never handed to a screen reader as a control character.

A PDF opens in both editors with a form feed (U+000C) between its pages, and
text near a page break reaches announcements -- a selection's first words, a
deleted line. These pin the three places that keep the character's *name* out
of what a listener hears (2026-10-17): the shared filter, the one engine every
announcement leaves through, and Character Details on the character itself.
"""

from __future__ import annotations

import types
from typing import Any

import pytest

from quill.core.char_describe import describe_character
from quill.core.speakable import speakable_controls
from quill.platform.windows.prism_bridge import AnnouncementEngine


def test_a_page_break_becomes_a_pause_and_other_controls_go() -> None:
    assert speakable_controls("end of page one\fStart of page two") == (
        "end of page one\nStart of page two"
    )
    assert speakable_controls("a\vb") == "a\nb"
    assert speakable_controls("bell\x07 and nul\x00 and del\x7f") == "bell and nul and del"
    # What a listener needs survives untouched.
    assert speakable_controls("tab\there\r\nnext line") == "tab\there\r\nnext line"
    assert speakable_controls("") == ""
    assert speakable_controls("café — naïve") == "café — naïve"


class _Backend:
    def __init__(self) -> None:
        self.features = types.SimpleNamespace(is_supported_at_runtime=True)
        self.name = "Fake Prism"
        self.messages: list[str] = []
        self.brailled: list[str] = []

    def speak(self, message: str, interrupt: bool = False) -> None:
        self.messages.append(message)


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> tuple[AnnouncementEngine, _Backend]:
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._ao2_live_screen_reader", lambda: (None, None, None)
    )
    backend = _Backend()
    context = types.SimpleNamespace(acquire_best=lambda: backend)
    prism = types.SimpleNamespace(Context=lambda: context)
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda name: prism if name == "prism" else None,
    )
    return AnnouncementEngine("auto"), backend


def test_every_announcement_leaves_without_a_control_character(engine: Any) -> None:
    announcer, backend = engine
    announcer.announce("Selected 2 lines. Begins: The end.\fChapter Two")
    assert backend.messages == ["Selected 2 lines. Begins: The end.\nChapter Two"]


def test_braille_gets_the_same_text(engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    announcer, _backend = engine
    written: list[str] = []
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.braille_via_prism",
        lambda _backend, message: written.append(message) or "",
    )
    announcer.braille("page one\fpage two")
    assert written == ["page one\npage two"]


def test_character_details_names_a_page_break_as_one() -> None:
    described = describe_character("one\ftwo", 3)
    assert "Page break" in described.summary
    assert "Unnamed character" not in described.summary
    assert "one page ends here and the next begins" in described.detail


def test_quill_lite_keeps_it_out_of_the_status_bar_too() -> None:
    """QUILL Lite's _announce writes the status cell JAWS reads with Insert+Page Down."""
    from quill.apps.lite_window import DocumentFrame

    spoken: list[str] = []
    shown: list[str] = []
    window = types.SimpleNamespace(
        app=types.SimpleNamespace(
            voice=types.SimpleNamespace(speak=lambda text, interrupt=True: spoken.append(text))
        ),
        _set_status_message=shown.append,
    )
    DocumentFrame._announce(window, "Deleted: last line\ffirst line")
    assert spoken == shown == ["Deleted: last line\nfirst line"]
