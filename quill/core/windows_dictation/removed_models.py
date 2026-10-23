"""Speech models removed from the catalogue, and the one sentence that says so.

**The decision** (dictation design, section 37, 2026-10-22): the five
English-only models below were removed in the same release that found them
beaten, rather than after a release of notice as section 32.6 first planned.
Each was beaten on every measure that matters for dictation by Parakeet
Unified, already in the catalogue -- fewer words wrong on the LibriVox
held-out set (recordings no model was trained on), faster on one processor
thread, and in the same or a smaller memory tier (section 36) -- so a release of notice would only
have kept offering a slower or heavier way to a worse result. Whisper base.en
and every multilingual Whisper size stay.

**Somebody who was using one.** The saved choice is no longer a catalogue id,
so :func:`~quill.core.windows_dictation.engines.coerce_engine` asks
:func:`replacement_for` what to use instead: Parakeet Unified when it is
already downloaded, otherwise the built-in model. Nothing is downloaded and no
file is deleted -- the old model's folder stays under the dictation models
folder until the person removes it. Never silently: :func:`noticed` records the
change in ``removed-model-notices.json`` beside the family's shared dictation
settings (``family_store``) the moment it is made, and :func:`take_notice` is the
sentence dictation says the next time it starts, once across every QuillVille
program. The record is written when the change is made, not when it is said,
because the next settings save forgets the old id.

wx-free.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

__all__ = ["REMOVED", "Removed", "is_removed", "noticed", "replacement_for", "take_notice"]

logger = logging.getLogger(__name__)

_NOTICES_FILE = "removed-model-notices.json"
_REPLACEMENT = "parakeet_unified"


@dataclass(frozen=True, slots=True)
class Removed:
    """One model taken out of the catalogue, and the folder it left behind."""

    model_id: str
    name: str
    #: Its folder under the dictation models folder (``model_store``).
    folder: str


#: Removed 2026-10-22. Parakeet Unified got 3.2 percent of words wrong on the
#: held-out audiobooks, against 3.6 to 6.3 for these, and ran faster.
REMOVED: dict[str, Removed] = {
    entry.model_id: entry
    for entry in (
        Removed("distil_small_en", "Distil-Whisper small.en", "whisper-distil-small.en-int8"),
        Removed("whisper_small_en", "Whisper small.en", "whisper-small.en-int8"),
        Removed("distil_medium_en", "Distil-Whisper medium.en", "whisper-distil-medium.en-int8"),
        Removed("whisper_medium_en", "Whisper medium.en", "whisper-medium.en-int8"),
        Removed("distil_large_v3", "Distil-Whisper large-v3", "whisper-distil-large-v3-int8"),
    )
}


def is_removed(model_id: str) -> bool:
    return model_id in REMOVED


def replacement_for(model_id: str) -> str | None:
    """What a saved *model_id* becomes: ``None`` when it was not removed,
    Parakeet Unified when that is already downloaded, else ``""`` (the
    default engine). Never downloads anything."""
    if model_id not in REMOVED:
        return None
    from quill.core.windows_dictation.model_catalog import downloadable
    from quill.core.windows_dictation.model_store import installed

    model = downloadable(_REPLACEMENT)
    try:
        return _REPLACEMENT if model is not None and installed(model) else ""
    except OSError:
        return ""


def _notices_path(folder: Path | None) -> Path:
    if folder is not None:
        return folder / _NOTICES_FILE
    from quill.core.windows_dictation.family_store import family_dictation_dir

    return family_dictation_dir() / _NOTICES_FILE


def _read(path: Path) -> dict[str, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pending": [], "said": []}
    if not isinstance(data, dict):
        data = {}
    return {
        key: [str(item) for item in value] if isinstance(value := data.get(key), list) else []
        for key in ("pending", "said")
    }


def _write(path: Path, record: dict[str, list[str]]) -> None:
    from quill.core.storage import write_json_atomic

    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, record)


def noticed(model_id: str, replacement: str, *, folder: Path | None = None) -> None:
    """Record that a saved *model_id* was changed to *replacement* (``""`` is
    the built-in model), to be said at the next dictation start. Once only."""
    path = _notices_path(folder)
    record = _read(path)
    entries = {item.partition("=")[0] for item in record["pending"]} | set(record["said"])
    if model_id in entries:
        return
    record["pending"].append(f"{model_id}={replacement}")
    try:
        _write(path, record)
    except OSError as error:
        logger.warning("Could not record that %s was removed: %s", model_id, error)


def _sentence(model_id: str, replacement: str) -> str:
    name = REMOVED[model_id].name
    if replacement:
        return (
            f"{name} was removed in this release. Dictation now uses Parakeet Unified, "
            "which you already have."
        )
    return (
        f"{name} was removed in this release, so dictation uses the built-in model. "
        "Parakeet Unified, in the model list, is more accurate."
    )


def take_notice(*, folder: Path | None = None) -> str:
    """The sentence for every change :func:`noticed` recorded and nobody has
    heard yet, else ``""``. Marked said before it is returned; if that cannot
    be written it is still returned (said again is better than never said)."""
    path = _notices_path(folder)
    record = _read(path)
    if not record["pending"]:
        return ""
    sentences = []
    for item in record["pending"]:
        model_id, _, replacement = item.partition("=")
        if model_id in REMOVED and model_id not in record["said"]:
            sentences.append(_sentence(model_id, replacement))
            record["said"].append(model_id)
    record["pending"] = []
    try:
        _write(path, record)
    except OSError as error:
        logger.warning("Could not record the removed-model notice: %s", error)
    return " ".join(sentences)
