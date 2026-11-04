"""The shared transport panel speaks of a file as a file and a book as a book.

One panel plays in QUILL, Quill Media Player and the WordPress player. A single
sound with no chapters used to load as "Loaded: 0 chapters, 0:03", end with
"End of book" and answer Where Am I with "... in the book". An audiobook with
chapters keeps every word it had.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.speech.chapters import Chapter  # noqa: E402
from quill.ui.audio_studio.player_panel import PlayerPanel  # noqa: E402


class _Engine:
    def __init__(self) -> None:
        self.at = 0

    def load(self, _path: str) -> bool:
        return True

    def position_ms(self) -> int:
        return self.at

    def is_playing(self) -> bool:
        return False

    def __getattr__(self, _name: str) -> Any:
        return lambda *_a, **_k: None


@pytest.fixture
def panel(wx_session_app):
    frame = wx.Frame(None)
    said: list[str] = []
    p = PlayerPanel(frame, announce=said.append)
    p._engine = _Engine()  # type: ignore[assignment]
    p.said = said  # type: ignore[attr-defined]
    try:
        yield p
    finally:
        p._timer.Stop()
        frame.Destroy()


def _book() -> list[Chapter]:
    return [
        Chapter(index=0, title="Opening", start_ms=0, end_ms=60_000),
        Chapter(index=1, title="Middle", start_ms=60_000, end_ms=120_000),
    ]


def test_a_single_file_loads_as_a_file(panel) -> None:
    panel.load("tone.wav", chapters=[])
    panel._on_engine_loaded(3_000)
    assert panel.said[-1] == "Loaded, 0:03"
    assert not any("chapters" in line for line in panel.said)


def test_a_single_file_ends_as_a_file(panel) -> None:
    panel.load("tone.wav", chapters=[])
    panel._on_engine_loaded(3_000)
    panel._on_engine_finished()
    assert panel.said[-1] == "End of file"


def test_where_am_i_in_a_single_file_says_the_file(panel) -> None:
    panel.load("tone.wav", chapters=[])
    panel._on_engine_loaded(3_000)
    panel._engine.at = 1_000
    panel._on_where_am_i()
    assert panel.said[-1] == "0:01 of 0:03 in the file, 0:02 remaining"


def test_an_audiobook_keeps_its_book_wording(panel) -> None:
    panel.load("book.m4b", chapters=_book())
    panel._on_engine_loaded(120_000)
    assert panel.said[-1] == "Loaded: 2 chapters, 2:00"
    panel._engine.at = 90_000
    panel._on_where_am_i()
    assert panel.said[-1].endswith("1:30 of 2:00 in the book, 0:30 remaining")
    assert panel.said[-1].startswith("Chapter 2 of 2: Middle")
    panel._on_engine_finished()
    assert panel.said[-1] == "End of book"
