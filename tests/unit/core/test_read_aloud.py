from __future__ import annotations

from pathlib import Path

from quill.core import read_aloud as read_aloud_module
from quill.core.read_aloud import (
    KOKORO_VOICE_GRADES,
    KOKORO_VOICES,
    ReadAloudController,
    ReadAloudUnavailableError,
    discover_espeak_executable,
    discover_piper_executable,
    list_dectalk_voices,
    list_espeak_english_voices,
    list_kokoro_voices,
    list_piper_voices,
    list_voices,
    sentence_spans,
    synthesize_to_file_with_dectalk,
    synthesize_to_file_with_sapi5,
    synthesize_with_espeak,
    synthesize_with_piper,
)


def _record_sapi5_synth(monkeypatch) -> list[tuple[str, str]]:
    """Patch SAPI 5 synthesis to record (text, voice) and skip audio playback.

    Live read-aloud routes SAPI 5 through the shared WAV-sentence player, so the
    controller calls ``synthesize_to_file_with_sapi5`` per sentence and then
    plays the file. Recording the synth call and disabling winsound lets tests
    assert what would be spoken without producing sound.
    """
    spoken: list[tuple[str, str]] = []

    def fake_synth(text, output_path, *, voice="", rate=200, volume=1.0) -> None:
        spoken.append((text, voice))
        Path(output_path).write_bytes(b"")

    monkeypatch.setattr(read_aloud_module, "synthesize_to_file_with_sapi5", fake_synth)
    monkeypatch.setattr(read_aloud_module, "_winsound", None)
    return spoken


def test_sentence_spans() -> None:
    spans = sentence_spans("One. Two! Three?")
    assert [(span.start, span.end) for span in spans] == [(0, 5), (5, 10), (10, 16)]


def test_list_voices_uses_backend(monkeypatch) -> None:
    from quill.platform.windows import sapi5 as sapi5_mod

    monkeypatch.setattr(
        sapi5_mod, "list_voices", lambda: [sapi5_mod.Sapi5Voice(id="voice-1", name="Voice 1")]
    )

    voices = list_voices()
    assert [(voice.id, voice.name) for voice in voices] == [("voice-1", "Voice 1")]


def test_read_aloud_controller_speaks_sentences(monkeypatch) -> None:
    spoken = _record_sapi5_synth(monkeypatch)

    controller = ReadAloudController()
    controller.start("One. Two!", 0, "voice-1")
    assert controller._thread is not None
    controller._thread.join(timeout=2)

    assert [text for text, _voice in spoken] == ["One.", "Two!"]
    assert all(voice == "voice-1" for _text, voice in spoken)


def test_read_aloud_controller_applies_punctuation_level(monkeypatch) -> None:
    spoken = _record_sapi5_synth(monkeypatch)

    controller = ReadAloudController()
    controller.start("Cost is $5.", 0, "voice-1", punctuation_level="all")
    assert controller._thread is not None
    controller._thread.join(timeout=2)

    text = " ".join(t for t, _ in spoken)
    assert "dollar" in text.split()
    assert "dot" in text.split()


def test_inter_sentence_pause_zero_returns_immediately() -> None:
    import time

    controller = ReadAloudController()
    controller._sentence_pause_ms = 0
    start = time.monotonic()
    controller._inter_sentence_pause()
    assert time.monotonic() - start < 0.05


def test_inter_sentence_pause_waits_configured_gap() -> None:
    import time

    controller = ReadAloudController()
    controller._sentence_pause_ms = 120
    start = time.monotonic()
    controller._inter_sentence_pause()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1


def test_inter_sentence_pause_interrupted_by_stop() -> None:
    import time

    controller = ReadAloudController()
    controller._sentence_pause_ms = 5000
    controller._stop_event.set()
    start = time.monotonic()
    controller._inter_sentence_pause()
    assert time.monotonic() - start < 0.2


def test_start_records_sentence_pause(monkeypatch) -> None:
    _record_sapi5_synth(monkeypatch)
    controller = ReadAloudController()
    controller.start("One. Two!", 0, "voice-1", sentence_pause_ms=250)
    if controller._thread is not None:
        controller._thread.join(timeout=2)
    assert controller._sentence_pause_ms == 250

    voices = list_dectalk_voices()
    assert voices
    assert voices[0].id == "paul"
    assert any(voice.id == "betty" for voice in voices)


def test_build_dectalk_payload_includes_voice_and_rate() -> None:
    from quill.core.read_aloud import build_dectalk_payload

    payload = build_dectalk_payload("Hello there", "paul", 200)
    assert "[:np]" in payload
    assert "[:ra 200]" in payload
    assert "Hello there" in payload


def test_discover_piper_executable_uses_explicit_path(tmp_path: Path) -> None:
    exe = tmp_path / "piper.exe"
    exe.write_text("binary", encoding="utf-8")
    discovered = discover_piper_executable(str(exe))
    assert discovered == exe.resolve()


def test_discover_piper_executable_rejects_unexpected_binary(tmp_path: Path) -> None:
    # SEC-1: a tampered settings value pointing at an arbitrary executable
    # (e.g. cmd.exe) must be rejected, not launched.
    rogue = tmp_path / "cmd.exe"
    rogue.write_text("binary", encoding="utf-8")
    result = discover_piper_executable(str(rogue))
    assert result != rogue.resolve()


def test_discover_piper_executable_rejects_directory(tmp_path: Path) -> None:
    folder = tmp_path / "piper.exe"
    folder.mkdir()
    result = discover_piper_executable(str(folder))
    assert result != folder.resolve()


def test_discover_espeak_executable_rejects_unexpected_binary(tmp_path: Path, monkeypatch) -> None:
    # Isolate the managed speech folder so a dev machine with eSpeak installed
    # does not satisfy discovery and mask the rejection.
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(read_aloud_module.shutil, "which", lambda _name: None)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    rogue = tmp_path / "powershell.exe"
    rogue.write_text("binary", encoding="utf-8")
    assert discover_espeak_executable(str(rogue)) is None


def test_discover_dectalk_executable_rejects_unexpected_binary(
    tmp_path: Path, monkeypatch: object
) -> None:
    # Patch app_data_dir so the managed speech folder is empty (tmp_path has no DECtalk).
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    rogue = tmp_path / "calc.exe"
    rogue.write_text("binary", encoding="utf-8")
    assert read_aloud_module.discover_dectalk_executable(str(rogue)) is None


def test_synthesize_with_piper_runs_process(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "piper.exe"
    model = tmp_path / "voice.onnx"
    output = tmp_path / "speech.wav"
    exe.write_text("binary", encoding="utf-8")
    model.write_text("model", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    called: dict[str, object] = {}

    def fake_run(command, **kwargs):
        called["command"] = command
        called["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr(read_aloud_module.subprocess, "run", fake_run)

    synthesize_with_piper(
        "Hello from piper",
        output,
        executable_path=exe,
        model_path=model,
    )
    assert called["command"] == [
        str(exe),
        "--model",
        str(model),
        "--output_file",
        str(output),
    ]
    # M-15: text is delivered via a temp-file stdin, not the pipe buffer.
    assert hasattr(called["kwargs"].get("stdin"), "read"), "stdin must be a file-like object"


def test_synthesize_with_piper_raises_for_failure(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "piper.exe"
    model = tmp_path / "voice.onnx"
    output = tmp_path / "speech.wav"
    exe.write_text("binary", encoding="utf-8")
    model.write_text("model", encoding="utf-8")

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "bad model"

    monkeypatch.setattr(read_aloud_module.subprocess, "run", lambda *_args, **_kwargs: Completed())

    try:
        synthesize_with_piper(
            "Hello from piper",
            output,
            executable_path=exe,
            model_path=model,
        )
    except ReadAloudUnavailableError as exc:
        assert "Piper failed" in str(exc)
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


# ---------------------------------------------------------------------------
# eSpeak-NG helpers
# ---------------------------------------------------------------------------


def test_list_espeak_english_voices_covers_key_variants() -> None:
    voices = list_espeak_english_voices()
    ids = [v.id for v in voices]
    # 8 bundled lang definition files (lang/gmw/en*)
    assert "en-gb" in ids
    assert "en-us" in ids
    assert "en-gb-scotland" in ids
    assert "en-029" in ids
    assert len(ids) == 8
    # eSpeak is English-only in Quill — no non-English variants expected
    assert all(id_.startswith("en") for id_ in ids)


def test_discover_espeak_executable_explicit_path(tmp_path: Path) -> None:
    exe = tmp_path / "espeak-ng.exe"
    exe.write_text("binary", encoding="utf-8")
    found = discover_espeak_executable(str(exe))
    assert found == exe.resolve()


def test_discover_espeak_executable_missing_returns_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(read_aloud_module.shutil, "which", lambda _name: None)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    found = discover_espeak_executable("/nonexistent/path/espeak-ng.exe")
    assert found is None


def test_synthesize_with_espeak_calls_process(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "espeak-ng.exe"
    exe.write_text("binary", encoding="utf-8")
    output = tmp_path / "speech.wav"

    class Completed:
        returncode = 0

    called: dict[str, object] = {}

    def fake_run(command, **kwargs):
        called["command"] = command
        return Completed()

    monkeypatch.setattr(read_aloud_module.subprocess, "run", fake_run)
    synthesize_with_espeak("Hello world", output, executable_path=exe, voice="en-us", rate=175)
    cmd = called["command"]
    assert str(exe) in cmd
    assert "-v" in cmd and "en-us" in cmd
    assert "-w" in cmd and str(output) in cmd


def test_synthesize_with_espeak_raises_on_failure(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "espeak-ng.exe"
    exe.write_text("binary", encoding="utf-8")
    output = tmp_path / "speech.wav"

    class Completed:
        returncode = 1
        stderr = b"error"
        stdout = b""

    monkeypatch.setattr(read_aloud_module.subprocess, "run", lambda *_a, **_kw: Completed())
    try:
        synthesize_with_espeak("Hi", output, executable_path=exe, voice="en")
    except ReadAloudUnavailableError as exc:
        assert "eSpeak-NG" in str(exc)
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


# ---------------------------------------------------------------------------
# Kokoro helpers
# ---------------------------------------------------------------------------


def test_list_kokoro_voices_has_american_and_british() -> None:
    voices = list_kokoro_voices()
    ids = [v.id for v in voices]
    assert any(i.startswith("af_") for i in ids), "no American female voices"
    assert any(i.startswith("am_") for i in ids), "no American male voices"
    assert any(i.startswith("bf_") for i in ids), "no British female voices"
    assert any(i.startswith("bm_") for i in ids), "no British male voices"


def test_list_kokoro_voices_default_is_af_heart() -> None:
    voices = list_kokoro_voices()
    assert voices[0].id == "af_heart"


def test_synthesize_with_kokoro_raises_when_package_missing(monkeypatch, tmp_path: Path) -> None:
    import builtins

    # Force the ONNX fast-path off (a dev machine may have the models) so this
    # exercises the kokoro+torch fallback, then block that import.
    monkeypatch.setattr(read_aloud_module, "kokoro_onnx_ready", lambda *a, **k: False)

    real_import = builtins.__import__

    def _block(name, *args, **kwargs):
        if name == "kokoro":
            raise ImportError("no kokoro")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block)
    from quill.core.read_aloud import synthesize_with_kokoro

    try:
        synthesize_with_kokoro("Hello", tmp_path / "out.wav")
    except ReadAloudUnavailableError as exc:
        assert "kokoro" in str(exc).lower()
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


_CANONICAL_KOKORO_IDS: set[str] = {
    # American female (11)
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    # American male (9)
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
    # British female (4)
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    # British male (4)
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
}


def test_kokoro_voices_canonical_28() -> None:
    ids = {vid for vid, _ in KOKORO_VOICES}
    assert ids == _CANONICAL_KOKORO_IDS, (
        f"missing={_CANONICAL_KOKORO_IDS - ids}, unexpected={ids - _CANONICAL_KOKORO_IDS}"
    )


def test_kokoro_voices_af_jessica_present() -> None:
    ids = {vid for vid, _ in KOKORO_VOICES}
    assert "af_jessica" in ids, "af_jessica is an official Kokoro voice and must not be omitted"


def test_kokoro_voices_am_santa_not_zeus() -> None:
    ids = {vid for vid, _ in KOKORO_VOICES}
    assert "am_santa" in ids, "canonical American male voice is am_santa"
    assert "am_zeus" not in ids, "am_zeus is not a canonical Kokoro voice"


def test_kokoro_voice_grades_cover_all_28() -> None:
    ids = {vid for vid, _ in KOKORO_VOICES}
    assert ids == set(KOKORO_VOICE_GRADES.keys()), (
        "KOKORO_VOICE_GRADES must cover every voice in KOKORO_VOICES"
    )


def test_kokoro_voice_grade_af_jessica_is_d() -> None:
    assert KOKORO_VOICE_GRADES["af_jessica"] == "D", (
        "af_jessica has official grade D — grade must be stored as metadata, never used to filter"
    )


def test_list_kokoro_voices_af_jessica_survives_all_filters() -> None:
    voices = list_kokoro_voices()
    ids = [v.id for v in voices]
    assert "af_jessica" in ids, "af_jessica must appear in list_kokoro_voices() unconditionally"


# ---------------------------------------------------------------------------
# SAPI 5 file synthesis helper
# ---------------------------------------------------------------------------


def test_synthesize_to_file_with_sapi5_saves_file(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "speech.wav"
    from quill.platform.windows import sapi5 as sapi5_mod

    calls: list[dict] = []

    def fake_synth_to_wav(text, path, *, voice_id="", rate_wpm=200, volume=1.0) -> None:
        calls.append({
            "text": text,
            "path": str(path),
            "voice": voice_id,
            "rate": rate_wpm,
            "vol": volume,
        })
        Path(path).write_bytes(b"")

    monkeypatch.setattr(sapi5_mod, "available", lambda: True)
    monkeypatch.setattr(sapi5_mod, "synthesize_to_wav", fake_synth_to_wav)
    synthesize_to_file_with_sapi5("Hello", output, voice="voice-1", rate=200, volume=1.0)
    assert calls == [
        {"text": "Hello", "path": str(output), "voice": "voice-1", "rate": 200, "vol": 1.0}
    ]


# ---------------------------------------------------------------------------
# DECtalk file synthesis helper
# ---------------------------------------------------------------------------


def test_synthesize_to_file_with_dectalk_invokes_dll_worker(monkeypatch, tmp_path: Path) -> None:
    # DECtalk synthesis is driven through DECtalk.dll by the console worker:
    # python dectalk_say.py --dll <DECtalk.dll> -w <out>, with the DECtalk
    # payload (voice + rate command + text) supplied on stdin as cp1252.
    dll = tmp_path / "DECtalk.dll"
    dll.write_text("binary", encoding="utf-8")
    output = tmp_path / "speech.wav"

    class Completed:
        returncode = 0
        stdout = b""
        stderr = b""

    called: dict[str, object] = {}

    def fake_run(command, **kwargs):
        called["command"] = command
        called["input"] = kwargs.get("input")
        return Completed()

    monkeypatch.setattr(read_aloud_module.subprocess, "run", fake_run)
    synthesize_to_file_with_dectalk("Hello", output, executable_path=dll, voice="paul", rate=200)
    cmd = called["command"]
    assert "dectalk_say.py" in cmd[1]
    assert "--dll" in cmd and str(dll) in cmd
    assert "-w" in cmd and str(output) in cmd
    assert "-wav" not in cmd and "-file" not in cmd and "-dict" not in cmd
    payload = called["input"].decode("cp1252")
    assert "[:np]" in payload and "[:ra 200]" in payload and "Hello" in payload


# ---------------------------------------------------------------------------
# Piper voice list from directory
# ---------------------------------------------------------------------------


def test_list_piper_voices_finds_onnx_files(tmp_path: Path) -> None:
    (tmp_path / "en_US-amy-medium.onnx").write_text("model", encoding="utf-8")
    (tmp_path / "en_GB-alan-low.onnx").write_text("model", encoding="utf-8")
    voices = list_piper_voices(str(tmp_path))
    names = {v.name for v in voices}
    assert "en_US-amy-medium" in names
    assert "en_GB-alan-low" in names


def test_list_piper_voices_empty_when_no_dir() -> None:
    assert list_piper_voices("") == []
    assert list_piper_voices("/nonexistent/path") == []


# ---------------------------------------------------------------------------
# Settings round-trip: new fields
# ---------------------------------------------------------------------------


def test_settings_round_trip_all_engine_fields() -> None:
    from quill.core.settings import Settings

    data = {
        "read_aloud_engine": "espeak",
        "read_aloud_espeak_voice": "en-gb",
        "read_aloud_espeak_rate": 160,
        "read_aloud_kokoro_voice": "am_adam",
        "read_aloud_kokoro_speed": 1.25,
        "read_aloud_piper_model_dir": "/models/piper",
    }
    s = Settings.from_dict(data)
    assert s.read_aloud_engine == "espeak"
    assert s.read_aloud_espeak_voice == "en-gb"
    assert s.read_aloud_espeak_rate == 160
    assert s.read_aloud_kokoro_voice == "am_adam"
    assert abs(s.read_aloud_kokoro_speed - 1.25) < 0.001
    assert s.read_aloud_piper_model_dir == "/models/piper"


def test_settings_rejects_unknown_engine() -> None:
    from quill.core.settings import Settings

    s = Settings.from_dict({"read_aloud_engine": "bananavoice"})
    assert s.read_aloud_engine == "sapi5"


def test_settings_clamps_espeak_rate() -> None:
    from quill.core.settings import Settings

    s_low = Settings.from_dict({"read_aloud_espeak_rate": 10})
    s_high = Settings.from_dict({"read_aloud_espeak_rate": 999})
    assert s_low.read_aloud_espeak_rate == 80
    assert s_high.read_aloud_espeak_rate == 450


def test_settings_clamps_kokoro_speed() -> None:
    from quill.core.settings import Settings

    s_low = Settings.from_dict({"read_aloud_kokoro_speed": 0.1})
    s_high = Settings.from_dict({"read_aloud_kokoro_speed": 5.0})
    assert s_low.read_aloud_kokoro_speed == 0.5
    assert s_high.read_aloud_kokoro_speed == 2.0


# ---------------------------------------------------------------------------
# Controller: all engines reach error when executable missing
# ---------------------------------------------------------------------------


def test_controller_espeak_raises_when_not_found(tmp_path: Path, monkeypatch) -> None:
    # Isolate discovery so a dev machine with eSpeak installed still exercises
    # the not-found path.
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(read_aloud_module.shutil, "which", lambda _name: None)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    controller = ReadAloudController()
    try:
        controller.start(
            "Hello",
            0,
            "",
            engine_name="espeak",
            espeak_executable="/nonexistent/espeak-ng.exe",
            espeak_voice="en",
        )
    except ReadAloudUnavailableError as exc:
        assert "eSpeak-NG" in str(exc)
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


def test_controller_piper_raises_when_model_missing(tmp_path: Path) -> None:
    exe = tmp_path / "piper.exe"
    exe.write_text("binary", encoding="utf-8")
    controller = ReadAloudController()
    try:
        controller.start(
            "Hello",
            0,
            "",
            engine_name="piper",
            piper_executable=str(exe),
            piper_model="/nonexistent/voice.onnx",
        )
    except ReadAloudUnavailableError as exc:
        assert "model" in str(exc).lower()
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


# ---------------------------------------------------------------------------
# M-14: wall-clock timeout for DECtalk / eSpeak
# ---------------------------------------------------------------------------


def test_dectalk_killed_after_wall_clock_timeout(monkeypatch, tmp_path: Path) -> None:
    import subprocess

    import quill.core.read_aloud as _ra

    monkeypatch.setattr(_ra, "_MAX_SYNTHESIS_SECONDS", 0.05)

    # DECtalk synthesis runs the console worker via subprocess.run with a
    # timeout; a TimeoutExpired must surface as ReadAloudUnavailableError.
    dll = tmp_path / "DECtalk.dll"
    dll.write_text("binary", encoding="utf-8")
    output = tmp_path / "speech.wav"

    def _raise_timeout(*_a, **_kw):
        raise subprocess.TimeoutExpired(cmd="dectalk_say", timeout=0.05)

    monkeypatch.setattr(_ra.subprocess, "run", _raise_timeout)

    from quill.core.read_aloud import ReadAloudUnavailableError, synthesize_to_file_with_dectalk

    try:
        synthesize_to_file_with_dectalk("hello", output, executable_path=dll, voice="paul")
    except ReadAloudUnavailableError as exc:
        assert "did not complete" in str(exc)
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


# ---------------------------------------------------------------------------
# M-15: Piper long text via temp file (not stdin pipe)
# ---------------------------------------------------------------------------


def test_piper_long_text_via_temp_file(monkeypatch, tmp_path: Path) -> None:
    import quill.core.read_aloud as _ra

    exe = tmp_path / "piper.exe"
    model = tmp_path / "voice.onnx"
    output = tmp_path / "out.wav"
    exe.write_text("x", encoding="utf-8")
    model.write_text("m", encoding="utf-8")

    stdin_objects: list[object] = []

    class _Done:
        returncode = 0
        stdout = b""
        stderr = b""

    def _fake_run(_cmd, *, stdin, capture_output, check, timeout, creationflags=0):
        stdin_objects.append(stdin)
        return _Done()

    monkeypatch.setattr(_ra.subprocess, "run", _fake_run)

    long_text = "word " * 20000
    _ra.synthesize_with_piper(long_text, output, executable_path=exe, model_path=model)

    assert stdin_objects, "subprocess.run must be called"
    assert hasattr(stdin_objects[0], "read"), "stdin must be a file object, not a pipe"


def test_kokoro_onnx_instance_is_cached(tmp_path, monkeypatch):
    """The kokoro-onnx model is built once and reused across calls (efficiency)."""
    import sys
    import types

    builds: list[int] = []

    class _FakeKokoro:
        def __init__(self, model_path: str, voices_path: str) -> None:
            builds.append(1)

        def create(self, text, voice, speed, lang):  # pragma: no cover - unused here
            return ([0.0], 24000)

    fake_mod = types.ModuleType("kokoro_onnx")
    fake_mod.Kokoro = _FakeKokoro  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "kokoro_onnx", fake_mod)

    read_aloud_module.clear_kokoro_cache()
    a = read_aloud_module._get_cached_kokoro_onnx(tmp_path)
    b = read_aloud_module._get_cached_kokoro_onnx(tmp_path)
    assert a is b
    assert sum(builds) == 1  # built only once

    read_aloud_module.clear_kokoro_cache()
    c = read_aloud_module._get_cached_kokoro_onnx(tmp_path)
    assert c is not a
    assert sum(builds) == 2  # rebuilt after clear


def test_read_aloud_controller_applies_pronunciation():
    """Live Read Aloud applies the active pronunciation set per sentence."""
    from quill.core.speech.pronunciation import PronunciationDictionary, PronunciationEntry

    controller = read_aloud_module.ReadAloudController()
    # no dictionaries -> sentence unchanged
    assert controller._apply_pronunciation("Say QUILL now.") == "Say QUILL now."
    # with a respelling -> applied
    controller._pron_engine = "kokoro"
    controller._pron_dicts = [
        PronunciationDictionary(
            id="d", entries=[PronunciationEntry(term="QUILL", replacement="kwill")]
        )
    ]
    assert controller._apply_pronunciation("Say QUILL now.") == "Say kwill now."


def test_read_aloud_controller_emits_ssml_on_capable_engine():
    """On SAPI 5, an SSML entry produces a <speak> utterance (skips verbalize)."""
    from quill.core.speech.pronunciation import PronunciationDictionary, PronunciationEntry

    controller = read_aloud_module.ReadAloudController()
    controller._pron_engine = "sapi5"
    controller._pron_dicts = [
        PronunciationDictionary(
            id="d",
            entries=[
                PronunciationEntry(
                    term="SQL",
                    replacement='<sub alias="sequel">SQL</sub>',
                    mode="ssml",
                    plain_fallback="sequel",
                )
            ],
        )
    ]
    out = controller._apply_pronunciation("Learn SQL.")
    assert out.startswith("<speak>") and '<sub alias="sequel">SQL</sub>' in out
