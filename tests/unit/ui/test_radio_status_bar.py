"""Unit tests for the Radio status bar's pure text/navigation logic.

These drive ``RadioStatusBar`` with a fake host (no wx), exercising the cell
text functions and the clamp helper. The wx wiring (buttons, focus, context
menus) is covered by the app-level integration tests.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.radio.status_bar import RadioStatusBar, clamp_index


def _spec_text(bar: RadioStatusBar, key: str) -> str:
    spec = next(s for s in bar._specs if s.key == key)
    return spec.text()


def _host(**overrides: object) -> SimpleNamespace:
    """A minimal host with the attributes the cells read, overridable per test."""
    base: dict[str, object] = {
        "_wx": None,
        "_radio_status_text": lambda: "",
        "_radio_controller": SimpleNamespace(
            state=SimpleNamespace(volume_percent=100, muted=False)
        ),
        "_radio_recorder": SimpleNamespace(active_count=0),
        "_sleep_timer_controller": SimpleNamespace(is_active=False, remaining_seconds=0),
        "_radio_favorites": SimpleNamespace(favorites=[]),
        "_radio_history": SimpleNamespace(volume_boost=False),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_clamp_index_bounds() -> None:
    assert clamp_index(-3, 5) == 0
    assert clamp_index(9, 5) == 4
    assert clamp_index(2, 5) == 2
    # An empty bar clamps to 0 rather than raising.
    assert clamp_index(4, 0) == 0


def test_now_playing_falls_back_to_stopped() -> None:
    bar = RadioStatusBar(_host())
    assert _spec_text(bar, "now_playing") == "Stopped"

    playing = RadioStatusBar(_host(_radio_status_text=lambda: "Radio: playing Jazz"))
    assert _spec_text(playing, "now_playing") == "Radio: playing Jazz"


def test_volume_cell_reports_percent_mute_and_boost() -> None:
    assert _spec_text(RadioStatusBar(_host()), "volume") == "100%"

    muted = _host(
        _radio_controller=SimpleNamespace(state=SimpleNamespace(volume_percent=0, muted=True))
    )
    assert _spec_text(RadioStatusBar(muted), "volume") == "Muted"

    boosted = _host(_radio_history=SimpleNamespace(volume_boost=True))
    assert _spec_text(RadioStatusBar(boosted), "volume") == "100% (boosted)"


def test_recording_cell_counts_active_jobs() -> None:
    assert _spec_text(RadioStatusBar(_host()), "recording") == "Idle"
    one = _host(_radio_recorder=SimpleNamespace(active_count=1))
    assert _spec_text(RadioStatusBar(one), "recording") == "Recording"
    many = _host(_radio_recorder=SimpleNamespace(active_count=3))
    assert _spec_text(RadioStatusBar(many), "recording") == "3 recording"


def test_sleep_timer_cell_off_and_remaining() -> None:
    assert _spec_text(RadioStatusBar(_host()), "sleep_timer") == "Off"
    active = _host(
        _sleep_timer_controller=SimpleNamespace(is_active=True, remaining_seconds=90)
    )
    # 90 s rounds up to 2 minutes left.
    assert _spec_text(RadioStatusBar(active), "sleep_timer") == "2 min left"


def test_favorites_cell_pluralizes() -> None:
    assert _spec_text(RadioStatusBar(_host()), "favorites") == "0 stations"
    one = _host(_radio_favorites=SimpleNamespace(favorites=[object()]))
    assert _spec_text(RadioStatusBar(one), "favorites") == "1 station"
    three = _host(_radio_favorites=SimpleNamespace(favorites=[object(), object(), object()]))
    assert _spec_text(RadioStatusBar(three), "favorites") == "3 stations"
