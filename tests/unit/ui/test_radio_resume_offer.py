"""Quill Radio's launch-time offer for an interrupted recording (R3, FUX-05).

The decision flow had no test at all: ask, always, never, a dismissed offer,
a recording whose time ran out (cleared without a word), a resume that failed
(spoke the exception), and the legacy-marker clear that wiped every marker,
the resumed recording's new one included.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

import quill.core.paths as paths
import quill.ui.outcome_report as outcome_report
import quill.ui.radio.resume_recording_dialog as dialogs
from quill.core.radio.recording_resume import (
    ActiveRecordingMarker,
    load_markers,
    save_marker,
)
from quill.ui.radio import resume_offer


class Recorder:
    def __init__(self, data_dir: Path, fail: bool = False) -> None:
        self.data_dir = data_dir
        self.fail = fail
        self.started: list[dict[str, object]] = []

    def start(self, **kwargs: object) -> None:
        if self.fail:
            raise OSError(r"C:\Temp\x\ffmpeg.exe exited with code 1")
        self.started.append(kwargs)
        # The new job writes its own marker under its own id, as the recorder does.
        save_marker(
            self.data_dir,
            ActiveRecordingMarker(
                station_name=str(kwargs["station_name"]),
                stream_url=str(kwargs["stream_url"]),
                temp_path="",
                output_path="",
                started_at=datetime.now().isoformat(),
                scheduled_end=(datetime.now() + timedelta(minutes=30)).isoformat(),
                duration_minutes=30,
                job_id="new-job",
            ),
        )


class Host:
    def __init__(self, data_dir: Path, choice: str = "ask", fail: bool = False) -> None:
        self.frame = None
        self.spoken: list[str] = []
        self._radio_history = SimpleNamespace(recording_resume_choice=choice)
        self.saved_history = 0
        self._radio_recorder = Recorder(data_dir, fail=fail)
        self._radio_recording_settings = SimpleNamespace(
            temp_dir="", destination_root=str(data_dir / "Recordings")
        )

    def _announce(self, text: str, sound: object = "") -> None:
        self.spoken.append(text)

    def _save_radio_history(self) -> None:
        self.saved_history += 1

    def _radio_recording_filter_graph(self) -> str:
        return ""

    def _radio_recording_exact(self) -> None:
        return None


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("quill.core.speech.ffmpeg.ffmpeg_available", lambda: True)
    return tmp_path


@pytest.fixture
def kept(monkeypatch):
    notes: list[dict[str, object]] = []

    def keep(action, summary, **kwargs):
        notes.append({"action": action, "summary": summary, **kwargs})

    monkeypatch.setattr(outcome_report, "keep_outcome", keep)
    return notes


def _marker(data_dir: Path, *, ends_in: int, job_id: str = "old-job") -> ActiveRecordingMarker:
    started = datetime.now() - timedelta(minutes=20)
    marker = ActiveRecordingMarker(
        station_name="WQXR",
        stream_url="http://example.invalid/stream",
        temp_path="",
        output_path=str(data_dir / "Recordings" / "WQXR - show.mp3"),
        started_at=started.isoformat(),
        scheduled_end=(datetime.now() + timedelta(minutes=ends_in)).isoformat(),
        duration_minutes=20 + ends_in,
        job_id=job_id,
    )
    part = Path(marker.output_path)
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"audio")
    stamp = (started + timedelta(minutes=15)).timestamp()
    os.utime(part, (stamp, stamp))
    save_marker(data_dir, marker)
    return marker


class FakeDialog:
    answer: tuple[str, bool] | None = None
    seen: list[dict[str, object]] = []

    def __init__(self, _parent, **kwargs):
        FakeDialog.seen.append(kwargs)

    def show(self):
        return FakeDialog.answer


@pytest.fixture
def dialog(monkeypatch):
    FakeDialog.seen = []
    monkeypatch.setattr(dialogs, "ResumeRecordingDialog", FakeDialog)
    monkeypatch.setattr(dialogs, "ResumeRecordingsBatchDialog", FakeDialog)
    return FakeDialog


def test_ask_offers_the_work_and_resume_starts_it(data_dir, dialog):
    _marker(data_dir, ends_in=30)
    dialog.answer = ("resume", False)
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    message = str(dialog.seen[0]["message"])
    assert "Your recording of WQXR, started" in message
    assert "What it recorded, 15 minutes, is kept in your recordings folder." in message
    assert "as a separate file" in message
    assert host._radio_recorder.started[0]["station_name"] == "WQXR"
    assert [m.job_id for m in load_markers(data_dir)] == ["new-job"]


def test_skip_deletes_nothing_and_clears_only_the_marker(data_dir, dialog):
    marker = _marker(data_dir, ends_in=30)
    dialog.answer = ("skip", True)
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    assert load_markers(data_dir) == []
    assert Path(marker.output_path).is_file()
    assert host._radio_history.recording_resume_choice == "never"
    assert host.saved_history == 1


def test_dismissed_offer_keeps_the_marker_for_next_launch(data_dir, dialog):
    _marker(data_dir, ends_in=30)
    dialog.answer = None
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    assert [m.job_id for m in load_markers(data_dir)] == ["old-job"]
    assert host._radio_recorder.started == []


def test_always_resumes_without_asking_and_never_clears(data_dir, dialog):
    _marker(data_dir, ends_in=30)
    host = Host(data_dir, choice="always")
    resume_offer.reconcile_and_offer(host)
    assert dialog.seen == []
    assert len(host._radio_recorder.started) == 1

    _marker(data_dir, ends_in=30, job_id="another")
    host = Host(data_dir, choice="never")
    resume_offer.reconcile_and_offer(host)
    assert host._radio_recorder.started == []
    assert load_markers(data_dir) == []


def test_time_run_out_is_said_once_and_kept_not_cleared_silently(data_dir, dialog, kept):
    marker = _marker(data_dir, ends_in=-60)
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    assert dialog.seen == []
    assert len(host.spoken) == 1
    said = host.spoken[0]
    assert said.startswith("Your recording of WQXR, started")
    assert "stopped unexpectedly before it was due to end at" in said
    assert "15 minutes, is kept in your recordings folder" in said
    assert kept and kept[0]["summary"] == said and kept[0]["partial"] is True
    assert kept[0]["path"] == Path(marker.output_path)
    assert load_markers(data_dir) == []
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    assert host.spoken == []


def test_failed_resume_names_the_station_not_the_exception(data_dir, dialog):
    _marker(data_dir, ends_in=30)
    dialog.answer = ("resume", False)
    host = Host(data_dir, fail=True)
    resume_offer.reconcile_and_offer(host)
    assert host.spoken == [
        "The recording of WQXR could not be resumed. What it recorded before is kept."
    ]


def test_legacy_marker_resume_never_wipes_the_new_marker(data_dir, dialog):
    import json

    legacy = _marker(data_dir, ends_in=30, job_id="")
    for path in (data_dir / "radio_active_recordings").glob("*.json"):
        path.unlink()
    (data_dir / "radio_active_recording.json").write_text(
        json.dumps(legacy.to_dict()), encoding="utf-8"
    )
    dialog.answer = ("resume", False)
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    assert [m.job_id for m in load_markers(data_dir)] == ["new-job"]


def test_several_recordings_are_listed_with_what_each_recorded(data_dir, dialog):
    _marker(data_dir, ends_in=30, job_id="a")
    _marker(data_dir, ends_in=40, job_id="b")
    dialog.answer = ("skip", False)
    host = Host(data_dir)
    resume_offer.reconcile_and_offer(host)
    lines = dialog.seen[0]["lines"]
    assert len(lines) == 2
    assert all("15 minutes recorded" in line for line in lines)
