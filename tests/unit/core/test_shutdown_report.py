"""A failed final write while closing is kept and said once (qc.md F-06).

Radio and Cast guard every teardown step so close always completes -- and that
used to make a failed library save, stats save or recording-marker clear look
exactly like success. These pin the report: close still completes, a
must-record failure is kept (a pending sentence and a Recent Problems row),
best-effort failures are only logged, nothing persisted carries exception text,
and the next launch reads the sentence once.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from quill.core import problem_log, shutdown_report
from quill.core.shutdown_report import BACKGROUND, BEST_EFFORT, MUST_RECORD, ShutdownReport


def _boom(message: str = "C:/Users/someone/private/path.json is locked"):
    def action() -> None:
        raise OSError(message)

    return action


def test_every_step_runs_even_after_a_failure_and_none_raises() -> None:
    ran: list[str] = []
    report = ShutdownReport("cast", "QUILL Cast")
    assert report.step("a", MUST_RECORD, _boom()) is False
    assert report.step("b", BEST_EFFORT, lambda: ran.append("b")) is True
    assert report.step("c", BACKGROUND, _boom()) is False
    assert report.step("d", BEST_EFFORT, None) is True  # an absent subsystem
    assert ran == ["b"]
    assert [f.step for f in report.failures] == ["a", "c"]


def test_only_must_record_failures_make_a_sentence() -> None:
    report = ShutdownReport("radio", "Quill Radio")
    report.step("tray", BEST_EFFORT, _boom())
    report.step("tasks", BACKGROUND, _boom())
    assert report.sentence() == ""
    report.step("recording_marker", MUST_RECORD, _boom())
    said = report.sentence()
    assert said.startswith("Last time Quill Radio closed, it could not clear the note")
    assert "Recent Problems" in said


def test_two_failed_writes_are_named_together() -> None:
    report = ShutdownReport("cast", "QUILL Cast")
    report.step("listening_stats", MUST_RECORD, _boom())
    report.step("podcast_library", MUST_RECORD, _boom())
    said = report.sentence()
    assert "save your listening statistics or save your podcast library" in said


def test_persist_keeps_a_pending_sentence_and_a_problem_row_without_exception_text(
    tmp_path: Path,
) -> None:
    report = ShutdownReport("cast", "QUILL Cast")
    report.step("podcast_library", MUST_RECORD, _boom())
    report.persist(tmp_path)
    pending = json.loads(shutdown_report.pending_path(tmp_path, "cast").read_text("utf-8"))
    assert pending["steps"] == ["podcast_library"]
    problems = problem_log.load_problems(tmp_path)
    assert len(problems) == 1
    assert problems[0].kind == problem_log.KIND_SHUTDOWN
    assert problems[0].target.startswith("cast")
    persisted = json.dumps(pending) + json.dumps([p.to_dict() for p in problems])
    assert "private" not in persisted and "locked" not in persisted
    assert "OSError" not in persisted


def test_a_clean_close_removes_an_old_pending_notice(tmp_path: Path) -> None:
    dirty = ShutdownReport("cast", "QUILL Cast")
    dirty.step("podcast_library", MUST_RECORD, _boom())
    dirty.persist(tmp_path)
    ShutdownReport("cast", "QUILL Cast").persist(tmp_path)
    assert not shutdown_report.pending_path(tmp_path, "cast").exists()


def test_the_next_launch_reads_it_once(tmp_path: Path) -> None:
    report = ShutdownReport("radio", "Quill Radio")
    report.step("last_seen", MUST_RECORD, _boom())
    report.persist(tmp_path)
    first = shutdown_report.take_pending(tmp_path, "radio")
    assert first.startswith("Last time Quill Radio closed")
    assert shutdown_report.take_pending(tmp_path, "radio") == ""
    assert shutdown_report.take_pending(tmp_path, "cast") == ""  # per app


def test_a_failure_is_logged_with_its_class_and_step(caplog: pytest.LogCaptureFixture) -> None:
    report = ShutdownReport("radio", "Quill Radio")
    with caplog.at_level(logging.WARNING, logger="quill.core.shutdown_report"):
        report.step("tray", BEST_EFFORT, _boom())
    line = caplog.records[0].getMessage()
    assert "step=tray" in line and "class=best-effort" in line and "error=OSError" in line


def test_persist_never_raises_even_when_the_folder_cannot_be_written(tmp_path: Path) -> None:
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("x", encoding="utf-8")
    report = ShutdownReport("cast", "QUILL Cast")
    report.step("podcast_library", MUST_RECORD, _boom())
    report.persist(blocked)  # must not raise


# -- the two apps' teardowns use it --------------------------------------------------- #


def test_cast_and_radio_class_their_final_writes_as_must_record() -> None:
    root = Path(__file__).resolve().parents[3]
    cast = (root / "quill" / "apps" / "podcasts_close.py").read_text(encoding="utf-8")
    radio = (root / "quill" / "apps" / "radio_shutdown.py").read_text(encoding="utf-8")
    assert 'report.step("podcast_library", MUST_RECORD' in cast
    assert 'report.step("listening_stats", MUST_RECORD' in cast
    assert 'report.step("last_seen", MUST_RECORD' in radio
    assert 'report.step("recording_marker", MUST_RECORD' in radio
    assert "report.persist(app_data_dir())" in cast and "report.persist(app_data_dir())" in radio


def test_radio_shutdown_runs_every_step_and_persists_through_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from quill.apps import radio_shutdown

    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    calls: list[str] = []

    def note(name: str):
        return lambda *_a, **_k: calls.append(name)

    def fail_marker() -> None:
        calls.append("marker")
        raise PermissionError("denied")

    app = SimpleNamespace(
        _app_host=SimpleNamespace(shutdown=note("quillins")),
        frame=object(),
        _stamp_radio_last_seen=note("last_seen"),
        stop_weather_monitoring=note("weather"),
        _clear_radio_recording_marker=fail_marker,
        _radio_controller=SimpleNamespace(shutdown=note("player")),
        _radio_recorder=SimpleNamespace(shutdown=note("recorder")),
        _radio_scheduler=SimpleNamespace(shutdown=note("scheduler")),
        _task_manager=SimpleNamespace(shutdown=note("tasks")),
        _unregister_media_keys=note("media_keys"),
        _unregister_global_hotkeys=note("hotkeys"),
        _remove_tray_icon=note("tray"),
    )
    radio_shutdown.run_radio_shutdown(app)
    assert calls[-1] == "tray"  # everything after the failure still ran
    assert "marker" in calls and "player" in calls
    assert shutdown_report.take_pending(tmp_path, "radio").startswith("Last time Quill Radio")


def test_radio_retry_keeps_the_marker_while_recording() -> None:
    from types import SimpleNamespace

    from quill.apps import radio_shutdown

    cleared: list[bool] = []
    app = SimpleNamespace(
        _stamp_radio_last_seen=lambda: None,
        _clear_radio_recording_marker=lambda: cleared.append(True),
        _radio_recorder=SimpleNamespace(active_count=lambda: 1),
    )
    said = radio_shutdown.retry_radio_final_writes(app)
    assert cleared == []
    assert "stays while you are recording" in said
    app._radio_recorder = SimpleNamespace(active_count=lambda: 0)
    radio_shutdown.retry_radio_final_writes(app)
    assert cleared == [True]
