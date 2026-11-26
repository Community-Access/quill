"""A finish whose check failed records the file it wrote (FUX-05).

Before, the work folder was kept with no record of the saved file, so the
next launch offered it as unfinished and recovering it saved a " (2)" copy.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import quill.platform.windows.screen_recorder_finish as finish
from quill.core.demo_recording import WORK_PREFIX, DemoPlan
from quill.core.demo_recording_ffmpeg import Capabilities
from quill.core.demo_recording_session import SegmentRecord, SessionRecord, plan_to_dict
from quill.core.demo_unfinished import describe_unfinished


def _session(tmp_path: Path) -> Path:
    work = tmp_path / f"{WORK_PREFIX}abc"
    segment = work / "1"
    segment.mkdir(parents=True)
    (segment / "video.mkv").write_bytes(b"video")
    plan = DemoPlan("display", "Display 1", (0, 0, 10, 10), str(tmp_path), sources=())
    SessionRecord(
        plan=plan_to_dict(plan),
        output=str(tmp_path / "Product demo.mp4"),
        started=datetime(2026, 11, 20, 16, 58).isoformat(),
        segments=[SegmentRecord(index=0, folder=str(segment), duration=10.0, closed=True)],
    ).save(work)
    return work


def test_saved_survives_a_round_trip(tmp_path):
    work = _session(tmp_path)
    session = SessionRecord.load(work)
    session.saved = "C:/x/Product demo.mp4"
    session.save(work)
    assert SessionRecord.load(work).saved == "C:/x/Product demo.mp4"


def test_a_failed_check_records_the_saved_file_and_is_not_offered_again(tmp_path, monkeypatch):
    work = _session(tmp_path)

    def run(command, _timeout):
        Path(command[-1]).write_bytes(b"out")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(finish, "_run", run)
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffprobe", lambda: None)
    monkeypatch.setattr(
        finish,
        "verify",
        lambda *a, **k: SimpleNamespace(
            state="Failed", timing=[], timing_data={}, source_timing=None
        ),
    )
    monkeypatch.setattr(finish, "save_reports", lambda *a, **k: None)
    result = finish.finalize(work, ffmpeg="ffmpeg", caps=Capabilities())
    assert result.state == "Failed"
    item = describe_unfinished(work)
    assert item.saved == tmp_path / "Product demo.mp4"
    assert not item.needs_finishing
    assert "already saved as Product demo.mp4" in item.label
