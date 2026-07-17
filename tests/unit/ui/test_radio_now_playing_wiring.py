"""What's Playing (Ctrl+T) renders through the configurable template (#1068).

Drives RadioMixin's announce path against a fake history/announce so the raw
broadcast metadata -> clean spoken phrase wiring is verified headlessly.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.main_frame_radio import RadioMixin

_REPORTED = 'title="YOUR SONG",artist="Elton John",url="song_spot="F" MediaBaseId="0"'


def _frame(template: str = "{title}[ by {artist}]") -> Any:
    frame = RadioMixin.__new__(RadioMixin)
    frame._radio_history = SimpleNamespace(
        now_playing_template=template, announce_track_titles=True
    )
    frame._radio_track_title = ""
    announced: list[str] = []
    frame._announce = announced.append
    frame._announced = announced  # type: ignore[attr-defined]
    return frame


def test_whats_playing_cleans_up_broadcast_metadata() -> None:
    frame = _frame()
    frame._radio_track_title = _REPORTED
    frame.radio_whats_playing()
    assert frame._announced == ["Now playing: YOUR SONG by Elton John"]


def test_track_change_uses_the_clean_phrase() -> None:
    frame = _frame()
    frame._radio_apply_track_title(_REPORTED, announce_result=False)
    assert frame._announced == ["Now playing: YOUR SONG by Elton John"]


def test_custom_template_is_honored() -> None:
    frame = _frame(template="{artist} -- {title}")
    frame._radio_track_title = _REPORTED
    frame.radio_whats_playing()
    assert frame._announced == ["Now playing: Elton John -- YOUR SONG"]


def test_missing_template_falls_back_to_the_default() -> None:
    frame = _frame(template="")
    frame._radio_track_title = "Elton John - Your Song"
    frame.radio_whats_playing()
    assert frame._announced == ["Now playing: Your Song by Elton John"]
