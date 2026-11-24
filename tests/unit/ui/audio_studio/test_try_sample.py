"""FUX-11: Try a Sample on the Studio summary page.

A sample is spoken through the run's own pipeline, writes nothing beside the
documents, says what it measured and what it cannot prove, and is labelled
out of date when a setting changes.
"""

from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.speech import document_speech as ds  # noqa: E402
from quill.ui import batch_speech_runner as runner  # noqa: E402
from quill.ui.audio_studio import try_sample as ts  # noqa: E402
from quill.ui.audio_studio.request import BatchSpeechRequest  # noqa: E402
from quill.ui.audio_studio.run_setup import chapter_options, synthesis_spec  # noqa: E402


def _silence(out: Path, ms: int = 300) -> None:
    with wave.open(str(out), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b"\x00\x00" * int(22050 * ms / 1000))


def _req(folder: Path, **over: Any) -> BatchSpeechRequest:
    values: dict[str, Any] = {
        "source_folder": folder,
        "recursive": False,
        "extensions": (".txt",),
        "engine": "kokoro",
        "voice": "am_liam",
        "rate": 190,
        "speed": 1.0,
        "output_format": "wav",
        "sound_enabled": False,
        "sound_volume": 80,
        "article_gap_ms": 0,
        "sentence_gap_ms": 0,
        "tail_padding_ms": 0,
        "speak_headings": False,
        "skip_existing": False,
    }
    values.update(over)
    return BatchSpeechRequest(**values)


def _host() -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(
        settings=SimpleNamespace(pronunciation_enabled=False), _announce=said.append, said=said
    )


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "a.txt").write_text(" ".join(f"word{i}" for i in range(200)), encoding="utf-8")
    (folder / "b.txt").write_text(" ".join(f"more{i}" for i in range(600)), encoding="utf-8")
    return folder


def test_a_sample_speaks_the_opening_with_the_run_settings_into_its_own_folder(
    docs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spoken: list[str] = []

    def fake_kokoro(text: str, out: Path, *, voice: str = "", speed: float = 1.0) -> None:
        spoken.append(text)
        _silence(out)

    monkeypatch.setattr(ds.read_aloud, "synthesize_with_kokoro", fake_kokoro)
    before = sorted(p.name for p in docs.iterdir())
    folder = tmp_path / "sample"
    folder.mkdir()
    req = _req(docs)
    host = _host()
    import threading

    outcome = ts.make_sample(host, req, folder, threading.Event())

    assert sorted(p.name for p in docs.iterdir()) == before  # nothing beside the documents
    assert outcome.play_path.parent == folder
    words = " ".join(spoken).split()
    assert words[0] == "word0" and "word80" not in words and len(words) <= ts.SAMPLE_WORDS
    assert outcome.result.covered == "the first 80 words of a.txt"
    assert outcome.result.total_units == 800  # both documents
    assert outcome.result.output_seconds is not None and outcome.result.output_seconds > 0
    assert outcome.result.is_current(ts.sample_fingerprint(host, req, docs / "a.txt"))
    assert outcome.whole == "all 2 documents"
    text = ts.describe(outcome, req)
    assert "narrating all 2 documents should take" in text
    assert "does not prove the rest" in text


def test_the_sample_uses_the_same_spec_and_options_as_the_run(
    docs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def fake(source: Path, out: Path, spec: Any, options: Any, **kw: Any) -> Any:
        seen.update(source=source, spec=spec, options=options, **kw)
        _silence(out)
        return SimpleNamespace(output_path=out, with_tones_path=None)

    monkeypatch.setattr(ds, "synthesize_document_to_chaptered_file", fake)
    req = _req(docs, round_robin_voices=("am_liam", "af_heart"), sentence_gap_ms=250)
    import threading

    ts.make_sample(_host(), req, tmp_path, threading.Event())
    assert seen["spec"] == synthesis_spec(req)
    assert seen["options"] == chapter_options(req)
    assert seen["voice_rotation"] == ["am_liam", "af_heart"]
    assert seen["max_words"] == ts.SAMPLE_WORDS
    assert "voice_blacklist" not in seen  # a sample never blacklists a voice


def test_stop_between_chunks_keeps_nothing(
    docs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    stop = threading.Event()

    def fake(source: Path, out: Path, spec: Any, options: Any, **kw: Any) -> Any:
        stop.set()
        kw["on_progress"](1, 2)
        raise AssertionError("not reached")

    monkeypatch.setattr(ds, "synthesize_document_to_chaptered_file", fake)
    with pytest.raises(ts.SampleStopped):
        ts.make_sample(_host(), _req(docs), tmp_path, stop)


def _controls(wx_session_app: Any) -> tuple[Any, Any, Any]:
    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    panel.SetSizer(sizer)
    host = _host()
    return frame, ts.SampleControls(panel, sizer, host), host


def test_the_button_is_offered_only_for_narration(wx_session_app: Any, docs: Path) -> None:
    frame, controls, _host_ = _controls(wx_session_app)
    try:
        controls.show_for(_req(docs))
        assert controls.button.IsShown()
        assert controls.result.GetValue() == ts.NO_SAMPLE_YET
        controls.show_for(_req(docs, extensions=()))  # the combine-recordings journey
        assert not controls.button.IsShown()
        controls.show_for(_req(docs, dry_run=True))
        assert not controls.button.IsShown()
    finally:
        frame.Destroy()


def test_a_changed_setting_marks_the_sample_out_of_date(
    wx_session_app: Any, docs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    played: list[tuple[str, int]] = []
    monkeypatch.setattr(
        ts.SampleControls,
        "_play",
        lambda self, wav, delay_ms=0: played.append((wav.name, delay_ms)),
    )
    frame, controls, host = _controls(wx_session_app)
    try:
        req = _req(docs)
        controls.show_for(req)
        wav = tmp_path / "sample.wav"
        _silence(wav)
        from quill.core.rehearsal import SampleResult

        outcome = ts.SampleOutcome(
            result=SampleResult(
                fingerprint=ts.sample_fingerprint(host, req, docs / "a.txt"),
                covered="the first 80 words of a.txt",
                sample_units=80,
                total_units=800,
                elapsed_seconds=4,
                output_bytes=1000,
                output_seconds=30,
            ),
            play_path=wav,
            summary="Sample of a.txt.",
            whole="all 2 documents",
        )
        import threading

        stop = threading.Event()
        controls._stop = stop
        controls._finished(stop, req, outcome, None)
        assert "should take" in controls.result.GetValue()
        assert played == [("sample.wav", ts.PLAY_DELAY_MS)]  # after the short sentence
        assert host.said[-1] == "Sample ready."

        controls.show_for(_req(docs, voice="af_heart"))
        assert controls.result.GetValue().startswith("Out of date:")
        controls.show_for(req)  # back to the settings it tested
        assert not controls.result.GetValue().startswith("Out of date:")

        said = len(host.said)
        controls.press()  # current: replay rather than make another, and say nothing
        assert played[-1] == ("sample.wav", 0)
        assert len(host.said) == said
    finally:
        frame.Destroy()


def test_press_makes_a_sample_off_the_ui_thread_and_stop_discards_it(
    wx_session_app: Any,
    wx_call_after: Any,
    docs: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[Any] = []

    class _Thread:
        def __init__(self, *, target: Any, daemon: bool, name: str) -> None:
            assert daemon
            self.target = target

        def start(self) -> None:
            started.append(self.target)

    monkeypatch.setattr(ts.threading, "Thread", _Thread)
    monkeypatch.setattr(runner, "_engine_available", lambda _h: {"kokoro": True})
    monkeypatch.setattr(ts.tempfile, "mkdtemp", lambda **_kw: str(tmp_path / "s"))
    (tmp_path / "s").mkdir()
    calls: list[str] = []
    monkeypatch.setattr(ts, "make_sample", lambda *a: calls.append("made"))
    wx_call_after()
    frame, controls, host = _controls(wx_session_app)
    try:
        controls.show_for(_req(docs))
        controls.press()
        assert controls.running and "Stop" in controls.button.GetLabel()
        controls.press()  # Stop
        assert not controls.running
        assert controls.result.GetValue() == "Sample stopped. Nothing was kept."
        started[0]()  # the worker finishes late: its result is dropped
        assert controls.result.GetValue() == "Sample stopped. Nothing was kept."
        controls.close()
        assert not (tmp_path / "s").exists()
    finally:
        frame.Destroy()


def test_a_missing_engine_says_so_and_makes_nothing(
    wx_session_app: Any, docs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "_engine_available", lambda _h: {"kokoro": False})
    frame, controls, _host_ = _controls(wx_session_app)
    try:
        controls.show_for(_req(docs))
        controls.press()
        assert not controls.running
        assert "not fully installed" in controls.result.GetValue()
    finally:
        frame.Destroy()


def test_a_press_while_playing_stops_the_sound_and_leaving_the_page_halts(
    wx_session_app: Any, tmp_path: Path, docs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import winsound

    calls: list[Any] = []
    monkeypatch.setattr(winsound, "PlaySound", lambda *a: calls.append(a))
    later: list[Any] = []
    monkeypatch.setattr(ts.wx, "CallLater", lambda ms, fn, *a: later.append((ms, fn, a)))
    frame, controls, host = _controls(wx_session_app)
    try:
        controls.show_for(_req(docs))
        wav = tmp_path / "s.wav"
        _silence(wav)
        controls._play(wav, delay_ms=ts.PLAY_DELAY_MS)
        assert calls == [] and later[0][0] == ts.PLAY_DELAY_MS  # nothing over the speech
        assert "Stop" in controls.button.GetLabel()
        controls.press()  # stop it during the pause
        _ms, fn, args = later[0]
        fn(*args)  # the pause ends: the stopped sample must not start
        assert all(a[0] is None for a in calls)
        assert "Try" in controls.button.GetLabel()

        controls._play(wav)
        assert calls[-1][0] == str(wav)
        import threading

        controls._stop = threading.Event()  # a sample being made as well
        controls.halt()  # the wizard leaves the summary page
        assert calls[-1] == (None, 0)
        assert not controls.running
        assert "left this page" in controls.result.GetValue()
    finally:
        frame.Destroy()


def test_the_wizard_halts_the_sample_when_the_summary_page_is_left(
    wx_session_app: Any, tmp_path: Path
) -> None:
    from quill.ui.audio_studio.wizard import AudioStudioWizard

    frame = wx.Frame(None)
    dlg = AudioStudioWizard(
        frame,
        defaults=_req(tmp_path),
        engine_options=[("Kokoro", "kokoro")],
        engine_available={"kokoro": True},
        voices_for=lambda _e: [],
        on_preview=lambda _e, _v: None,
        host=_host(),
    )
    try:
        halted: list[bool] = []
        assert dlg.summary.sample is not None
        dlg.summary.sample.halt = lambda: halted.append(True)  # type: ignore[method-assign]
        last = len(dlg._sequence()) - 1
        dlg._show_page(last)
        dlg._show_page(last - 1)  # Back
        assert halted == [True]
    finally:
        dlg.Destroy()
        frame.Destroy()
