"""Kokoro through sherpa-onnx's ``OfflineTts`` (dict.md D-30) -- built, not switched on.

QUILL reads aloud with Kokoro through the ``kokoro-onnx`` package (a patched
wheel, its own onnxruntime session, and the phonemizer, espeakng-loader and
Babel chain). D-30 asked whether the sherpa-onnx runtime dictation already
ships could speak the same voices instead, and said to adopt only if every
shipped Kokoro voice and language is covered. Measured on 2026-10-17
(dictation design record section 35):

* **Covered.** sherpa-onnx's ``kokoro-int8-multi-lang-v1_0`` export carries all
  41 voices in :data:`quill.core.read_aloud.KOKORO_VOICES` (it has 54), and spoke
  every one of QUILL's seven languages intelligibly -- *once* the language is
  passed per call (``GenerationConfig.extra = {"lang": ...}``) and French is
  named ``fr``: the ``fr-fr`` code kokoro-onnx takes made sherpa-onnx return no
  audio at all. :func:`sherpa_lang` is that mapping.
* **Comparable cost.** One engine for every language; about the same peak
  memory as kokoro-onnx and a slightly longer load (the numbers are in the
  design record).
* **Not the same files.** sherpa-onnx needs its own export (the model with
  speaker metadata, its ``voices.bin``, lexicons and ``espeak-ng-data``), so
  switching means a new download for everyone who has Kokoro today.

So the engine is here and tested with fakes, and :data:`SHERPA_TTS_ADOPTED`
is ``False``: switching people's reading voice needs a listening comparison
by a person and a decision on that download (Jeff's), not a benchmark. Nothing
in the app imports this module yet.

wx-free. sherpa-onnx is passed in, never imported here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "SHERPA_TTS_ADOPTED",
    "SherpaKokoro",
    "build",
    "sherpa_lang",
]

#: Off until a person has compared the voices by ear and the download is decided.
SHERPA_TTS_ADOPTED = False

#: kokoro-onnx's espeak codes where sherpa-onnx wants another (measured
#: 2026-10-17: ``fr-fr`` gave no audio, ``fr`` gave French). English goes
#: through sherpa-onnx's own lexicons, which an empty code selects.
_SHERPA_CODES = {"fr-fr": "fr", "en-us": "", "en-gb": ""}


def sherpa_lang(voice: str) -> str:
    """The language sherpa-onnx needs for *voice*, from QUILL's own voice table."""
    from quill.core.voice_catalog import kokoro_lang_for_voice

    code = kokoro_lang_for_voice(voice)
    return _SHERPA_CODES.get(code, code)


@dataclass
class SherpaKokoro:
    """One sherpa-onnx Kokoro engine, every voice and language through it."""

    engine: Any
    speakers: Sequence[str]
    sherpa_onnx: Any

    def covers(self, voice: str) -> bool:
        return voice in self.speakers

    def speak(self, text: str, voice: str, *, speed: float = 1.0) -> tuple[Any, int]:
        """``(samples, sample_rate)`` for *text* in *voice*. Raises ``ValueError``
        for a voice the model does not have, never speaking in another one."""
        config = self.sherpa_onnx.GenerationConfig()
        config.sid = list(self.speakers).index(voice)
        config.speed = float(speed)
        lang = sherpa_lang(voice)
        if lang:
            config.extra = {"lang": lang}
        audio = self.engine.generate(text, config)
        return audio.samples, int(audio.sample_rate)


def build(
    sherpa_onnx: Any, folder: Path, speakers: Sequence[str], *, threads: int = 1
) -> SherpaKokoro:
    """The engine for the sherpa-onnx Kokoro export in *folder*. *speakers* is
    the export's ``speaker_names`` metadata, in speaker-id order."""
    model = sorted(folder.glob("model*.onnx"))[0]
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=str(model),
                voices=str(folder / "voices.bin"),
                tokens=str(folder / "tokens.txt"),
                lexicon=",".join(str(p) for p in sorted(folder.glob("lexicon-*.txt"))),
                data_dir=str(folder / "espeak-ng-data"),
                dict_dir=str(folder / "dict") if (folder / "dict").is_dir() else "",
                lang="",
            ),
            num_threads=threads,
            provider="cpu",
        ),
    )
    return SherpaKokoro(sherpa_onnx.OfflineTts(config), tuple(speakers), sherpa_onnx)
