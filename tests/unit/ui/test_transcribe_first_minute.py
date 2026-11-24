"""FUX-11: Try the First Minute in Transcribe a Recording.

The first minute is transcribed with the very job the queue would run, its
words and a measured estimate are shown in the details box, nothing is queued,
OpenAI is never sampled, and a changed choice marks the result out of date.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.windows_dictation import file_transcribe as ft  # noqa: E402
from quill.core.windows_dictation.audio_file import RATE, AudioSource  # noqa: E402
from quill.ui import transcribe_first_minute as fm  # noqa: E402


def _wav(path: Path, seconds: float) -> Path:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\x00\x00" * int(16000 * seconds))
    return path


def test_first_seconds_reads_only_the_clip(tmp_path: Path) -> None:
    import numpy as np

    def opener(path: Path) -> AudioSource:
        def blocks() -> Any:
            for _ in range(10):
                yield np.zeros(RATE, dtype=np.float32)  # ten one-second blocks

        return AudioSource(path=path, duration=10.0, decoder="test", _blocks=blocks)

    clip = ft.first_seconds(2.5, opener)(tmp_path / "x.wav")
    assert clip.duration == 2.5
    assert sum(len(block) for block in clip.blocks()) == int(2.5 * RATE)
    short = ft.first_seconds(60, opener)(tmp_path / "x.wav")
    assert short.duration == 10.0  # a recording shorter than the clip is all of it


class _Thread:
    def __init__(self, *, target: Any, daemon: bool, name: str) -> None:
        assert daemon
        self.target = target

    def start(self) -> None:
        self.target()


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """FileTranscriber.run, faked: records the job, the opener and the rewrite."""
    runs: list[Any] = []

    def run(self: Any, progress: Any = None, cancelled: Any = lambda: False) -> Any:
        runs.append(self)
        return ft.FileTranscript(
            (ft.Paragraph(start=0.0, text="Hello from the first minute."),), 60.0, 6.0
        )

    monkeypatch.setattr(ft.FileTranscriber, "run", run)
    monkeypatch.setattr(fm.threading, "Thread", _Thread)
    return runs


def _dialog(path: Path, said: list[str]) -> Any:
    from types import SimpleNamespace

    from quill.ui.dictation_transcribe_dialog import TranscribeFileDialog, job_for

    prefs = SimpleNamespace(remove_fillers=True, dash="en", rewrite=str.upper)
    dialog = TranscribeFileDialog(
        None,
        paths=[path],
        weak=True,
        load_openai=False,
        sample_job=lambda choice, p: (job_for(choice, p, prefs), prefs.rewrite),
        announce=said.append,
    )
    deadline = time.monotonic() + 15
    while dialog._model_scan_pending and time.monotonic() < deadline:
        wx.Yield()
        time.sleep(0.005)
    return dialog


def test_the_first_minute_uses_the_queue_job_and_shows_words_and_estimate(
    wx_session_app: Any, wx_call_after: Any, tmp_path: Path, fake_run: list[Any]
) -> None:
    wx_call_after()
    said: list[str] = []
    dialog = _dialog(_wav(tmp_path / "talk.wav", 1.0), said)
    try:
        dialog.first_minute.press()
        assert len(fake_run) == 1
        transcriber = fake_run[0]
        choice = dialog.current_choice()
        assert transcriber.job.model == choice.model.id
        assert transcriber.job.remove_fillers is True and transcriber.job.dash == "en"
        assert transcriber.rewrite is str.upper  # the queue's rewrite, not a default
        assert transcriber.opener is not ft.open_audio  # the clip opener
        about = dialog.about.GetValue()
        assert "Hello from the first minute." in about
        assert "The sample took 6 seconds to make." in about
        assert "does not prove the rest" in about
        assert said[-1].startswith("First minute transcribed")

        dialog.timestamps.SetValue(True)
        dialog._describe()  # what the check box's event does
        assert "Out of date:" in dialog.about.GetValue()
    finally:
        dialog.Destroy()


def test_no_recording_says_why_and_runs_nothing(
    wx_session_app: Any, tmp_path: Path, fake_run: list[Any]
) -> None:
    said: list[str] = []
    dialog = _dialog(tmp_path / "missing.wav", said)
    try:
        dialog.first_minute.press()
        assert fake_run == []
        assert "was not found" in said[-1]
    finally:
        dialog.Destroy()


def test_stop_drops_a_late_result(
    wx_session_app: Any, wx_call_after: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    started: list[Any] = []

    class _Later:
        def __init__(self, *, target: Any, daemon: bool, name: str) -> None:
            started.append(target)

        def start(self) -> None:
            pass

    monkeypatch.setattr(fm.threading, "Thread", _Later)
    monkeypatch.setattr(
        ft.FileTranscriber,
        "run",
        lambda self, progress=None, cancelled=lambda: False: ft.FileTranscript(
            (ft.Paragraph(0.0, "late words"),), 60.0, 5.0
        ),
    )
    said: list[str] = []
    dialog = _dialog(_wav(tmp_path / "talk.wav", 1.0), said)
    try:
        dialog.first_minute.press()
        assert dialog.first_minute.running
        assert "Stop" in dialog.first_minute.button.GetLabel()
        dialog.first_minute.press()  # Stop
        assert not dialog.first_minute.running
        wx_call_after()
        started[0]()
        assert "late words" not in dialog.about.GetValue()
    finally:
        dialog.Destroy()


def test_openai_is_never_sampled(
    wx_session_app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_run: list[Any]
) -> None:
    from quill.core.windows_dictation import openai_models

    monkeypatch.setattr(openai_models, "cloud_problem", lambda **_k: "")
    said: list[str] = []
    dialog = _dialog(_wav(tmp_path / "talk.wav", 1.0), said)
    try:
        dialog.show_openai(["whisper-1"])
        cloud = [i for i, m in enumerate(dialog._models) if m.cloud]
        assert cloud
        dialog.model.SetSelection(cloud[0])
        dialog._describe()
        assert dialog.first_minute.button.IsEnabled()  # reachable, so it can say why
        dialog.first_minute.press()
        assert "OpenAI charges for every minute" in said[-1]
        assert not dialog.first_minute.running and fake_run == []
    finally:
        dialog.Destroy()


def test_rewriting_the_details_keeps_the_readers_place(
    wx_session_app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    said: list[str] = []
    dialog = _dialog(_wav(tmp_path / "talk.wav", 1.0), said)
    try:
        dialog._set_about("one two three four five six")
        monkeypatch.setattr(dialog.about, "HasFocus", lambda: True)
        dialog.about.SetInsertionPoint(8)
        dialog._set_about("one two three four five six seven")
        assert dialog.about.GetInsertionPoint() == 8
    finally:
        dialog.Destroy()
