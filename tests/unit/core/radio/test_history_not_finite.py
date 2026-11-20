"""Quill Radio starts when its settings file holds ``Infinity`` or ``NaN``.

The family settings audit (2026-11-20): Python's JSON reader accepts
``Infinity``, ``-Infinity`` and ``NaN``, and ``load_history`` turned several
such numbers into ``int`` -- the volume, the search-source epoch, OptiLab's
auto-adapt -- which raises ``OverflowError``. Nothing catches it while Radio
is being built, so one hand-edited or damaged number kept Radio from opening.

The recovery is the family's (quill.core.settings_recovery): Radio starts,
every usable choice is kept, the unusable numbers take their defaults, the
file is copied aside before anything can save over it, and Radio says so
once its window is up.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from quill.core import settings_recovery
from quill.core.radio import history as radio_history  # imports its store
from quill.core.radio import history_store
from quill.core.radio.models import RadioStation


@pytest.fixture(autouse=True)
def _fresh_launch():
    settings_recovery._forget()
    yield
    settings_recovery._forget()


def _write(data_dir: Path, text: str) -> Path:
    path = data_dir / radio_history._FILE_NAME
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "field",
    ["volume_percent", "search_sources_epoch", "browse_sources_epoch", "optilab_auto_adapt"],
)
@pytest.mark.parametrize("number", ["Infinity", "-Infinity", "NaN"])
def test_a_number_that_is_not_finite_never_stops_radio_starting(
    tmp_path: Path, field: str, number: str
) -> None:
    extra = ', "browse_sources_enabled": {}' if field == "browse_sources_epoch" else ""
    _write(tmp_path, f'{{"resume_on_launch": true, "{field}": {number}{extra}}}')
    history = history_store.load_history(tmp_path)  # must not raise
    assert history.resume_on_launch is True  # the usable choice is kept


def test_unusable_numbers_take_their_defaults_and_the_file_is_kept_and_said(
    tmp_path: Path,
) -> None:
    station = RadioStation(name="Jazz", stream_url="https://radio.example.test/jazz")
    original = (
        '{"resume_on_launch": true, "skip_silence": true, "volume_percent": Infinity,'
        ' "optilab_auto_adapt": Infinity, "eq_bass_db": NaN, "eq_mid_db": 3.0,'
        ' "eq_treble_db": -Infinity, "recording_speed": Infinity, "ui_font_scale": NaN,'
        f' "stations": [{json.dumps(station.to_dict())}]}}'
    )
    path = _write(tmp_path, original)

    history = history_store.load_history(tmp_path)

    # Usable choices are kept...
    assert history.resume_on_launch is True and history.skip_silence is True
    assert history.eq_mid_db == 3.0
    assert [s.name for s in history.stations] == ["Jazz"]
    # ...and the unusable ones take their defaults, never a non-finite value.
    assert history.volume_percent == -1
    assert history.optilab_auto_adapt == 0
    for value in (
        history.eq_bass_db,
        history.eq_treble_db,
        history.recording_speed,
        history.ui_font_scale,
    ):
        assert math.isfinite(value)
    assert history.recording_speed == 1.0 and history.ui_font_scale == 1.0

    # The file is copied aside, byte for byte, before anything saves over it.
    copies = list(tmp_path.glob("*.damaged-*"))
    assert len(copies) == 1
    assert copies[0].read_text(encoding="utf-8") == original
    assert path.read_text(encoding="utf-8") == original
    # Radio says so once its window is up, naming the copy.
    notice = settings_recovery.take_notice("Quill Radio")
    assert copies[0].name in notice
    assert settings_recovery.take_notice("Quill Radio") == ""  # once


def test_a_clean_file_is_not_called_damaged(tmp_path: Path) -> None:
    _write(tmp_path, '{"resume_on_launch": true, "volume_percent": 40}')
    assert history_store.load_history(tmp_path).volume_percent == 40
    assert list(tmp_path.glob("*.damaged-*")) == []
    assert settings_recovery.take_notice("Quill Radio") == ""


def test_saving_after_recovery_writes_only_finite_numbers(tmp_path: Path) -> None:
    """Reload from disk after the next save: the file is valid JSON again."""
    _write(tmp_path, '{"resume_on_launch": true, "eq_bass_db": Infinity}')
    history = history_store.load_history(tmp_path)
    history_store.save_history(tmp_path, history)
    text = (tmp_path / radio_history._FILE_NAME).read_text(encoding="utf-8")
    assert "Infinity" not in text and "NaN" not in text
    assert history_store.load_history(tmp_path).resume_on_launch is True


def test_radio_says_so_once_its_window_is_up(tmp_path: Path, monkeypatch) -> None:
    """The person's view: Radio opens, then says once that the file was kept."""
    from types import SimpleNamespace

    from quill.apps import radio_launch_tasks, radio_podcast_refresh
    from quill.ui.radio import calendar_wiring

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    _write(tmp_path, '{"resume_on_launch": true, "volume_percent": Infinity}')
    history = history_store.load_history(tmp_path)  # Radio's main() reads it first
    said: list[str] = []
    host = SimpleNamespace(_radio_history=history, _announce=said.append)
    host._save_radio_history = lambda: None
    deferred: list = []
    fake_wx = SimpleNamespace(CallAfter=lambda fn, *a, **k: deferred.append((fn, a, k)))
    monkeypatch.setattr(calendar_wiring, "install_reminders", lambda *_a: None)
    monkeypatch.setattr(radio_podcast_refresh, "install", lambda *_a, **_k: None)
    monkeypatch.setattr("sys.argv", ["quill-radio"])
    radio_launch_tasks.schedule(host, fake_wx, safe_mode=True)

    notices = [args for fn, args, _k in deferred if fn == said.append]
    assert len(notices) == 1
    assert "Quill Radio" in notices[0][0] and ".damaged-" in notices[0][0]
