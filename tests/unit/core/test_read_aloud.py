from __future__ import annotations

from pathlib import Path

from quill.core import read_aloud as read_aloud_module
from quill.core.read_aloud import (
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
from quill.core.voice_catalog import (
    KOKORO_VOICE_GRADES,
    KOKORO_VOICES,
    piper_voice_download_urls,
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


def test_read_aloud_controller_strips_markdown_before_synthesis(monkeypatch) -> None:
    """Live Read Aloud must not hand raw markdown syntax to a synthesis engine
    (fix.md #4) -- espeak-ng-based engines like Piper badly mis-tokenize
    literal '#'/'**'/'[text](url)' characters, sounding garbled or like the
    wrong language."""
    spoken = _record_sapi5_synth(monkeypatch)

    controller = ReadAloudController()
    controller.start("Read [this](https://example.com) **now**.", 0, "voice-1")
    assert controller._thread is not None
    controller._thread.join(timeout=2)

    assert [text for text, _voice in spoken] == ["Read this now."]


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
# ElevenLabs cloud read-aloud voice
# ---------------------------------------------------------------------------


def test_elevenlabs_read_aloud_blocked_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    controller = ReadAloudController()
    try:
        controller.start("Hello.", 0, "v1", engine_name="elevenlabs", elevenlabs_api_key="key")
    except ReadAloudUnavailableError as exc:
        assert "Safe Mode" in str(exc)
    else:
        raise AssertionError("Expected Safe Mode to block ElevenLabs read-aloud")


def test_elevenlabs_read_aloud_requires_a_key(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    controller = ReadAloudController()
    try:
        controller.start("Hello.", 0, "v1", engine_name="elevenlabs", elevenlabs_api_key="  ")
    except ReadAloudUnavailableError as exc:
        assert "Connect ElevenLabs" in str(exc)
    else:
        raise AssertionError("Expected a missing key to be rejected")


def test_elevenlabs_read_aloud_requires_the_sdk(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    from quill.core.ai import elevenlabs_tts

    monkeypatch.setattr(elevenlabs_tts, "available", lambda: False)
    controller = ReadAloudController()
    try:
        controller.start("Hello.", 0, "v1", engine_name="elevenlabs", elevenlabs_api_key="key")
    except ReadAloudUnavailableError as exc:
        assert "optional SDK" in str(exc) or "pip install" in str(exc)
    else:
        raise AssertionError("Expected the missing SDK to be reported")


def test_list_elevenlabs_voices_empty_without_key() -> None:
    assert read_aloud_module.list_elevenlabs_voices("") == []
    assert read_aloud_module.list_elevenlabs_voices("   ") == []


def test_list_elevenlabs_voices_maps_account_voices(monkeypatch) -> None:
    from quill.core.ai import elevenlabs_tts

    monkeypatch.setattr(elevenlabs_tts, "available", lambda: True)
    monkeypatch.setattr(
        elevenlabs_tts, "list_voices", lambda key: [("v1", "Rachel"), ("v2", "Adam")]
    )
    voices = read_aloud_module.list_elevenlabs_voices("key")
    assert [(v.id, v.name) for v in voices] == [("v1", "Rachel"), ("v2", "Adam")]


def test_list_elevenlabs_voices_swallows_errors(monkeypatch) -> None:
    from quill.core.ai import elevenlabs_tts

    def boom(_key: str) -> list:
        raise RuntimeError("network down")

    monkeypatch.setattr(elevenlabs_tts, "available", lambda: True)
    monkeypatch.setattr(elevenlabs_tts, "list_voices", boom)
    assert read_aloud_module.list_elevenlabs_voices("key") == []  # never raises into the UI


# ---------------------------------------------------------------------------
# eSpeak-NG helpers
# ---------------------------------------------------------------------------


def test_list_espeak_english_voices_covers_key_variants() -> None:
    voices = list_espeak_english_voices()
    ids = [v.id for v in voices]
    # 8 English lang definition files (lang/gmw/en*)
    assert "en-gb" in ids
    assert "en-us" in ids
    assert "en-gb-scotland" in ids
    assert "en-029" in ids
    assert len(ids) == 8
    assert all(id_.startswith("en") for id_ in ids)


def test_list_espeak_voices_adds_world_languages() -> None:
    voices = read_aloud_module.list_espeak_voices()
    ids = [v.id for v in voices]
    # English variants stay first and intact...
    assert ids[:8] == [v.id for v in list_espeak_english_voices()]
    # ...and the world languages follow (#813 follow-on: Italian read-aloud).
    for lang in ("it", "es", "fr-fr", "hi", "pt-br"):
        assert lang in ids, f"missing eSpeak world language {lang}"
    italian = next(v for v in voices if v.id == "it")
    assert italian.accent == "Italian"


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
        message = str(exc)
        # Names the actual fix first (#2 beta-2 fix pass), not just the
        # alternative pip+torch path.
        assert "Tools > Speech > Install Kokoro ONNX" in message
    else:
        raise AssertionError("Expected ReadAloudUnavailableError")


def test_kokoro_engine_ready_requires_package_not_just_models(monkeypatch) -> None:
    """kokoro_onnx_ready() alone only checks model files on disk; a UI wired to
    it alone can claim Kokoro is ready when the pip package was never
    installed (or its install failed) -- the actual bug behind #2."""
    from quill.core.speech import engine_install

    monkeypatch.setattr(read_aloud_module, "kokoro_onnx_ready", lambda *a, **k: True)
    monkeypatch.setattr(engine_install, "is_kokoro_onnx_available", lambda: False)
    assert read_aloud_module.kokoro_engine_ready() is False

    monkeypatch.setattr(engine_install, "is_kokoro_onnx_available", lambda: True)
    assert read_aloud_module.kokoro_engine_ready() is True

    monkeypatch.setattr(read_aloud_module, "kokoro_onnx_ready", lambda *a, **k: False)
    assert read_aloud_module.kokoro_engine_ready() is False


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
    # Spanish (3)
    "ef_dora",
    "em_alex",
    "em_santa",
    # French (1)
    "ff_siwis",
    # Hindi (4)
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
    # Italian (2)
    "if_sara",
    "im_nicola",
    # Brazilian Portuguese (3)
    "pf_dora",
    "pm_alex",
    "pm_santa",
}


def test_kokoro_voices_canonical_41() -> None:
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


def test_kokoro_voice_grades_cover_all_voices() -> None:
    ids = {vid for vid, _ in KOKORO_VOICES}
    assert ids == set(KOKORO_VOICE_GRADES.keys()), (
        "KOKORO_VOICE_GRADES must cover every voice in KOKORO_VOICES"
    )


def test_list_kokoro_voices_includes_italian_with_accent() -> None:
    voices = list_kokoro_voices()
    by_id = {v.id: v for v in voices}
    assert "if_sara" in by_id and "im_nicola" in by_id, "Italian Kokoro voices must be listed"
    assert by_id["if_sara"].accent == "Italian"
    assert by_id["im_nicola"].accent == "Italian"


def test_kokoro_lang_for_voice_maps_languages() -> None:
    lang_for = read_aloud_module.kokoro_lang_for_voice
    assert lang_for("af_heart") == "en-us"
    assert lang_for("bm_fable") == "en-gb"
    assert lang_for("if_sara") == "it"
    assert lang_for("ef_dora") == "es"
    assert lang_for("ff_siwis") == "fr-fr"
    assert lang_for("hf_alpha") == "hi"
    assert lang_for("pm_alex") == "pt-br"
    # Unknown prefixes fall back to en-us rather than raising.
    assert lang_for("xx_unknown") == "en-us"
    assert lang_for("") == "en-us"


def test_synthesize_with_kokoro_torch_fallback_uses_voice_lang_code(
    monkeypatch, tmp_path: Path
) -> None:
    """The kokoro+torch fallback must derive KPipeline's lang_code from the
    voice prefix, so a non-English voice never regresses to English "a"."""
    import sys
    import types

    import pytest

    # The fake pipeline yields numpy audio and the writer uses soundfile; both
    # are optional deps absent on the lean CI runner.
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")

    # Force the ONNX fast-path off so the torch fallback runs.
    monkeypatch.setattr(read_aloud_module, "kokoro_onnx_ready", lambda *a, **k: False)
    captured: list[str] = []

    class FakeKPipeline:
        def __init__(self, lang_code: str) -> None:
            captured.append(lang_code)

        def __call__(self, text, voice, speed):
            yield None, None, np.zeros(240, dtype="float32")

    monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=FakeKPipeline))
    read_aloud_module.synthesize_with_kokoro("Ciao a tutti", tmp_path / "it.wav", voice="if_sara")
    read_aloud_module.synthesize_with_kokoro("Hello there", tmp_path / "en.wav", voice="af_heart")
    read_aloud_module.synthesize_with_kokoro("Fallback", tmp_path / "xx.wav", voice="xx_odd")
    assert captured == ["i", "a", "a"]
    assert (tmp_path / "it.wav").exists()


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


def test_piper_catalog_includes_italian_voices(tmp_path: Path) -> None:
    voices = read_aloud_module.list_piper_catalog_voices(tmp_path)
    by_id = {v.id: v for v in voices}
    assert "it_IT-paola-medium" in by_id, "Italian Piper voice missing from catalog"
    assert "it_IT-riccardo-x_low" in by_id
    assert by_id["it_IT-paola-medium"].accent == "Italian"
    assert by_id["it_IT-paola-medium"].installed is False


def test_resolve_piper_model_path_matches_catalog_installed_check(tmp_path: Path) -> None:
    """The path Test/Preview synthesizes from must be the same file
    list_piper_catalog_voices() checked to decide the voice was installed --
    a bare voice id is not a path (regression guard for "Piper model file was
    not found" when previewing a voice the catalog already reports as
    downloaded)."""
    (tmp_path / "en_GB-alan-medium.onnx").write_text("model", encoding="utf-8")
    resolved = read_aloud_module.resolve_piper_model_path("en_GB-alan-medium", tmp_path)
    assert resolved == tmp_path / "en_GB-alan-medium.onnx"
    assert resolved.exists()


def test_piper_voice_download_urls_for_any_language() -> None:
    urls = piper_voice_download_urls("it_IT-paola-medium")
    assert urls is not None
    onnx_url, json_url = urls
    assert onnx_url == (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main"
        "/it/it_IT/paola/medium/it_IT-paola-medium.onnx"
    )
    assert json_url.endswith("/it_IT-paola-medium.onnx.json")
    # English ids keep the exact URL shape the downloader always used.
    urls_en = piper_voice_download_urls("en_US-amy-low")
    assert urls_en is not None
    assert urls_en[0] == (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main"
        "/en/en_US/amy/low/en_US-amy-low.onnx"
    )
    # Malformed ids return None so the UI can show a clear error.
    assert piper_voice_download_urls("not-a-voice") is None


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


def test_kokoro_onnx_failure_is_logged_before_torch_fallback(monkeypatch, tmp_path, caplog) -> None:
    """A downloaded Kokoro that fails at onnx synthesis (e.g. onnxruntime cannot
    load its native DLL) used to fall through to a generic "needs a component"
    error with the real cause silently swallowed -- the exact shape of the "I
    downloaded it, it says it worked, but voices still error" report. The true
    error must now be logged so Help > Save Diagnostics captures it.
    """
    import pytest

    monkeypatch.setattr(read_aloud_module, "kokoro_engine_ready", lambda *a, **k: True)

    def _boom(*_a, **_k):
        raise RuntimeError("onnxruntime DLL load failed")

    monkeypatch.setattr(read_aloud_module, "_get_cached_kokoro_onnx", _boom)

    with caplog.at_level("ERROR", logger="quill.core.read_aloud"):
        with pytest.raises(ReadAloudUnavailableError):
            read_aloud_module.synthesize_with_kokoro(
                "Hello from QUILL.", tmp_path / "out.wav", voice="af_heart"
            )

    assert any("Kokoro onnx synthesis failed" in r.getMessage() for r in caplog.records)


def test_worker_python_prefers_embedded_python_over_launcher(tmp_path, monkeypatch) -> None:
    """In a bundled build sys.executable is quill.exe (the launcher); the DECtalk
    worker must run through the embedded pythonw.exe beside it, or QUILL opens the
    worker .py as a document instead of running it."""
    import sys as _sys

    from quill.core import read_aloud

    launcher = tmp_path / "quill.exe"
    launcher.write_bytes(b"MZ")
    pyw = tmp_path / "pythonw.exe"
    pyw.write_bytes(b"MZ")
    monkeypatch.setattr(_sys, "executable", str(launcher))
    assert read_aloud._worker_python_executable() == str(pyw)


def test_worker_python_uses_sys_executable_when_it_is_python(tmp_path, monkeypatch) -> None:
    import sys as _sys

    from quill.core import read_aloud

    py = tmp_path / "python.exe"
    py.write_bytes(b"MZ")
    monkeypatch.setattr(_sys, "executable", str(py))
    assert read_aloud._worker_python_executable() == str(py)


# ---------------------------------------------------------------------------
# #28: live WAV playback must work on macOS (afplay), not just Windows
# (winsound). Before the cross-platform _LiveWavPlayer, the playback path gated
# on `if _winsound is not None` and silently dropped every synthesized WAV on
# macOS -- Piper/Kokoro/ElevenLabs Read Aloud was mute.
# ---------------------------------------------------------------------------


def test_detect_live_wav_backend_prefers_winsound(monkeypatch) -> None:
    monkeypatch.setattr(read_aloud_module, "_winsound", object())  # non-None sentinel
    assert read_aloud_module._detect_live_wav_backend() == "winsound"


def test_detect_live_wav_backend_falls_back_to_afplay_on_macos(monkeypatch) -> None:
    import sys as _sys

    monkeypatch.setattr(read_aloud_module, "_winsound", None)
    monkeypatch.setattr(_sys, "platform", "darwin")
    monkeypatch.setattr(read_aloud_module.shutil, "which", lambda name: "/usr/bin/afplay")
    assert read_aloud_module._detect_live_wav_backend() == "afplay"


def test_detect_live_wav_backend_empty_when_nothing_available(monkeypatch) -> None:
    import sys as _sys

    monkeypatch.setattr(read_aloud_module, "_winsound", None)
    monkeypatch.setattr(_sys, "platform", "linux")
    assert read_aloud_module._detect_live_wav_backend() == ""


def test_live_wav_player_afplay_invokes_subprocess(monkeypatch, tmp_path) -> None:
    """On the afplay backend, play() runs `afplay <path>` and blocks until it
    exits; stop() terminates a running process."""

    started: list[list[str]] = []

    class _FakeProc:
        def __init__(self) -> None:
            self._terminated = False

        def wait(self) -> int:
            return 0

        def terminate(self) -> None:
            self._terminated = True

    proc = _FakeProc()

    def fake_popen(cmd, *args, **kwargs):  # noqa: ANN001
        started.append(cmd)
        return proc

    monkeypatch.setattr(read_aloud_module.subprocess, "Popen", fake_popen)

    player = read_aloud_module._LiveWavPlayer(backend="afplay")
    wav = tmp_path / "sentence.wav"
    wav.write_bytes(b"fake-wav")

    player.play(wav)
    assert started == [["afplay", str(wav)]]

    # stop() on an idle player (proc already cleared after wait) is a no-op.
    player.stop()


def test_live_wav_player_stop_terminates_running_afplay(monkeypatch, tmp_path) -> None:
    import threading

    class _FakeProc:
        def __init__(self) -> None:
            self.terminated = False
            self._wait_ready = threading.Event()
            self._wait_release = threading.Event()

        def wait(self) -> int:
            self._wait_ready.set()
            self._wait_release.wait(timeout=5)
            return 0

        def terminate(self) -> None:
            self.terminated = True
            self._wait_release.set()

    proc = _FakeProc()

    monkeypatch.setattr(read_aloud_module.subprocess, "Popen", lambda *a, **k: proc)

    player = read_aloud_module._LiveWavPlayer(backend="afplay")
    wav = tmp_path / "s.wav"
    wav.write_bytes(b"x")

    play_done = threading.Event()

    def _play() -> None:
        player.play(wav)
        play_done.set()

    t = threading.Thread(target=_play, daemon=True)
    t.start()
    # Wait until the player's wait() is blocking on the running proc, then stop()
    # must terminate it (and unblock wait()).
    proc._wait_ready.wait(timeout=2)
    player.stop()
    t.join(timeout=2)
    assert proc.terminated


def test_live_wav_player_no_backend_is_silent_noop(tmp_path) -> None:
    player = read_aloud_module._LiveWavPlayer(backend="")
    assert player.available is False
    player.play(tmp_path / "none.wav")  # must not raise
    player.stop()
