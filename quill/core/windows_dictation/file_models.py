"""Which speech models can transcribe a recording here, which one to suggest,
and how long it should take.

Transcribe a Recording offers **every engine the person has**, and only those:

* the two built into every copy -- Moonshine tiny (English) and Whisper tiny
  (English, and multilingual for Spanish);
* every optional model they downloaded in Dictation Settings, Speech Models
  (:func:`~quill.core.windows_dictation.model_store.installed_models`);
* OpenAI's transcription models, where an OpenAI key is saved in Use My Own AI
  Key and Safe Mode is off -- the list read live from OpenAI, exactly as More
  Dictation Settings reads it, less the live-only models (``gpt-live-transcribe``
  takes a microphone, not a file).

Windows speech recognition and Windows voice typing are not offered: both
listen to a microphone and cannot be handed a file.

**The suggestion is the most accurate local model they have** (:data:`FILE_RANK`).
A file is not live dictation: nobody is waiting at the end of each phrase, so
a model too slow to keep up with a talker is fine here as long as the wait is
said up front. The order follows the published accuracy each model's
catalogue entry cites, with a preference for models that hear a whole phrase
at once (Parakeet TDT and Whisper) over streaming ones: Parakeet TDT 0.6B v3
first (best published accuracy of the set and about four times faster than
Whisper large), then Parakeet Unified, Nemotron, and the Whisper family large
to small, the built-in two last. OpenAI is never suggested: it costs money and
sends the recording away, so it is only ever chosen.

**The estimate** (:func:`estimate_seconds`) is the measured speed of each model
(seconds of computing per second of speech on one processor thread, 2026-10-05
dictbench, :attr:`~quill.core.windows_dictation.model_types.DownloadableModel.cost_factor`)
on this computer's class -- the two-second check's hardware answer, without
running a model -- spread over the two threads transcription uses.

Pure and wx-free, apart from asking the model store what is downloaded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from quill.core.windows_dictation.model_catalog import downloadable

__all__ = [
    "FILE_CONSENT_TEXT",
    "FILE_RANK",
    "FileModel",
    "OPENAI_PREFIX",
    "default_model",
    "describe",
    "estimate_seconds",
    "estimate_sentence",
    "file_models",
    "openai_file_models",
    "spoken_length",
]

OPENAI_PREFIX = "openai:"

#: Most accurate first. Ids not listed (a model added to the catalogue later)
#: rank after these and before the built-in two.
FILE_RANK: tuple[str, ...] = (
    "parakeet",
    "parakeet_unified",
    "nemotron",
    "whisper_large_v3",
    "whisper_turbo",
    "distil_large_v3",
    "whisper_medium_en",
    "whisper_medium",
    "distil_medium_en",
    "whisper_small_en",
    "whisper_small",
    "distil_small_en",
    "moonshine_base",
    "whisper_base_en",
    "whisper_base",
    "whisper",
    "moonshine",
)

#: The built-in engines' cost, as a multiple of Moonshine tiny's: Whisper
#: tiny.en measured 0.20 against Moonshine tiny's 0.05 (2026-10-05).
_BUILT_IN_COST = {"moonshine": 1.0, "whisper": 4.0}
#: Moonshine tiny's seconds per second of speech on one thread, on a modest and
#: a capable computer (speed_check's own fallback figures).
_WEAK_TINY, _CAPABLE_TINY = 0.12, 0.05
#: Two threads are not twice one: measured about 1.6 times on the dictbench
#: machine for the transducer and Whisper models.
_TWO_THREADS = 1.6
#: Reading the file and finding the pauses, on top of recognising: seconds of
#: computing per second of recording (measured 2026-10-05 on a three-minute MP3,
#: where Moonshine tiny took 0.06 in all).
_READING = 0.02

#: What the person agrees to before a recording leaves the computer.
FILE_CONSENT_TEXT = (
    "Transcribing with OpenAI sends this recording to OpenAI.\n\n"
    "The speech in the file is sent, a minute or so at a time, over an encrypted "
    "connection to OpenAI with the OpenAI key saved in Use My Own AI Key, and the "
    "words come back. OpenAI bills your account by the minute of audio. Nothing "
    "goes through QUILL's servers, and QUILL keeps no copy.\n\n"
    "OpenAI's own policies apply to what it receives: by default OpenAI does not "
    "train on data sent through its API, and may keep it for up to 30 days to "
    "watch for abuse. Read OpenAI's terms at openai.com/policies before you agree.\n\n"
    "Only send recordings you have the right to share, and the agreement of the "
    "people who speak in them. The models on this computer never send anything "
    "anywhere.\n\n"
    "Send this recording to OpenAI?"
)


@dataclass(frozen=True, slots=True)
class FileModel:
    """One row of the Speech model list."""

    #: An engine id (``moonshine``, ``parakeet``...), or ``openai:<model>``.
    id: str
    label: str
    #: What the details box says about it.
    description: str
    languages: tuple[str, ...]
    #: Cost relative to Moonshine tiny; ``None`` for OpenAI, whose speed is the network's.
    cost_factor: float | None

    @property
    def cloud(self) -> bool:
        return self.id.startswith(OPENAI_PREFIX)

    @property
    def openai_model(self) -> str:
        return self.id[len(OPENAI_PREFIX) :] if self.cloud else ""

    @property
    def name(self) -> str:
        """The label without its parenthesis, for sentences."""
        return self.label.split(" (", 1)[0]

    @property
    def rank(self) -> int:
        if self.cloud:
            return len(FILE_RANK) + 10
        if self.id in FILE_RANK:
            return FILE_RANK.index(self.id)
        return FILE_RANK.index("whisper") - 1


_BUILT_IN = (
    FileModel(
        "moonshine",
        "Moonshine tiny (built in, fastest)",
        "Built into every copy. The fastest model, good on clear speech from one "
        "person close to the microphone: a voice note, a dictated letter. English only.",
        ("en",),
        _BUILT_IN_COST["moonshine"],
    ),
    FileModel(
        "whisper",
        "Whisper tiny (built in)",
        "Built into every copy. A little slower than Moonshine and a little more "
        "forgiving of accents; for Spanish it is the multilingual Whisper tiny.",
        ("en", "es"),
        _BUILT_IN_COST["whisper"],
    ),
)


def openai_file_models(available: Sequence[str]) -> list[str]:
    """OpenAI's models that take a file: the dictation list less the live-only ones."""
    from quill.core.windows_dictation.openai_models import is_live_model

    return [model for model in available if not is_live_model(model)]


def file_models(language: str = "en", openai_models: Sequence[str] = ()) -> list[FileModel]:
    """Every model that can transcribe *language* here, most accurate first.

    *openai_models* is OpenAI's live list for the person's key (empty until it
    has been read, or where there is no key); they are added only where
    :func:`~quill.core.windows_dictation.openai_models.cloud_problem` has no
    objection.
    """
    from quill.core.windows_dictation.model_store import installed_models
    from quill.core.windows_dictation.openai_models import cloud_problem

    rows = [model for model in _BUILT_IN if language in model.languages]
    for model in installed_models():
        if language in model.languages:
            rows.append(
                FileModel(
                    model.id,
                    f"{model.name} (downloaded)",
                    f"{model.good_for} {model.works_best_on}",
                    model.languages,
                    model.cost_factor,
                )
            )
    rows.sort(key=lambda row: row.rank)
    if openai_models and not cloud_problem():
        for name in openai_file_models(openai_models):
            rows.append(
                FileModel(
                    OPENAI_PREFIX + name,
                    f"OpenAI {name} (your own key; sends the recording to OpenAI)",
                    "Very accurate, especially with several voices, accents and noise, "
                    "and it needs an internet connection. The recording is sent to "
                    "OpenAI and billed to your OpenAI account; you are asked first.",
                    ("en", "es"),
                    None,
                )
            )
    return rows


def default_model(models: Sequence[FileModel]) -> FileModel | None:
    """The most accurate model on this computer: never OpenAI."""
    local = [model for model in models if not model.cloud]
    return min(local, key=lambda model: model.rank) if local else None


def _tiny(weak: bool) -> float:
    return _WEAK_TINY if weak else _CAPABLE_TINY


def estimate_seconds(model: FileModel, audio_seconds: float, *, weak: bool) -> float | None:
    """Seconds *model* should take for *audio_seconds* of recording here, or ``None``."""
    if model.cost_factor is None or audio_seconds <= 0:
        return None
    per_second = _tiny(weak) * model.cost_factor / _TWO_THREADS + _READING
    return audio_seconds * per_second


def spoken_length(seconds: float) -> str:
    """``"12 minutes"``, ``"1 hour 5 minutes"``, ``"40 seconds"`` -- for sentences."""
    seconds = max(0.0, seconds)
    if seconds < 60:
        whole = max(1, round(seconds))
        return f"{whole} second{'s' if whole != 1 else ''}"
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or not hours:
        parts.append(f"{minutes:,} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)


def estimate_sentence(model: FileModel, audio_seconds: float, *, weak: bool) -> str:
    """What the dialog says about the wait, in one or two sentences."""
    if audio_seconds <= 0:
        return "The recording's length could not be read, so there is no estimate."
    length = f"The recording is {spoken_length(audio_seconds)} long."
    if model.cloud:
        return (
            f"{length} OpenAI's speed depends on your internet connection; it is "
            "usually much quicker than the recording itself."
        )
    seconds = estimate_seconds(model, audio_seconds, weak=weak) or 0.0
    wait = "under a minute" if seconds < 60 else f"about {spoken_length(seconds)}"
    return (
        f"{length} With {model.name}, transcribing it should take {wait} on this "
        "computer. You can keep working while it runs."
    )


def describe(engine_id: str) -> str:
    """The display name of a local engine id, for sentences after the fact."""
    for model in _BUILT_IN:
        if model.id == engine_id:
            return model.name
    found = downloadable(engine_id)
    return found.name if found is not None else engine_id
