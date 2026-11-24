"""QUILL's launch-check update waits for a quiet moment (FUX-15).

The automatic check used to download with spoken milestones and then open the
modal "Update downloaded" window whenever the download finished -- mid-sentence
in a dictation, over Read Aloud, or seconds after launch. Now its progress is
written and not spoken, and the window opens only at a quiet moment or when
the person asks (Help > Check for Updates).
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

import quill.core.updates as updates
from quill.core import maintenance_moment
from quill.ui import main_frame_updates, maintenance_moment_ui
from quill.ui.main_frame_updates import UpdatesMixin


class _Now:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def moment(monkeypatch):
    clock = _Now()
    later: list = []
    maintenance_moment_ui.reset_for_tests()
    maintenance_moment_ui._MOMENTS["quill"] = maintenance_moment.MaintenanceMoment(clock=clock)
    monkeypatch.setattr(maintenance_moment_ui, "_wx_later", lambda _ms, run: later.append(run))
    monkeypatch.setattr(maintenance_moment_ui, "window_in_front", lambda _w: True)
    monkeypatch.setattr(maintenance_moment_ui, "input_idle_seconds", lambda: None)
    yield SimpleNamespace(clock=clock, later=later)
    maintenance_moment_ui.reset_for_tests()


def _frame(tmp_path, monkeypatch):
    said: list[str] = []
    notes: list[str] = []
    status: list[str] = []
    offered: list[str] = []
    frame = UpdatesMixin.__new__(UpdatesMixin)
    frame._announce = lambda m, **k: said.append(m)  # type: ignore[method-assign]
    frame._set_status = lambda m: (status.append(m), said.append(m))  # type: ignore[method-assign]
    frame._set_status_quiet = status.append  # type: ignore[method-assign]
    frame._record_notification = lambda m, _k: notes.append(m)  # type: ignore[method-assign]
    frame._offer_post_download_actions = (  # type: ignore[method-assign]
        lambda release, _target: offered.append(release.version)
    )
    frame._wx = SimpleNamespace(CallAfter=lambda fn, *a, **k: fn(*a, **k))
    frame.frame = object()
    frame._live_dictation = None
    frame._read_aloud = SimpleNamespace(state="stopped")
    monkeypatch.setattr(main_frame_updates, "app_data_dir", lambda: tmp_path)

    def _download(_url, target, *, progress, expected_sha256=""):
        progress(0, 100)
        progress(50, 100)
        progress(100, 100)
        target.write_bytes(b"x")

    monkeypatch.setattr(updates, "download_release_asset", _download)

    class _Inline:
        def __init__(self, target, daemon=None):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(threading, "Thread", _Inline)
    release = SimpleNamespace(
        version="9.9.0",
        download_url="https://github.com/o/r/releases/download/v9.9.0/QUILL-Setup.exe",
        download_digest="",
    )
    return frame, release, SimpleNamespace(said=said, notes=notes, status=status, offered=offered)


def test_the_launch_download_is_written_not_spoken(tmp_path, monkeypatch, moment) -> None:
    frame, release, seen = _frame(tmp_path, monkeypatch)
    frame._download_update_release(release, automatic=True)
    assert seen.said == []
    assert "Downloaded update 9.9.0" in seen.status


def test_a_downloaded_update_waits_out_the_first_minute(tmp_path, monkeypatch, moment) -> None:
    frame, release, seen = _frame(tmp_path, monkeypatch)
    frame._download_update_release(release, automatic=True)
    assert seen.offered == []
    held = "Update 9.9.0 is ready and waits for a quiet moment."
    assert any(note.startswith(held) for note in seen.notes)
    moment.clock.now = 61.0
    moment.later.pop(0)()
    assert seen.offered == ["9.9.0"]
    assert seen.status[-1] == ""  # the "waits" line is gone once it opens


def test_it_never_opens_over_dictation_or_reading_aloud(tmp_path, monkeypatch, moment) -> None:
    frame, release, seen = _frame(tmp_path, monkeypatch)
    moment.clock.now = 100.0
    frame._read_aloud.state = "playing"
    frame._download_update_release(release, automatic=True)
    assert seen.offered == []
    assert any("waits until reading aloud stops" in note for note in seen.notes)
    frame._read_aloud.state = "stopped"
    frame._live_dictation = SimpleNamespace(is_busy=True)
    moment.later.pop(0)()
    assert seen.offered == []
    frame._live_dictation = None
    moment.clock.now = 110.0
    moment.later.pop(0)()  # dictation just ended: not yet
    assert seen.offered == []
    moment.clock.now = 130.0
    moment.later.pop(0)()
    assert seen.offered == ["9.9.0"]


def test_check_for_updates_opens_the_waiting_update_at_once(tmp_path, monkeypatch, moment) -> None:
    frame, release, seen = _frame(tmp_path, monkeypatch)
    frame._download_update_release(release, automatic=True)
    assert seen.offered == []
    frame.check_for_updates()
    assert seen.offered == ["9.9.0"]


def test_a_download_somebody_asked_for_is_unchanged(tmp_path, monkeypatch, moment) -> None:
    frame, release, seen = _frame(tmp_path, monkeypatch)
    frame._download_update_release(release)
    assert "Downloading update 9.9.0" in seen.said
    assert seen.offered == ["9.9.0"]


def test_launch_component_questions_wait_for_a_quiet_moment(moment) -> None:
    frame = UpdatesMixin.__new__(UpdatesMixin)
    asked: list[str] = []
    frame.frame = object()
    frame._live_dictation = None
    frame._read_aloud = None
    frame._maybe_prompt_braille_pack_install = lambda: asked.append("braille")
    frame._maybe_prompt_kokoro_package_install = lambda: asked.append("kokoro")
    frame._set_status_quiet = lambda _m: pytest.fail("a silent hold writes nothing")
    frame._record_notification = lambda *_a: pytest.fail("a silent hold records nothing")
    frame._braille_pack_prompt_when_quiet()
    frame._kokoro_package_prompt_when_quiet()
    assert asked == []
    moment.clock.now = 61.0
    moment.later.pop(0)()
    assert asked == ["braille"]  # one window at a time
    moment.later.pop(0)()
    assert asked == ["braille", "kokoro"]
