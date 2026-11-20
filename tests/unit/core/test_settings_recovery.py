"""Malformed settings: kept, explained, never a failed launch.

plan.md (settings review): readable JSON with unusable values escaped the
loaders -- Inkwell's ``schema_version="invalid"`` raised ``ValueError`` and
Weather's ``refresh_minutes: 1e309`` raised ``OverflowError`` -- and both apps
call their loader while the window is being built. Each test writes the file
the review used into a temporary data folder and loads it the way the app
does, then saves and reloads as the next launch would.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import settings_recovery


@pytest.fixture(autouse=True)
def _fresh_launch():
    settings_recovery._forget()
    yield
    settings_recovery._forget()


def _damaged_copies(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.damaged-*"))


# -- Inkwell ------------------------------------------------------------------------ #


def test_inkwell_with_an_unreadable_schema_version_starts_keeps_the_file_and_says_so(
    tmp_path: Path,
) -> None:
    from quill.core.expansion import settings as inkwell

    raw = {"schema_version": "invalid", "announce_expansions": True, "injection_mode": "paste"}
    path = inkwell.settings_path(tmp_path)
    path.write_text(json.dumps(raw), encoding="utf-8")
    loaded = inkwell.load_settings(tmp_path)  # raised ValueError
    assert loaded.announce_expansions is True  # what could be read was kept
    assert loaded.injection_mode == "paste"
    assert not loaded.read_only  # a damaged version is not a newer build
    copies = _damaged_copies(tmp_path)
    assert len(copies) == 1 and json.loads(copies[0].read_text(encoding="utf-8")) == raw
    notice = settings_recovery.take_notice("Quill Inkwell")
    assert copies[0].name in notice and "defaults" in notice
    assert settings_recovery.take_notice("Quill Inkwell") == ""  # said once
    # The next save writes a good file; the copy stays; the next launch is quiet.
    inkwell.save_settings(tmp_path, loaded)
    again = inkwell.load_settings(tmp_path)
    assert again.announce_expansions is True
    assert _damaged_copies(tmp_path) == copies
    assert settings_recovery.take_notice("Quill Inkwell") == ""


@pytest.mark.parametrize(
    "raw",
    [
        {"schema_version": 1e309},
        {"schema_version": [1]},
        {"schema_version": {"v": 1}},
        {"schema_version": "2"},
    ],
)
def test_inkwell_survives_any_schema_version(tmp_path: Path, raw: dict) -> None:
    from quill.core.expansion import settings as inkwell

    inkwell.settings_path(tmp_path).write_text(json.dumps(raw), encoding="utf-8")
    loaded = inkwell.load_settings(tmp_path)
    assert isinstance(loaded, inkwell.InkwellSettings)


def test_a_newer_inkwell_file_is_still_read_only_not_damaged(tmp_path: Path) -> None:
    from quill.core.expansion import settings as inkwell

    inkwell.settings_path(tmp_path).write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    assert inkwell.load_settings(tmp_path).read_only is True
    assert _damaged_copies(tmp_path) == []


# -- Weather ------------------------------------------------------------------------ #


def test_weather_with_an_infinite_refresh_keeps_the_rest_the_file_and_says_so(
    tmp_path: Path,
) -> None:
    from quill.core.weather import settings as weather

    path = tmp_path / "weather_settings.json"
    path.write_text(
        '{"refresh_minutes": 1e309, "temperature_unit": "C", "hourly_hours": NaN}',
        encoding="utf-8",
    )
    loaded = weather.load_settings(tmp_path)  # raised OverflowError
    assert loaded.temperature_unit == "C"
    assert loaded.refresh_minutes == weather.WeatherSettings().refresh_minutes
    assert loaded.hourly_hours == weather.WeatherSettings().hourly_hours
    assert len(_damaged_copies(tmp_path)) == 1
    weather.load_settings(tmp_path)  # read again elsewhere: no second copy
    assert len(_damaged_copies(tmp_path)) == 1
    assert "Quill Weather" in settings_recovery.take_notice("Quill Weather")
    weather.save_settings(tmp_path, loaded)
    assert weather.load_settings(tmp_path).temperature_unit == "C"


def test_weather_with_ordinary_settings_says_nothing(tmp_path: Path) -> None:
    from quill.core.weather import settings as weather

    weather.save_settings(tmp_path, weather.WeatherSettings(refresh_minutes=30))
    assert weather.load_settings(tmp_path).refresh_minutes == 30
    assert _damaged_copies(tmp_path) == []
    assert settings_recovery.take_notice("Quill Weather") == ""


def test_a_copy_that_cannot_be_made_is_still_explained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "x.json"
    path.write_text("{}", encoding="utf-8")

    def refuse(self, data):
        raise PermissionError("read-only")

    monkeypatch.setattr(Path, "write_bytes", refuse)
    assert settings_recovery.keep_damaged(path, app="Quill Weather") is None
    assert "was left in" in settings_recovery.take_notice("Quill Weather")
