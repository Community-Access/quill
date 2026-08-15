"""Recordings and the real OptiLab engine: when it runs, and when it must not.

The post-pass happens *after* a recording is over, never during it -- an adapter
fault mid-capture must not be able to cost somebody the show they were recording.
These tests pin that ordering and the refusals around it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.radio import recording as recording_module
from quill.core.radio.recording import RadioRecorder, RecordingJob, RecordingSettings
from quill.core.radio.recording_commands import encode_args_for_format


class TestSettings:
    def test_exact_processing_is_off_by_default(self) -> None:
        assert RecordingSettings().exact_optilab is False

    def test_it_survives_a_save_and_load(self) -> None:
        settings = RecordingSettings(exact_optilab=True)
        assert RecordingSettings.from_dict(settings.to_dict()).exact_optilab is True

    def test_a_settings_file_written_before_the_feature_still_loads(self) -> None:
        # No key at all: an older file must read as "off", not raise.
        assert RecordingSettings.from_dict({"format": "mp3"}).exact_optilab is False


class TestEncodeArgs:
    def test_a_recording_is_re_encoded_the_way_it_was_recorded(self) -> None:
        # If the post-pass picked its own codec, turning exact processing on
        # would silently change the format of what somebody keeps.
        assert encode_args_for_format("mp3", 192) == ["-c:a", "libmp3lame", "-b:a", "192k"]
        assert encode_args_for_format("flac", 192) == ["-c:a", "flac"]

    def test_a_raw_capture_has_no_encode_at_all(self) -> None:
        assert encode_args_for_format("copy", 192) == []


def _job(tmp_path: Path, *, settings: RecordingSettings, exact: ExactOptilab | None) -> Any:
    class _DeadProcess:
        returncode = 0

        def poll(self) -> int:
            return 0

    return RecordingJob(
        job_id="j1",
        process=_DeadProcess(),  # type: ignore[arg-type]
        destination=tmp_path / "show.mp3",
        final_destination=tmp_path / "show.mp3",
        station_name="Test FM",
        stream_url="http://example.invalid/stream",
        settings=settings,
        minutes=30,
        filter_graph="",
        extension="mp3",
        started_at=datetime(2026, 8, 13, 10, 0, 0),
        scheduled_end=datetime(2026, 8, 13, 10, 30, 0),
        exact=exact,
    )


class TestPostPass:
    def test_nothing_happens_when_it_was_not_asked_for(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[Path] = []
        monkeypatch.setattr(
            recording_module,
            "encode_args_for_format",
            lambda *_a, **_k: ["-c:a", "libmp3lame"],
        )
        from quill.core.audio import exact_optilab

        monkeypatch.setattr(exact_optilab, "process_in_place", lambda p, *_a, **_k: calls.append(p))
        recorder = RadioRecorder()
        job = _job(tmp_path, settings=RecordingSettings(), exact=None)
        recorder._apply_exact_optilab(job, tmp_path / "show.mp3")
        assert calls == []

    def test_it_runs_and_says_so_when_asked_for(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        spoken: list[str] = []
        processed: list[Path] = []
        from quill.core.audio import exact_optilab

        monkeypatch.setattr(exact_optilab, "available", lambda: True)
        monkeypatch.setattr(
            exact_optilab, "process_in_place", lambda p, *_a, **_k: processed.append(p)
        )
        recorder = RadioRecorder(on_exact_processed=spoken.append)
        job = _job(
            tmp_path,
            settings=RecordingSettings(exact_optilab=True),
            exact=ExactOptilab(mode="podcast"),
        )
        recorder._apply_exact_optilab(job, tmp_path / "show.mp3")
        assert processed == [tmp_path / "show.mp3"]
        assert spoken and "OptiLab" in spoken[0]

    def test_an_absent_component_is_announced_rather_than_silently_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        spoken: list[str] = []
        from quill.core.audio import exact_optilab

        monkeypatch.setattr(exact_optilab, "available", lambda: False)
        recorder = RadioRecorder(on_exact_processed=spoken.append)
        job = _job(
            tmp_path,
            settings=RecordingSettings(exact_optilab=True),
            exact=ExactOptilab(mode="stream"),
        )
        recorder._apply_exact_optilab(job, tmp_path / "show.mp3")
        # A listener who turned this on is entitled to know it did not happen.
        assert spoken and "without exact OptiLab processing" in spoken[0]

    def test_a_failure_is_reported_and_the_recording_survives(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        spoken: list[str] = []
        from quill.core.audio import exact_optilab

        def explode(*_a: object, **_k: object) -> None:
            raise exact_optilab.ExactProcessingError("the engine fell over")

        monkeypatch.setattr(exact_optilab, "available", lambda: True)
        monkeypatch.setattr(exact_optilab, "process_in_place", explode)
        recorder = RadioRecorder(on_exact_processed=spoken.append)
        job = _job(
            tmp_path,
            settings=RecordingSettings(exact_optilab=True),
            exact=ExactOptilab(mode="limiter"),
        )
        recorder._apply_exact_optilab(job, tmp_path / "show.mp3")
        assert spoken and "was saved" in spoken[0]

    def test_a_raw_capture_is_never_post_processed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A raw capture is the original packets. Re-encoding it would make it
        not that, which is the only thing raw capture is for."""
        processed: list[Path] = []
        from quill.core.audio import exact_optilab

        monkeypatch.setattr(exact_optilab, "available", lambda: True)
        monkeypatch.setattr(
            exact_optilab, "process_in_place", lambda p, *_a, **_k: processed.append(p)
        )
        recorder = RadioRecorder()
        job = _job(
            tmp_path,
            settings=RecordingSettings(format="copy", exact_optilab=True),
            exact=ExactOptilab(mode="podcast"),
        )
        recorder._apply_exact_optilab(job, tmp_path / "show.mka")
        assert processed == []
