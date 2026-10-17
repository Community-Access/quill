"""Punctuation and speaker labels on the shared sherpa-onnx layer (dict.md D-29).

Two passes that run *after* recognition, on any engine's text or a recording's
audio, through the same sherpa-onnx runtime every local model already uses:

* **Punctuation** -- sherpa-onnx's ``OfflinePunctuation`` (a CT-Transformer),
  for engines that write no marks of their own: Windows speech recognition
  optionally, and Zipformer transducers if they join the catalogue. Every model
  dictation offers today punctuates by itself, so nothing needs it yet.
* **Speaker labels** -- sherpa-onnx's ``OfflineSpeakerDiarization`` (pyannote
  segmentation plus a speaker-embedding model, clustered), for Transcribe a
  Recording's "Speaker 1:" labels in QUILL, QUILL Lite and QUILL Transcribe,
  replacing whisper.cpp's tinydiarize and, for local use, the gated pyannote
  Quillin.

**Built, not switched on.** dict.md says both are gated: the punctuation
model's English quality is unverified (gate it on the real-voice benchmark,
B-1), and the speaker models' sizes, licences and memory on the 8 GB machine
are unmeasured. So :data:`PUNCTUATION_ADOPTED` and :data:`SPEAKERS_ADOPTED`
are ``False`` and no model is in the download catalogue; :func:`punctuation_ready`
and :func:`speakers_ready` stay ``False`` until both a measurement says yes and
a pinned model is added. Everything below that point -- building the sherpa-onnx
objects, running them, and matching speakers to a transcript's paragraphs -- is
here and tested with fakes, so adopting a model is a catalogue entry and a flag.

**Measured 2026-10-17 (dictation design record section 35).** Punctuation:
not adopted. The CT-Transformer writes Chinese full-width marks into English
text, and neither it nor the English cased model came near the engines' own
marks. Speaker labels: pyannote 3.0 with NeMo TitaNet small at threshold 0.8
labelled 92 and 89 percent of turns right (two and three voices) at about a
fifth of one thread and under 400 MB, enough to offer on request once the
models are pinned in the catalogue and wired in; still off until then.

wx-free. sherpa-onnx is passed in, never imported here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "PUNCTUATION_ADOPTED",
    "SPEAKERS_ADOPTED",
    "SPEAKERS_UNAVAILABLE",
    "Turn",
    "build_diarizer",
    "build_punctuator",
    "label_spans",
    "punctuate",
    "punctuation_ready",
    "speaker_turns",
    "speakers_ready",
]

#: Switched on only after B-1 shows the English punctuation model helps.
PUNCTUATION_ADOPTED = False
#: Switched on only after the speaker models are pinned and their memory is
#: measured on the 8 GB machine (B-8).
SPEAKERS_ADOPTED = False

#: Folders under the shared model store a pinned model will use.
PUNCTUATION_FOLDER = "punctuation-ct-transformer"
SEGMENTATION_FOLDER = "speaker-segmentation"
EMBEDDING_FOLDER = "speaker-embedding"

#: Said (as a transcription warning) when somebody asks for speaker labels.
SPEAKERS_UNAVAILABLE = (
    "Speaker labels are not available with this engine yet, so the transcript has none."
)

_THREADS = 2


def _store_file(folder: str, name: str) -> Path | None:
    from quill.core.windows_dictation.model_store import downloads_root

    path = downloads_root() / folder / name
    return path if path.is_file() else None


# -- punctuation --------------------------------------------------------------- #


def punctuation_ready(find: Callable[[str, str], Path | None] = _store_file) -> bool:
    """Adopted, and its model on this computer."""
    return PUNCTUATION_ADOPTED and find(PUNCTUATION_FOLDER, "model.onnx") is not None


def build_punctuator(sherpa_onnx: Any, model: Path, *, threads: int = _THREADS) -> Any:
    """sherpa-onnx's offline punctuation for the CT-Transformer at *model*."""
    config = sherpa_onnx.OfflinePunctuationConfig(
        model=sherpa_onnx.OfflinePunctuationModelConfig(
            ct_transformer=str(model), num_threads=threads, provider="cpu"
        )
    )
    return sherpa_onnx.OfflinePunctuation(config)


def punctuate(punctuator: Any, text: str) -> str:
    """*text* with marks added; *text* unchanged when the pass fails or is empty,
    because a pass that could not run must never lose words."""
    if not text.strip():
        return text
    try:
        marked = str(punctuator.add_punctuation(text))
    except Exception:  # noqa: BLE001 - the unpunctuated words are still right
        return text
    return marked if marked.strip() else text


# -- speaker labels ------------------------------------------------------------ #


@dataclass(frozen=True, slots=True)
class Turn:
    """One stretch of one voice, in seconds."""

    start: float
    end: float
    speaker: int


def speakers_ready(find: Callable[[str, str], Path | None] = _store_file) -> bool:
    """Adopted, and both speaker models on this computer."""
    return (
        SPEAKERS_ADOPTED
        and find(SEGMENTATION_FOLDER, "model.onnx") is not None
        and find(EMBEDDING_FOLDER, "model.onnx") is not None
    )


def build_diarizer(
    sherpa_onnx: Any,
    segmentation: Path,
    embedding: Path,
    *,
    speakers: int = -1,
    threshold: float = 0.8,
    threads: int = _THREADS,
) -> Any:
    """sherpa-onnx's offline speaker diarization. *speakers* is ``-1`` to let
    the clustering decide, or the number the person knows took part.
    *threshold* 0.8 is the measured best with pyannote segmentation 3.0 and
    NeMo TitaNet small (design record section 35: 91.7 and 88.6 percent of
    turns right for two and three voices; 0.5 over-split every conversation)."""
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(segmentation)
            ),
            num_threads=threads,
            provider="cpu",
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(embedding), num_threads=threads, provider="cpu"
        ),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=speakers, threshold=threshold),
    )
    return sherpa_onnx.OfflineSpeakerDiarization(config)


def speaker_turns(diarizer: Any, samples: Any) -> list[Turn]:
    """Who spoke when, in 16 kHz *samples*, in order."""
    result = diarizer.process(samples)
    ordered = result.sort_by_start_time() if hasattr(result, "sort_by_start_time") else result
    return [Turn(float(s.start), float(s.end), int(s.speaker)) for s in ordered]


def label_spans(spans: Sequence[tuple[float, float]], turns: Sequence[Turn]) -> list[str]:
    """``"Speaker 1"`` and so on for each ``(start, end)`` span: the voice that
    covers most of it, numbered in the order the voices are first heard. ``""``
    for a span no voice covers."""
    numbers: dict[int, int] = {}
    for turn in sorted(turns, key=lambda turn: turn.start):
        numbers.setdefault(turn.speaker, len(numbers) + 1)
    labels: list[str] = []
    for start, end in spans:
        overlap: dict[int, float] = {}
        for turn in turns:
            shared = min(end, turn.end) - max(start, turn.start)
            if shared > 0:
                overlap[turn.speaker] = overlap.get(turn.speaker, 0.0) + shared
        if not overlap:
            labels.append("")
            continue
        speaker = max(overlap, key=lambda key: (overlap[key], -numbers[key]))
        labels.append(f"Speaker {numbers[speaker]}")
    return labels
