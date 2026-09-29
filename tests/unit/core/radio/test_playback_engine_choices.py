"""The Playback engine dropdown only offers what is installed (2026-09-29)."""

from __future__ import annotations

from quill.core.radio.playback_engine_choices import engine_choices


def test_with_mpv_all_three_rows_and_automatic_says_mpv() -> None:
    labels, values, index = engine_choices("auto", mpv_present=True)
    assert values == ["auto", "wx", "mpv"]
    assert labels[0] == "Automatic (recommended, uses mpv)"
    assert index == 0
    assert engine_choices("mpv", mpv_present=True)[2] == 2


def test_without_mpv_no_mpv_row_and_automatic_says_windows_media() -> None:
    labels, values, index = engine_choices("auto", mpv_present=False)
    assert values == ["auto", "wx"]
    assert labels == [
        "Automatic (uses Windows Media; mpv is not installed)",
        "Windows Media (classic)",
    ]
    assert index == 0


def test_a_saved_mpv_preference_lands_on_automatic_when_mpv_is_gone() -> None:
    _labels, _values, index = engine_choices("mpv", mpv_present=False)
    assert index == 0  # what it resolves to, not a row for an absent engine


def test_windows_media_stays_selected_either_way() -> None:
    assert engine_choices("wx", mpv_present=True)[2] == 1
    assert engine_choices("wx", mpv_present=False)[2] == 1
    assert engine_choices("", mpv_present=False)[2] == 0
