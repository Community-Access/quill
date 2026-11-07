"""D-30's sherpa-onnx Kokoro engine: built, off, and tested with a fake sherpa-onnx."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import sherpa_kokoro as sk
from quill.core.read_aloud import KOKORO_VOICES


class _Config(SimpleNamespace):
    pass


class _Engine:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.calls: list[tuple[str, Any]] = []

    def generate(self, text: str, config: Any) -> Any:
        self.calls.append((text, config))
        return SimpleNamespace(samples=[0.0, 0.1], sample_rate=24_000)


def _fake() -> Any:
    return SimpleNamespace(
        OfflineTtsConfig=_Config,
        OfflineTtsModelConfig=_Config,
        OfflineTtsKokoroModelConfig=_Config,
        OfflineTts=_Engine,
        GenerationConfig=_Config,
    )


def _folder(tmp_path: Path) -> Path:
    for name in ("model.int8.onnx", "voices.bin", "tokens.txt", "lexicon-us-en.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    (tmp_path / "espeak-ng-data").mkdir()
    return tmp_path


def test_it_is_not_adopted() -> None:
    assert sk.SHERPA_TTS_ADOPTED is False


def test_french_is_named_as_sherpa_onnx_needs_and_english_uses_the_lexicons() -> None:
    assert sk.sherpa_lang("ff_siwis") == "fr"  # fr-fr gave no audio (2026-10-17)
    assert sk.sherpa_lang("af_heart") == "" and sk.sherpa_lang("bf_emma") == ""
    assert sk.sherpa_lang("ef_dora") == "es"
    assert sk.sherpa_lang("pf_dora") == "pt-br"


def test_one_engine_speaks_every_language_per_call(tmp_path: Path) -> None:
    speakers = ["af_heart", "ff_siwis", "ef_dora"]
    engine = sk.build(_fake(), _folder(tmp_path), speakers)
    samples, rate = engine.speak("Bonjour", "ff_siwis", speed=1.2)
    assert rate == 24_000 and samples == [0.0, 0.1]
    _text, config = engine.engine.calls[-1]
    assert config.sid == 1 and config.speed == 1.2 and config.extra == {"lang": "fr"}
    engine.speak("Hello", "af_heart")
    assert not hasattr(engine.engine.calls[-1][1], "extra")
    kokoro = engine.engine.config.model.kokoro
    assert kokoro.lang == "" and kokoro.lexicon.endswith("lexicon-us-en.txt")


def test_a_voice_the_model_lacks_is_refused_not_swapped(tmp_path: Path) -> None:
    engine = sk.build(_fake(), _folder(tmp_path), ["af_heart"])
    assert engine.covers("af_heart") and not engine.covers("bm_george")
    with pytest.raises(ValueError):
        engine.speak("Hello", "bm_george")


def test_every_shipped_voice_has_a_sherpa_language() -> None:
    for voice, _label in KOKORO_VOICES:
        assert sk.sherpa_lang(voice) != "fr-fr"
