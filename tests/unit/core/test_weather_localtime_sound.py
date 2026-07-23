"""Local-time-at-location rendering, its timezone plumbing, and the alert-sound
resolution/settings. Pure where possible; the sound player is exercised only for
its never-raise contract."""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.weather import open_meteo, render
from quill.core.weather import settings as settings_mod
from quill.core.weather.settings import WeatherSettings

# -- local time ---------------------------------------------------------------


def test_local_time_phrase_converts_to_zone() -> None:
    # 2023-04-27 13:51 UTC is 09:51 EDT (UTC-4); that day is a Thursday.
    now = datetime(2023, 4, 27, 13, 51, tzinfo=UTC)
    phrase = render.local_time_phrase(now, "America/New_York")
    assert phrase == "The local time there is Thursday, April 27, 9:51 AM."


def test_local_time_phrase_pm_and_other_zone() -> None:
    now = datetime(2023, 4, 27, 22, 5, tzinfo=UTC)  # 23:05 in Dublin (IST, +1)
    phrase = render.local_time_phrase(now, "Europe/Dublin")
    assert "11:05 PM" in phrase


def test_local_time_phrase_empty_when_no_zone_or_naive() -> None:
    now = datetime(2023, 4, 27, 13, 51, tzinfo=UTC)
    assert render.local_time_phrase(now, "") == ""
    assert render.local_time_phrase(datetime(2023, 4, 27, 13, 51), "America/New_York") == ""
    assert render.local_time_phrase(now, "Not/AZone") == ""


def test_open_meteo_report_carries_timezone(monkeypatch) -> None:
    from quill.core.weather.models import WeatherLocation

    payload = {
        "timezone": "America/Phoenix",
        "utc_offset_seconds": -25200,
        "current": {"temperature_2m": 90, "time": "2026-07-19T12:00"},
        "daily": {"time": ["2026-07-19"], "temperature_2m_max": [100]},
    }
    monkeypatch.setattr(open_meteo, "http_json", lambda url: payload)
    monkeypatch.setattr(open_meteo, "air_quality", lambda *a, **k: None)
    loc = WeatherLocation(display_name="Phoenix", latitude=33.45, longitude=-112.07)
    report = open_meteo.fetch_report(loc)
    assert report.time_zone == "America/Phoenix"


def test_local_time_setting_round_trips(tmp_path) -> None:
    s = WeatherSettings()
    s.show_local_time = False
    settings_mod.save_settings(tmp_path, s)
    assert settings_mod.load_settings(tmp_path).show_local_time is False


# -- alert sound --------------------------------------------------------------


def test_resolve_alert_sound_falls_back_to_bundled_default(tmp_path) -> None:
    from quill.platform import alert_sound

    # Empty -> bundled default (which must exist in the package).
    default = alert_sound.resolve_alert_sound("")
    assert default == alert_sound.bundled_alert_sound()
    assert default.is_file()
    # A non-existent custom path -> default, not the bogus path.
    assert alert_sound.resolve_alert_sound(str(tmp_path / "nope.wav")) == default


def test_resolve_alert_sound_uses_existing_custom(tmp_path) -> None:
    from quill.platform import alert_sound

    custom = tmp_path / "mine.wav"
    custom.write_bytes(b"RIFF....WAVE")  # contents irrelevant to resolution
    assert alert_sound.resolve_alert_sound(str(custom)) == custom


def test_play_alert_sound_never_raises(tmp_path) -> None:
    from quill.platform import alert_sound

    # Default path (real file) and a bogus custom path must both be safe.
    alert_sound.play_alert_sound("")
    alert_sound.play_alert_sound(str(tmp_path / "missing.wav"))


def test_alert_sound_settings_round_trip(tmp_path) -> None:
    s = WeatherSettings()
    s.alert_sound_enabled = False
    s.alert_sound_path = r"C:\sounds\siren.wav"
    s.alert_sound_repeat = 3
    settings_mod.save_settings(tmp_path, s)
    loaded = settings_mod.load_settings(tmp_path)
    assert loaded.alert_sound_enabled is False
    assert loaded.alert_sound_path == r"C:\sounds\siren.wav"
    assert loaded.alert_sound_repeat == 3


def test_alert_sound_repeat_clamped() -> None:
    s = WeatherSettings()
    s.alert_sound_repeat = 99
    s.normalized()
    assert s.alert_sound_repeat == 10
    s.alert_sound_repeat = 0
    s.normalized()
    assert s.alert_sound_repeat == 1


def test_play_alert_sound_repeat_never_raises() -> None:
    from quill.platform import alert_sound

    alert_sound.play_alert_sound("", repeat=3)  # default sound, 3x, must not raise
