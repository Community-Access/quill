from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from quill.core.speech import models
from quill.core.speech.provider import SpeechError, SpeechModelInfo, TranscriptionRequest
from quill.core.speech.providers import whispercpp

_SAMPLE_JSON = json.dumps({
    "result": {"language": "en"},
    "transcription": [
        {"offsets": {"from": 0, "to": 2500}, "text": " Hello world"},
        {"offsets": {"from": 2500, "to": 4000}, "text": " second line"},
    ],
})


@pytest.fixture(autouse=True)
def _isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path)


# --- pure helpers ---------------------------------------------------------- #


def test_parse_whisper_json() -> None:
    result = whispercpp.parse_whisper_json(_SAMPLE_JSON)
    assert result.full_text == "Hello world second line"
    assert result.language == "en"
    assert len(result.segments) == 2
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[0].end_seconds == 2.5
    assert result.duration_seconds == 4.0


def test_parse_whisper_json_bad_input_raises() -> None:
    with pytest.raises(SpeechError):
        whispercpp.parse_whisper_json("{ not json")


def test_build_whisper_command_includes_flags(tmp_path: Path) -> None:
    request = TranscriptionRequest(
        source_path=tmp_path / "a.wav",
        model_id="small",
        language="en",
        translate_to_english=True,
    )
    args = whispercpp.build_whisper_command(
        "whisper-cli", tmp_path / "ggml-small.bin", tmp_path / "a.wav", tmp_path / "out", request
    )
    assert args[0] == "whisper-cli"
    assert "-oj" in args
    assert args[args.index("-l") + 1] == "en"
    assert "-tr" in args


def test_resolve_executable_honors_allowed_configured(tmp_path: Path) -> None:
    exe = tmp_path / "whisper-cli"
    exe.write_text("", encoding="utf-8")
    assert whispercpp.resolve_whisper_executable(str(exe)) == str(exe)


def test_resolve_executable_rejects_disallowed_basename(tmp_path: Path) -> None:
    evil = tmp_path / "rm-rf"
    evil.write_text("", encoding="utf-8")
    assert whispercpp.resolve_whisper_executable(str(evil)) is None


def test_resolve_executable_rejects_openai_whisper_cli(tmp_path: Path) -> None:
    # Issue #931: the bare ``whisper.exe`` is the openai-whisper PyPI package
    # CLI, not whisper.cpp. Accepting it made QUILL feed whisper.cpp flags
    # (-m/-f/-oj/-of) to a program that speaks --model/--output_format, so its
    # argparse exited with code 2 ("Transcription failed (code 2)"). It must be
    # rejected on the configured path, in bundled dirs, and on PATH.
    fake = tmp_path / "whisper.exe"
    fake.write_text("", encoding="utf-8")
    assert whispercpp.resolve_whisper_executable(str(fake)) is None
    bare = tmp_path / "whisper"
    bare.write_text("", encoding="utf-8")
    assert whispercpp.resolve_whisper_executable(str(bare)) is None


def test_resolve_executable_does_not_pick_openai_whisper_in_engine_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A bare ``whisper.exe`` sitting in the QUILL-managed engine dir must not be
    # mistaken for whisper.cpp (issue #931). Only whisper-cli / main qualify.
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: None)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    engine_dir = tmp_path / "speech-engine"
    engine_dir.mkdir(parents=True)
    (engine_dir / "whisper.exe").write_text("", encoding="utf-8")
    assert whispercpp.resolve_whisper_executable() is None


def test_resolve_executable_does_not_pick_openai_whisper_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # If only the openai-whisper ``whisper``/``whisper.exe`` is on PATH, QUILL
    # reports "not installed" rather than running the wrong CLI (issue #931).
    monkeypatch.setattr(
        whispercpp.shutil,
        "which",
        lambda name: str(tmp_path / "whisper.exe") if name in ("whisper", "whisper.exe") else None,
    )
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert whispercpp.resolve_whisper_executable() is None


def test_resolve_executable_finds_bundled_under_app_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: None)
    bundled = tmp_path / "app" / "tools" / "speech" / "whispercpp"
    bundled.mkdir(parents=True)
    exe = bundled / "whisper-cli.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    assert whispercpp.resolve_whisper_executable() == str(exe)


def test_resolve_executable_finds_downloaded_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: None)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    engine_dir = tmp_path / "speech-engine"
    engine_dir.mkdir(parents=True)
    exe = engine_dir / "whisper-cli"
    exe.write_text("", encoding="utf-8")
    assert whispercpp.resolve_whisper_executable() == str(exe)


def test_resolve_executable_uses_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        whispercpp.shutil,
        "which",
        lambda name: "/usr/bin/whisper-cli" if name == "whisper-cli" else None,
    )
    assert whispercpp.resolve_whisper_executable() == "/usr/bin/whisper-cli"


# --- provider behavior ----------------------------------------------------- #


def test_get_install_status_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: None)
    provider = whispercpp.WhisperCppProvider()
    assert provider.is_available() is False
    assert provider.get_install_status().installed is False


def test_download_blocked_in_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    provider = whispercpp.WhisperCppProvider()
    with pytest.raises(SpeechError, match="Safe Mode"):
        provider.download_model("small")


def test_download_records_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    def _fake_download(info, target, progress):
        Path(target).write_bytes(b"FAKEMODEL")

    monkeypatch.setattr(whispercpp, "_download_to_file", _fake_download)
    provider = whispercpp.WhisperCppProvider()
    installed = provider.download_model("small")
    assert installed.id == "small"
    assert installed.path.exists()
    assert provider.list_installed_models()[0].id == "small"


def _sample_model_info(sha256: str) -> SpeechModelInfo:
    return SpeechModelInfo(
        id="small",
        display_name="Small",
        language_mode="multilingual",
        approximate_size_mb=465,
        accuracy_tier="medium",
        speed_tier="medium",
        recommended_use="test",
        download_url="ggerganov/whisper.cpp",
        hf_filename="ggml-small.bin",
        revision="5359861c739e955e79d9a303bcbc70fb988958b1",
        sha256=hashlib.sha256(b"hello model bytes").hexdigest(),
    )


def test_transcribe_uses_bundled_model_when_no_downloaded_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The Offline Edition bundles the default model under QUILL_APP_ROOT;
    transcription must find and use it with no download step at all."""
    bundled = tmp_path / "app" / "speech-models-bundled" / "whispercpp" / "ggml-tiny.bin"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"bundled model")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    assert whispercpp._model_path("tiny") == bundled


def test_downloaded_copy_takes_priority_over_bundled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A user's own downloaded model (e.g. a fresher one) wins over the
    bundled copy shipped with the app -- same precedence as Kokoro's models."""
    bundled = tmp_path / "app" / "speech-models-bundled" / "whispercpp" / "ggml-tiny.bin"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"bundled model")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    downloaded = whispercpp._downloaded_model_path("tiny")
    downloaded.parent.mkdir(parents=True)
    downloaded.write_bytes(b"downloaded model")
    assert whispercpp._model_path("tiny") == downloaded


def test_bundled_whisper_model_path_none_without_app_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert whispercpp._bundled_whisper_model_path("tiny") is None


def test_bundled_whisper_model_path_none_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    assert whispercpp._bundled_whisper_model_path("tiny") is None


def test_remove_model_never_deletes_bundled_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Remove must only ever touch the user-downloaded copy -- the bundled
    model shipped with the Offline Edition installer is never writable/
    removable, matching how Kokoro's Remove works."""
    bundled = tmp_path / "app" / "speech-models-bundled" / "whispercpp" / "ggml-tiny.bin"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"bundled model")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    provider = whispercpp.WhisperCppProvider()
    provider.remove_model("tiny")
    assert bundled.is_file()  # untouched


def test_list_installed_models_synthesizes_bundled_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A bundled model (no download-time JSON record) still shows as
    installed in Manage Speech Models, same as a real download would."""
    bundled = tmp_path / "app" / "speech-models-bundled" / "whispercpp" / "ggml-tiny.bin"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"bundled model")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    provider = whispercpp.WhisperCppProvider()
    installed = provider.list_installed_models()
    assert any(m.id == "tiny" and m.path == bundled for m in installed)


def test_list_installed_models_prefers_recorded_over_bundled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A real, recorded download for a model id is never shadowed by a
    synthesized bundled entry for that same id."""
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    def _fake_download(info, target, progress):
        Path(target).write_bytes(b"FAKEMODEL")

    monkeypatch.setattr(whispercpp, "_download_to_file", _fake_download)
    bundled = tmp_path / "app" / "speech-models-bundled" / "whispercpp" / "ggml-tiny.bin"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"bundled model")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    provider = whispercpp.WhisperCppProvider()
    provider.download_model("tiny")
    installed = [m for m in provider.list_installed_models() if m.id == "tiny"]
    assert len(installed) == 1
    assert installed[0].installed_at  # the real, recorded entry, not the synthesized one


def test_download_to_file_uses_hf_hub_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    huggingface_hub = pytest.importorskip("huggingface_hub")

    payload = b"hello model bytes"
    calls: dict[str, object] = {}

    def _fake_hf_hub_download(**kwargs):
        calls.update(kwargs)
        cached = tmp_path / "cached" / kwargs["filename"]
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(payload)
        return str(cached)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)
    info = _sample_model_info(hashlib.sha256(payload).hexdigest())
    target = tmp_path / "ggml-small.bin"

    whispercpp._download_to_file(info, target, None)

    assert target.read_bytes() == payload
    assert calls["repo_id"] == "ggerganov/whisper.cpp"
    assert calls["filename"] == "ggml-small.bin"
    assert calls["revision"] == "5359861c739e955e79d9a303bcbc70fb988958b1"


def test_download_to_file_stale_pin_raises_coded_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    huggingface_hub = pytest.importorskip("huggingface_hub")
    from huggingface_hub.errors import EntryNotFoundError

    def _fake_hf_hub_download(**kwargs):
        raise EntryNotFoundError("404 for ggml-small.bin")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)
    info = _sample_model_info("0" * 64)
    target = tmp_path / "ggml-small.bin"

    with pytest.raises(SpeechError, match=r"\[QUILL-SPEECH-WHISPER-DL-404\]"):
        whispercpp._download_to_file(info, target, None)


def test_download_to_file_checksum_mismatch_raises_coded_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    huggingface_hub = pytest.importorskip("huggingface_hub")

    def _fake_hf_hub_download(**kwargs):
        cached = tmp_path / "cached" / kwargs["filename"]
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"wrong bytes")
        return str(cached)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)
    info = _sample_model_info(hashlib.sha256(b"expected bytes").hexdigest())
    target = tmp_path / "ggml-small.bin"

    with pytest.raises(SpeechError, match=r"\[QUILL-SPEECH-WHISPER-DL-CHK\]"):
        whispercpp._download_to_file(info, target, None)
    assert not target.exists()


def test_download_to_file_network_error_raises_coded_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    huggingface_hub = pytest.importorskip("huggingface_hub")

    def _fake_hf_hub_download(**kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)
    info = _sample_model_info("0" * 64)
    target = tmp_path / "ggml-small.bin"

    with pytest.raises(SpeechError, match=r"\[QUILL-SPEECH-WHISPER-DL-NET\]"):
        whispercpp._download_to_file(info, target, None)


def test_progress_tqdm_survives_no_console_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QUILL's bundled quill.exe is a windowed pythonw.exe with no console, so
    sys.stderr is None there. tqdm's own bar rendering defaults to writing to
    sys.stderr; calling update() must not crash with "'NoneType' object has no
    attribute 'write'" (regression guard for the whisper.cpp download failure
    with that exact message on a real bundled build)."""
    pytest.importorskip("tqdm")
    monkeypatch.setattr("sys.stderr", None)
    calls: list[tuple[float, str]] = []
    info = _sample_model_info("0" * 64)
    tqdm_cls = whispercpp._make_progress_tqdm(info, lambda f, m: calls.append((f, m)))
    assert tqdm_cls is not None
    bar = tqdm_cls(total=100, disable=False)
    try:
        bar.update(10)
        expected_fraction = 0.02 + 0.95 * min(10 / (465 * 1024 * 1024), 1.0)
        assert calls == [(pytest.approx(expected_fraction), "Downloading Small...")]
    finally:
        bar.close()


def test_transcribe_requires_installed_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: "/usr/bin/whisper-cli")
    provider = whispercpp.WhisperCppProvider()
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    with pytest.raises(SpeechError, match="not installed"):
        provider.transcribe_file(TranscriptionRequest(source_path=audio, model_id="small"))


def test_transcribe_runs_and_parses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: "/usr/bin/whisper-cli")
    # Install a fake model file.
    model_path = whispercpp._model_path("small")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"FAKE")
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")

    def _fake_run(args, *, timeout_seconds=0.0, cwd=None):
        # whisper writes <output_base>.json; -of is the arg after the flag.
        out_base = Path(args[args.index("-of") + 1])
        out_base.with_suffix(".json").write_text(_SAMPLE_JSON, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    import quill.stability.safe_subprocess as ssp

    monkeypatch.setattr(ssp, "run_subprocess_safely", _fake_run)
    # Force the no-ffmpeg path so a .wav passes straight through to whisper.cpp
    # (deterministic regardless of whether ffmpeg is on the test machine's PATH).
    from quill.core.speech import ffmpeg as ffmpeg_tools

    monkeypatch.setattr(ffmpeg_tools, "find_ffmpeg", lambda: None)

    provider = whispercpp.WhisperCppProvider()
    result = provider.transcribe_file(TranscriptionRequest(source_path=audio, model_id="small"))
    assert result.full_text == "Hello world second line"
    assert result.model_id == "small"


def test_transcribe_transcodes_non_wav_when_ffmpeg_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(whispercpp.shutil, "which", lambda _name: "/usr/bin/whisper-cli")
    model_path = whispercpp._model_path("small")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"FAKE")
    audio = tmp_path / "a.mp3"  # not a WAV -> must be transcoded first
    audio.write_bytes(b"ID3")

    from quill.core.speech import ffmpeg as ffmpeg_tools

    monkeypatch.setattr(ffmpeg_tools, "find_ffmpeg", lambda: "/usr/bin/ffmpeg")
    seen: dict[str, object] = {}

    def _fake_run(args, *, timeout_seconds=0.0, cwd=None):
        if args[0] == "/usr/bin/ffmpeg":  # the transcode call
            Path(args[-1]).write_bytes(b"RIFF")  # produce the WAV
            seen["transcoded_to"] = args[-1]
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        # the whisper call: whisper must be handed the transcoded WAV, not the mp3
        seen["whisper_audio"] = args[args.index("-f") + 1]
        out_base = Path(args[args.index("-of") + 1])
        out_base.with_suffix(".json").write_text(_SAMPLE_JSON, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    import quill.stability.safe_subprocess as ssp

    monkeypatch.setattr(ssp, "run_subprocess_safely", _fake_run)

    provider = whispercpp.WhisperCppProvider()
    result = provider.transcribe_file(TranscriptionRequest(source_path=audio, model_id="small"))
    assert result.full_text == "Hello world second line"
    assert str(seen["whisper_audio"]).endswith(".wav")  # whisper saw the WAV, not the mp3
    assert str(seen["transcoded_to"]).endswith(".wav")


def test_build_command_adds_tdrz_when_diarize(tmp_path: Path) -> None:
    request = TranscriptionRequest(
        source_path=tmp_path / "a.wav", model_id="small.en-tdrz", diarize=True
    )
    args = whispercpp.build_whisper_command(
        "whisper-cli", tmp_path / "m.bin", tmp_path / "a.wav", tmp_path / "out", request
    )
    assert "-tdrz" in args


def test_parse_assigns_speakers_on_turn_markers() -> None:
    payload = json.dumps({
        "result": {"language": "en"},
        "transcription": [
            {"offsets": {"from": 0, "to": 1000}, "text": " Hello there [SPEAKER_TURN]"},
            {"offsets": {"from": 1000, "to": 2000}, "text": " Hi back"},
        ],
    })
    result = whispercpp.parse_whisper_json(payload)
    assert result.segments[0].speaker == "Speaker 1"
    assert result.segments[0].text == "Hello there"  # marker stripped
    assert result.segments[1].speaker == "Speaker 2"


def test_parse_without_markers_has_no_speakers() -> None:
    result = whispercpp.parse_whisper_json(_SAMPLE_JSON)
    assert all(seg.speaker == "" for seg in result.segments)


def test_whisper_cpp_catalog_is_pinned_to_a_revision_with_hashes() -> None:
    from quill.core.speech import catalog

    # Every whisper.cpp model pins a commit (not "main") and a sha256 so the
    # download verifies integrity (#617 / HF supply-chain hardening).
    for model in catalog.WHISPER_CPP_MODELS:
        assert model.download_url and "/resolve/main/" not in model.download_url, model.id
        assert model.sha256 and len(model.sha256) == 64, model.id
        assert model.hf_filename, model.id
        assert model.revision and model.revision != "main", model.id
    # The tinydiarize model lives in its own repo, not ggerganov/whisper.cpp.
    tdrz = catalog.model_by_id("small.en-tdrz")
    assert tdrz is not None and "tinydiarize-whisper.cpp" in (tdrz.download_url or "")


def test_faster_whisper_catalog_pins_revisions() -> None:
    from quill.core.speech import catalog

    for model in catalog.FASTER_WHISPER_MODELS:
        assert model.revision and len(model.revision) == 40, model.id
