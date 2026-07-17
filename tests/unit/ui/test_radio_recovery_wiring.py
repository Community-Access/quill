"""RadioMixin applies stream-recovery results correctly (issue #1065).

Drives _radio_apply_recovery against fakes (no wx) so the confident-play,
favorite-self-heal, and announce-only paths are verified headlessly.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.radio.models import RadioStation
from quill.core.radio.recovery import RecoveryResult
from quill.ui.main_frame_radio import RadioMixin


class _FakeFavorites:
    def __init__(self, favorite: Any = None) -> None:
        self._favorite = favorite
        self.found_key: str | None = None

    def find(self, key: str) -> Any:
        self.found_key = key
        return self._favorite


def _frame(favorite: Any = None) -> Any:
    frame = RadioMixin.__new__(RadioMixin)
    frame._announced: list[str] = []
    frame._announce = frame._announced.append
    frame._played: list[RadioStation] = []
    frame._radio_controller = SimpleNamespace(play_station=frame._played.append)
    frame._radio_favorites = _FakeFavorites(favorite)
    frame._saved: list[bool] = []
    frame._save_radio_favorites = lambda: frame._saved.append(True)
    return frame


def test_confident_result_plays_and_announces() -> None:
    frame = _frame()
    healed = RadioStation(name="Magic 104.1", stream_url="https://good/live", station_uuid="u1")
    frame._radio_apply_recovery(
        RecoveryResult(station=healed, message="Trying its current address.")
    )
    assert frame._played == [healed]
    assert frame._announced == ["Trying its current address."]


def test_confident_result_self_heals_a_saved_favorite() -> None:
    favorite = SimpleNamespace(station=None)
    frame = _frame(favorite)
    healed = RadioStation(name="Magic 104.1", stream_url="https://good/live", station_uuid="u1")
    frame._radio_apply_recovery(RecoveryResult(station=healed))
    assert favorite.station is healed
    assert frame._saved == [True]
    assert frame._radio_favorites.found_key == "u1"


def test_ambiguous_result_announces_without_playing() -> None:
    frame = _frame()
    frame._radio_apply_recovery(
        RecoveryResult(message="That stream isn't working. I found 2 possible streams...")
    )
    assert frame._played == []
    assert frame._announced == ["That stream isn't working. I found 2 possible streams..."]


def test_non_result_is_ignored() -> None:
    frame = _frame()
    frame._radio_apply_recovery(None)
    frame._radio_apply_recovery("not a result")
    assert frame._played == []
    assert frame._announced == []
