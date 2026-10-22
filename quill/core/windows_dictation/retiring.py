"""Speech models being retired, and the one-time notice that says so.

**The policy** (dictation design, section 32.6, "Deprecation policy"): evidence
first; a full feature release of notice; announced three ways (the changelog
and release notes, one spoken sentence the first time a retiring model starts,
and a line in the model list); never silently, so QUILL never switches anybody's
model and never deletes a file.

**The evidence** (dictation design, section 36; 2026-10-22 machine run on real
recordings): each model here was beaten on every measure that matters for
dictation by a model already in the catalogue -- fewer words wrong on the
LibriVox held-out set (recordings no model was trained on), faster on one
processor thread, and no more memory -- so keeping it offered only a slower or
heavier way to get a worse result. Whisper base.en and every multilingual
Whisper size stay: base.en is the lightest good English model after the built-in
ones, and the multilingual sizes are the only local models for many languages.

**What it does.** :func:`row_note` is the line the model list shows;
:func:`take_notice` is the sentence dictation says once, the first time a
retiring model starts, and records that it was said in ``retiring-notices.json``
beside the family's shared dictation settings (``family_store``), so it is said
once across every QuillVille program, not once per program. The recommendation
never names a retiring model (``model_advice``).

wx-free.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

__all__ = ["RETIRING", "Retiring", "is_retiring", "notice", "reason", "row_note", "take_notice"]

logger = logging.getLogger(__name__)

_NOTICES_FILE = "retiring-notices.json"


@dataclass(frozen=True, slots=True)
class Retiring:
    """One model being retired, what replaces it, and the measured reason."""

    model_id: str
    #: The catalogue id of the model to use instead.
    replacement: str
    #: The measurements, in words, naming both models (shown in the details).
    evidence: str


#: Retiring since 2026-10-22; removed no earlier than the next feature release.
#: Each was beaten by Parakeet Unified on the held-out audiobooks (3.2 percent
#: wrong), on FLEURS where both ran, and on noisy LibriSpeech, while running
#: faster per thread in the same or a smaller memory tier (design section 36).
RETIRING: dict[str, Retiring] = {
    entry.model_id: entry
    for entry in (
        Retiring(
            "distil_small_en",
            "parakeet_unified",
            "Parakeet Unified got 3.2 percent of words wrong and Distil-Whisper "
            "small.en 5.9; on noisy speech, 3.2 and 9.2. Parakeet Unified was also "
            "faster.",
        ),
        Retiring(
            "whisper_small_en",
            "parakeet_unified",
            "Parakeet Unified got 3.2 percent of words wrong and Whisper small.en 4.3. "
            "Parakeet Unified was also more than twice as fast, in less memory.",
        ),
        Retiring(
            "distil_medium_en",
            "parakeet_unified",
            "Parakeet Unified got 3.2 percent of words wrong and Distil-Whisper "
            "medium.en 6.3. Parakeet Unified was also about three times as fast, in "
            "less memory.",
        ),
        Retiring(
            "whisper_medium_en",
            "parakeet_unified",
            "Parakeet Unified got 3.2 percent of words wrong and Whisper medium.en "
            "3.6. Parakeet Unified was also about ten times as fast, in less than half "
            "the memory.",
        ),
        Retiring(
            "distil_large_v3",
            "parakeet_unified",
            "Parakeet Unified got 3.2 percent of words wrong and Distil-Whisper "
            "large-v3 4.5. Parakeet Unified was also about five times as fast, in less "
            "memory.",
        ),
    )
}


def is_retiring(model_id: str) -> bool:
    return model_id in RETIRING


def _name(model_id: str) -> str:
    from quill.core.windows_dictation.model_catalog import downloadable

    model = downloadable(model_id)
    return model.name if model is not None else model_id


def row_note(model_id: str) -> str:
    """``"Being retired, use NVIDIA Parakeet ... instead."``, or ``""``."""
    entry = RETIRING.get(model_id)
    if entry is None:
        return ""
    return f"Being retired, use {_name(entry.replacement)} instead."


def reason(model_id: str) -> str:
    """The measured reason, for the model's details: ``""`` when it stays."""
    entry = RETIRING.get(model_id)
    if entry is None:
        return ""
    return f"Being retired. In our tests with real recordings, {entry.evidence}"


def notice(model_id: str) -> str:
    """The one sentence said once, as dictation starts, or ``""``.

    Short on purpose (accessibility review, 2026-10-22): it is spoken as the
    microphone opens, so it front-loads the fact, says nothing changes, and
    leaves the measured reason to the model's details in the list, where it can
    be read at leisure. "The model list" fits QUILL, QUILL Lite and QUILL
    Transcribe alike, whose windows are named differently.
    """
    if model_id not in RETIRING:
        return ""
    return (
        f"Retiring: {_name(model_id)}. It keeps working, and nothing changes until "
        "you choose another model; the model list says why."
    )


def _notices_path(folder: Path | None) -> Path:
    if folder is not None:
        return folder / _NOTICES_FILE
    from quill.core.windows_dictation.family_store import family_dictation_dir

    return family_dictation_dir() / _NOTICES_FILE


def _said(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    said = data.get("said") if isinstance(data, dict) else None
    return {str(item) for item in said} if isinstance(said, list) else set()


def take_notice(model_id: str, *, folder: Path | None = None) -> str:
    """The retirement notice for *model_id* the first time only, else ``""``.

    The record is written before the notice is returned; if it cannot be
    written, the notice is still returned (said again next time is better than
    never said at all) and the failure is logged.
    """
    text = notice(model_id)
    if not text:
        return ""
    path = _notices_path(folder)
    said = _said(path)
    if model_id in said:
        return ""
    try:
        from quill.core.storage import write_json_atomic

        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, {"said": sorted(said | {model_id})})
    except OSError as error:
        logger.warning("Could not record the retirement notice for %s: %s", model_id, error)
    return text
