"""Tests for "one volume for all stations" (RadioHistory.use_global_volume).

The setting exists because a favorite's own remembered volume used to win
outright, so twenty favorites meant twenty places to turn the volume down. The
rules worth pinning: the shared level answers for every station while it is on,
per-station levels survive so turning it back off restores them, and clearing a
station's volume is not the same as setting it to zero.
"""

from pathlib import Path

from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.history import RadioHistory, load_history, save_history
from quill.core.radio.models import RadioStation


def _store_with(*favorites: FavoriteStation) -> RadioFavoritesStore:
    store = RadioFavoritesStore()
    store.favorites.extend(favorites)
    return store


def _fav(name: str, url: str, volume: int = -1) -> FavoriteStation:
    return FavoriteStation(station=RadioStation(name=name, stream_url=url), volume_percent=volume)


def test_use_global_volume_defaults_off_so_behaviour_is_unchanged() -> None:
    assert RadioHistory().use_global_volume is False


def test_use_global_volume_round_trips_through_disk(tmp_path: Path) -> None:
    history = RadioHistory()
    history.use_global_volume = True
    history.volume_percent = 42
    save_history(tmp_path, history)

    reloaded = load_history(tmp_path)
    assert reloaded.use_global_volume is True
    assert reloaded.volume_percent == 42


def test_a_store_written_before_the_setting_existed_loads_as_off(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text('{"volume_percent": 55}', encoding="utf-8")
    reloaded = load_history(tmp_path)
    assert reloaded.use_global_volume is False
    assert reloaded.volume_percent == 55


# -- clear_volume is not set_volume(-1) ---------------------------------------


def test_clear_volume_forgets_the_preference_rather_than_silencing() -> None:
    """set_volume clamps to 0-100, so -1 would mean *muted*, not *unset*."""
    favorite = _fav("Jazz FM", "https://x/1", volume=80)
    store = _store_with(favorite)

    assert store.clear_volume(favorite.key) is True
    assert favorite.volume_percent == -1


def test_set_volume_minus_one_really_does_clamp_to_zero() -> None:
    """The trap clear_volume exists to avoid, pinned so it cannot regress."""
    favorite = _fav("Jazz FM", "https://x/1", volume=80)
    store = _store_with(favorite)

    store.set_volume(favorite.key, -1)
    assert favorite.volume_percent == 0


def test_clear_volume_reports_an_unknown_station() -> None:
    assert _store_with().clear_volume("nope") is False


def test_clearing_one_station_leaves_the_others() -> None:
    keeper = _fav("Rock FM", "https://x/2", volume=30)
    target = _fav("Jazz FM", "https://x/1", volume=80)
    store = _store_with(target, keeper)

    store.clear_volume(target.key)

    assert target.volume_percent == -1
    assert keeper.volume_percent == 30
