"""Phonon 31m engine: discovery, the CPU guard, voices, rate and dispatch.

The real model is ~75 MB and only staged on build machines, so everything
here fakes the folder and the ``ptts`` module except the last test, which
speaks one sentence from the staged model with sockets blocked (R-41) and is
skipped where the model is absent.
"""

from __future__ import annotations

import json
import socket
import sys
import types
import wave
from pathlib import Path

import pytest

from quill.core import read_aloud
from quill.core.speech import phonon_tts


def _fake_model(root: Path, voices: tuple[str, ...] = ("Zoey", "Alfie")) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name in ("model.q8.gguf", "config.json", "tokenizer.json", "default-voice.safetensors"):
        (root / name).write_bytes(b"x")
    (root / "voices").mkdir(exist_ok=True)
    lines = []
    for name in voices:
        (root / "voices" / f"{name}.safetensors").write_bytes(b"v")
        lines.append(
            json.dumps({
                "filename": f"voices/{name}.safetensors",
                "name": name,
                "language": "en",
                "description": f"{name} voice",
            })
        )
    # A catalogue entry whose file is absent must not be offered.
    lines.append(json.dumps({"filename": "voices/Gone.safetensors", "name": "Gone"}))
    (root / "voices.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


@pytest.fixture
def model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = _fake_model(tmp_path / "phonon-models" / "en")
    monkeypatch.setattr(phonon_tts, "_candidate_dirs", lambda: [tmp_path / "nowhere", root])
    return root


def test_model_dir_is_the_first_complete_folder(model_dir: Path) -> None:
    assert phonon_tts.default_phonon_model_dir() == model_dir
    assert phonon_tts.phonon_model_ready()


def test_incomplete_folder_is_not_a_model(tmp_path: Path) -> None:
    root = _fake_model(tmp_path / "m")
    (root / "tokenizer.json").unlink()
    assert not phonon_tts.phonon_model_ready(root)


def test_voices_default_first_then_sorted_and_present_only(model_dir: Path) -> None:
    names = [v.name for v in phonon_tts.list_phonon_voices()]
    assert names == ["Default", "Alfie", "Zoey"]


def test_status_names_the_reason(model_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phonon_tts, "ptts_importable", lambda: True)
    monkeypatch.setattr(phonon_tts, "cpu_supported", lambda: True)
    assert phonon_tts.phonon_status() == "ready"
    monkeypatch.setattr(phonon_tts, "ptts_importable", lambda: False)
    assert phonon_tts.phonon_status() == "engine"
    monkeypatch.setattr(phonon_tts, "cpu_supported", lambda: False)
    assert phonon_tts.phonon_status() == "cpu"
    assert "processor" in phonon_tts.unavailable_message("cpu")
    assert "Piper" in phonon_tts.unavailable_message("cpu")


def test_old_cpu_is_refused_before_anything_imports(
    model_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A CPU without AVX2 must never reach ``import ptts`` (R-8)."""
    monkeypatch.setattr(phonon_tts, "cpu_supported", lambda: False)
    monkeypatch.setitem(sys.modules, "ptts", None)  # an import would raise ImportError
    with pytest.raises(read_aloud.PhononUnavailableError):
        phonon_tts.synthesize_with_phonon("Hello.", tmp_path / "o.wav")
    with pytest.raises(read_aloud.PhononUnavailableError):
        read_aloud.ReadAloudController().start("Hello.", 0, "", engine_name="phonon")


def test_speed_maps_inside_the_range_the_model_holds() -> None:
    assert phonon_tts.duration_delta_for_speed(1.0) == 0.0
    assert phonon_tts.duration_delta_for_speed(1.3) == -0.5
    assert phonon_tts.duration_delta_for_speed(0.85) == 0.5
    # Out of range clamps rather than asking the model for speech it breaks on.
    assert phonon_tts.duration_delta_for_speed(2.0) == -0.5
    assert phonon_tts.duration_delta_for_speed(0.5) == 0.5
    faster = [phonon_tts.duration_delta_for_speed(s / 100) for s in range(85, 131)]
    assert faster == sorted(faster, reverse=True)


def test_cpu_check_on_this_machine_does_not_raise() -> None:
    assert isinstance(phonon_tts.cpu_supported(), bool)


class _FakeTTS:
    instances = 0

    def __init__(self, **kwargs: object) -> None:
        type(self).instances += 1
        self.kwargs = kwargs
        self.conditions: dict[str, object] = {}
        self.calls: list[tuple[str, object]] = []
        self.sample_rate = 24000

    def set_conditions(self, conditions: dict[str, object]) -> None:
        self.conditions = dict(conditions)

    def synth(self, text: str, *, voice: object = None) -> list[float]:
        self.calls.append((text, voice))
        return [0.0, 0.5, -0.5]


@pytest.fixture
def fake_ptts(model_dir: Path, monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    pytest.importorskip("numpy")  # ptts depends on it; the CI unit image has neither
    module = types.ModuleType("ptts")
    module.TTS = _FakeTTS  # type: ignore[attr-defined]
    module.threads = []  # type: ignore[attr-defined]
    module.set_num_threads = module.threads.append  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ptts", module)
    monkeypatch.setattr(phonon_tts, "ptts_importable", lambda: True)
    monkeypatch.setattr(phonon_tts, "cpu_supported", lambda: True)
    monkeypatch.setattr(phonon_tts, "_THREADS_SET", False)
    _FakeTTS.instances = 0
    phonon_tts.clear_phonon_cache()
    yield module
    phonon_tts.clear_phonon_cache()


def test_synthesis_is_local_cached_and_writes_a_wav(
    fake_ptts: types.ModuleType, model_dir: Path, tmp_path: Path
) -> None:
    out = tmp_path / "a.wav"
    phonon_tts.synthesize_with_phonon("Hello there.", out, voice="Zoey", speed=1.3)
    phonon_tts.synthesize_with_phonon("Again.", tmp_path / "b.wav")
    assert _FakeTTS.instances == 1
    tts = next(iter(phonon_tts._CACHE.values()))
    # Always a local folder and a local catalogue: never the Hub (R-9).
    assert tts.kwargs["model"] == str(model_dir)
    assert tts.kwargs["voice_catalog"] == str(model_dir / "voices.jsonl")
    assert tts.calls == [("Hello there.", "Zoey"), ("Again.", None)]
    assert tts.conditions == {"duration_delta": 0.0}
    assert len(fake_ptts.threads) == 1  # type: ignore[attr-defined]
    with wave.open(str(out)) as handle:
        assert handle.getframerate() == 24000
        assert handle.getnframes() == 3


def test_long_passages_are_split_on_sentences(fake_ptts: types.ModuleType, tmp_path: Path) -> None:
    text = " ".join(f"This is sentence number {n} of a long chapter." for n in range(60))
    phonon_tts.synthesize_with_phonon(text, tmp_path / "c.wav")
    tts = next(iter(phonon_tts._CACHE.values()))
    assert len(tts.calls) > 1
    assert all(len(piece) <= 600 for piece, _ in tts.calls)
    assert "".join(piece for piece, _ in tts.calls) == text


def test_read_aloud_lists_phonon_voices(fake_ptts: types.ModuleType) -> None:
    voices = read_aloud.list_phonon_voices()
    assert [v.id for v in voices] == ["default", "Alfie", "Zoey"]
    assert all(v.installed for v in voices)


def test_batch_export_dispatches_to_phonon(fake_ptts: types.ModuleType, tmp_path: Path) -> None:
    from quill.core.speech import batch_export

    opts = batch_export.BatchExportOptions(tmp_path, tmp_path, engine="phonon")
    opts.phonon_voice = "Alfie"
    opts.phonon_speed = 0.85
    out = tmp_path / "d.wav"
    batch_export._synthesize_one("Chapter one.", out, opts)
    tts = next(iter(phonon_tts._CACHE.values()))
    assert tts.calls == [("Chapter one.", "Alfie")]
    assert tts.conditions == {"duration_delta": 0.5}
    assert "phonon" in batch_export._SINGLE_THREAD_ENGINES


def test_document_speech_makes_a_phonon_synthesizer(
    fake_ptts: types.ModuleType, tmp_path: Path
) -> None:
    from quill.core.speech.document_speech import SynthesisSpec, make_synthesizer

    synth = make_synthesizer(SynthesisSpec(engine="phonon", voice="Zoey", speed=1.0))
    synth("Hello.", tmp_path / "e.wav")
    assert (tmp_path / "e.wav").is_file()


def test_project_profile_carries_phonon_voice_and_speed() -> None:
    from quill.core.speech import project_profile

    assert "phonon" in project_profile._VALID_ENGINES


def test_settings_round_trip_and_clamp(tmp_path: Path) -> None:
    from quill.core.settings import Settings

    s = Settings.from_dict({"read_aloud_phonon_voice": "Zoey", "read_aloud_phonon_speed": 5})
    assert s.read_aloud_phonon_voice == "Zoey"
    assert s.read_aloud_phonon_speed == 1.3
    assert Settings.from_dict({}).read_aloud_phonon_voice == "default"


_STAGED = Path(__file__).resolve().parents[4] / "build" / "deps" / "phonon-31m-en"


@pytest.mark.skipif(
    not (_STAGED / "model.q8.gguf").is_file() or not phonon_tts.ptts_importable(),
    reason="Phonon model not staged (scripts/fetch_build_deps.py --only phonon)",
)
def test_real_model_speaks_with_the_network_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not phonon_tts.cpu_supported():
        pytest.skip("this CPU cannot run Phonon")

    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("Phonon tried to reach the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    out = tmp_path / "real.wav"
    phonon_tts.synthesize_with_phonon("Hello.", out, voice="Zoey", model_dir=_STAGED)
    with wave.open(str(out)) as handle:
        assert handle.getnframes() > 2400
