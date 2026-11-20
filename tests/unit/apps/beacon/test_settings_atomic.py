"""Beacon's settings files survive a write that dies part-way through.

The family settings audit (2026-11-20) found Beacon writing its settings --
accessibility (``a11y.json``), the external player (``player_settings.json``),
routing rules (``routing.json``) and sync (``sync_config.json``) -- by opening
the real file for writing. That truncates it first, so a full disk or a crash
mid-write left an empty or half-written file, and the next launch quietly fell
back to defaults: every choice gone, with nothing said.

Each test saves a first choice, then makes a second save fail while the
destination file is being written (the moment a direct write has already
emptied it), and reloads as the next launch would: the first choice must
still be there. QUILL's atomic writer (temp file + ``os.replace``) never opens
the destination, so the old file stands until the new one is complete.
"""

from __future__ import annotations

import builtins
import errno
import io
import os
from pathlib import Path

import pytest


class _DiesMidWrite:
    """``open`` that empties the named file, then fails writing to it."""

    def __init__(self, real, target: Path) -> None:
        self.real = real
        self.target = target.resolve()

    def __call__(self, file, mode="r", *args, **kwargs):
        handle = self.real(file, mode, *args, **kwargs)
        try:
            same = Path(file).resolve() == self.target
        except (TypeError, OSError):
            same = False
        if same and "w" in mode:

            def die(*_a, **_k):
                raise OSError(errno.ENOSPC, "No space left on device")

            handle.write = die  # the file is already truncated by now
        return handle


def _break_writes_to(monkeypatch: pytest.MonkeyPatch, target: Path) -> None:
    """The disk fills up while *target* is being saved, however it is saved."""
    fault = _DiesMidWrite(builtins.open, target)
    monkeypatch.setattr(builtins, "open", fault)
    monkeypatch.setattr(io, "open", fault)
    real_fdopen = os.fdopen

    def fdopen(fd, mode="r", *args, **kwargs):  # the atomic writer's temp file
        handle = real_fdopen(fd, mode, *args, **kwargs)
        if "w" in mode:

            def die(*_a, **_k):
                raise OSError(errno.ENOSPC, "No space left on device")

            handle.write = die
        return handle

    monkeypatch.setattr(os, "fdopen", fdopen)


def test_accessibility_settings_survive_a_failed_save(tmp_path, monkeypatch) -> None:
    from quill.apps.beacon import a11y

    a11y.save(tmp_path, a11y.A11ySettings(high_contrast=True, scale_index=3))
    _break_writes_to(monkeypatch, a11y.settings_path(tmp_path))
    with pytest.raises(OSError):
        a11y.save(tmp_path, a11y.A11ySettings(high_contrast=False))
    monkeypatch.undo()
    reloaded = a11y.load(tmp_path)
    assert reloaded.high_contrast is True
    assert reloaded.scale_index == 3


def test_external_player_settings_survive_a_failed_save(tmp_path, monkeypatch) -> None:
    from quill.apps.beacon import external_player as ep

    first = ep.PlayerSettings(default_player="mpv", per_type={"radioStream": "vlc"})
    assert ep.save_settings(tmp_path, first) is True
    _break_writes_to(monkeypatch, tmp_path / ep.SETTINGS_FILE)
    assert ep.save_settings(tmp_path, ep.PlayerSettings(default_player="vlc")) is False
    monkeypatch.undo()
    reloaded = ep.load_settings(tmp_path)
    assert reloaded.default_player == "mpv"
    assert reloaded.per_type == {"radioStream": "vlc"}


def test_routing_rules_survive_a_failed_save(tmp_path, monkeypatch) -> None:
    from quill.apps.beacon import routing

    routing.save_rules(tmp_path, [routing.Rule("github.com", "Code")])
    _break_writes_to(monkeypatch, tmp_path / routing.SETTINGS_FILE)
    with pytest.raises(OSError):
        routing.save_rules(tmp_path, [routing.Rule("example.com", "Other")])
    monkeypatch.undo()
    assert [(r.keyword, r.collection) for r in routing.load_rules(tmp_path)] == [
        ("github.com", "Code")
    ]


def test_sync_settings_survive_a_failed_save(tmp_path, monkeypatch) -> None:
    from quill.apps.beacon.sync_ui import SyncConfig, SyncController

    controller = SyncController(None, tmp_path)
    controller.save_config(SyncConfig(transport="folder", folder="D:/Sync"))
    _break_writes_to(monkeypatch, controller.config_path)
    with pytest.raises(OSError):
        controller.save_config(SyncConfig(transport="off"))
    monkeypatch.undo()
    reloaded = SyncController(None, tmp_path).config
    assert (reloaded.transport, reloaded.folder) == ("folder", "D:/Sync")


def test_beacon_settings_are_written_by_the_shared_atomic_writer(tmp_path, monkeypatch) -> None:
    """Each save goes through ``write_json_atomic``, so it is atomic by construction."""
    from quill.apps.beacon import a11y, routing
    from quill.apps.beacon import external_player as ep
    from quill.apps.beacon.sync_ui import SyncConfig, SyncController
    from quill.core import storage

    written: list[str] = []
    real = storage.write_json_atomic

    def spy(path, data, *args, **kwargs):
        written.append(Path(path).name)
        return real(path, data, *args, **kwargs)

    monkeypatch.setattr(storage, "write_json_atomic", spy)
    a11y.save(tmp_path, a11y.A11ySettings())
    ep.save_settings(tmp_path, ep.PlayerSettings())
    routing.save_rules(tmp_path, [])
    SyncController(None, tmp_path).save_config(SyncConfig())
    assert written == [
        a11y.SETTINGS_NAME,
        ep.SETTINGS_FILE,
        routing.SETTINGS_FILE,
        "sync_config.json",
    ]
