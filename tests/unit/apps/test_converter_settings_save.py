"""Quill Converter: a choice that could not be saved is said, with a Retry.

plan.md (settings review): ``converter_settings.save`` caught ``OSError`` and
did nothing, so a locked or read-only ``converter.json`` produced no
persistence outcome at all. The choice worked for the session and was gone
after a restart, with nothing said. These drive the real window.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.machine_global  # a real Converter window: tray icon and hotkey


@pytest.fixture()
def converter(wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from quill.apps import converter as app
    from quill.core import converter_settings

    monkeypatch.setattr(
        converter_settings, "settings_path", lambda _d=None: tmp_path / "converter.json"
    )
    monkeypatch.setattr(app, "_find_ffmpeg", lambda: None)
    frame = app.QuillConverterFrame()
    said: list[str] = []
    monkeypatch.setattr(frame, "_announce", lambda text, **_k: said.append(text))
    frame.said = said
    yield frame
    frame._ipc_timer.Stop()
    frame._remove_tray_icon()
    frame.frame.Destroy()
    wx_app.Yield()


@pytest.fixture()
def outcomes():
    from quill.core import persistence_outcome

    heard: list = []
    stop = persistence_outcome.subscribe(heard.append)
    yield heard
    stop()


def _on_disk(tmp_path: Path):
    from quill.core import converter_settings

    raw = json.loads((tmp_path / "converter.json").read_text(encoding="utf-8"))
    return converter_settings.ConverterSettings.from_json(raw)


def test_a_locked_settings_file_is_reported_with_a_retry_and_never_claimed(
    converter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcomes
) -> None:
    from quill.core import storage

    real_write = storage.write_json_atomic

    def locked(*_a, **_k):
        raise PermissionError(13, "locked")

    monkeypatch.setattr(storage, "write_json_atomic", locked)
    converter._effect.SetSelection(converter._effect_ids.index("night"))
    converter._on_choice_changed(type("E", (), {"Skip": lambda self: None})())
    failed = [o for o in outcomes if not o.ok]
    assert failed, "the failure reached nobody"
    assert "Converter" in failed[-1].what and failed[-1].retry is not None
    assert not any("saved" in text.lower() for text in converter.said)
    assert converter._effect_ids[converter._effect.GetSelection()] == "night"  # still in use
    # The listener changes another choice; then the disk comes back and Retry runs.
    converter._dest.SetValue(str(tmp_path / "out"))
    monkeypatch.setattr(storage, "write_json_atomic", real_write)
    converter._remember()  # the next change saves everything current
    failed[-1].retry()  # and a late Retry still writes what is current
    saved = _on_disk(tmp_path)
    assert saved.effect == "night" and saved.dest_dir == str(tmp_path / "out")


def test_save_says_whether_it_worked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import converter_settings, storage

    settings = converter_settings.ConverterSettings(effect="night")
    assert converter_settings.save(settings, tmp_path) is True
    monkeypatch.setattr(
        storage, "write_json_atomic", lambda *_a, **_k: (_ for _ in ()).throw(OSError(28, "full"))
    )
    assert converter_settings.save(settings, tmp_path) is False
