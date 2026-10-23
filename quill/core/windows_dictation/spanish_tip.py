"""The one-time suggestion of a better Spanish model, on a computer that can run one.

**Why** (do.md, 2026-10-22 decision; dictation design, section 36): the only
Spanish model in the installers is the built-in Whisper tiny, which got 30.5
percent of words wrong on FLEURS Spanish and 27.0 on the Spanish audiobooks --
about one word in four. Parakeet TDT v3 got 4.4 and 7.3, and on a computer with
8 GB of memory the Spanish recommendation is already that model. Shipping
Whisper base instead (12.6 and 16.1) would have made every installer bigger
and still left Spanish three times worse than a download most computers can
run, so the answer is to say so, once, at the moment it matters.

**When.** The first time dictation starts in Spanish on a computer whose own
recommendation for Spanish (``model_advice.for_this_computer``) is a model to
download, while the speech is going to the built-in Whisper tiny -- which is
what both built-in engines and every English-only download use for Spanish
(``engines.model_for``). Said once across every QuillVille program, recorded in
``spanish-tip.json`` beside the family's shared dictation settings. Nothing is
downloaded and nothing switched: the sentence names the model and where to get
it, and the person decides.

wx-free.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ["take_tip", "tip"]

logger = logging.getLogger(__name__)

_TIP_FILE = "spanish-tip.json"


def _megabytes(download_bytes: int) -> str:
    return f"{round(download_bytes / 1_000_000):,} MB"


def tip(engine_id: str, speech_language: str) -> str:
    """The sentence for dictating *speech_language* with *engine_id* here, or ``""``."""
    from quill.core.windows_dictation.engines import WHISPER_MULTILINGUAL, model_for
    from quill.core.windows_dictation.speech_language import coerce_speech_language

    if coerce_speech_language(speech_language) != "es":
        return ""
    if model_for(engine_id, "es").id != WHISPER_MULTILINGUAL.id:
        return ""  # a Spanish model of its own, or Windows doing the recognising
    from quill.core.windows_dictation.model_advice import for_this_computer
    from quill.core.windows_dictation.model_catalog import downloadable
    from quill.core.windows_dictation.model_types import MEASURED

    try:
        advice = for_this_computer("es")
    except Exception:  # noqa: BLE001 - no advice is no tip, never a failed start
        logger.debug("No Spanish recommendation for the tip", exc_info=True)
        return ""
    model = downloadable(advice.model_id)
    built_in = MEASURED["whisper"].word_errors_es
    better = MEASURED[advice.model_id].word_errors_es if advice.model_id in MEASURED else None
    if advice.built_in or model is None or built_in is None or better is None:
        return ""  # this computer is best left on the built-in model
    from quill.core.windows_dictation.model_store import installed

    where = (
        "It is already downloaded; choose it in the model list."
        if installed(model)
        else f"It is a {_megabytes(model.download_bytes)} download in the model list."
    )
    return (
        f"For Spanish, {model.name} gets about {round(better)} percent of words wrong, "
        f"against {round(built_in)} for the built-in model. {where}"
    )


def _tip_path(folder: Path | None) -> Path:
    if folder is not None:
        return folder / _TIP_FILE
    from quill.core.windows_dictation.family_store import family_dictation_dir

    return family_dictation_dir() / _TIP_FILE


def _said(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and bool(data.get("said"))


def _write(path: Path) -> None:
    from quill.core.storage import write_json_atomic

    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, {"said": True})


def take_tip(engine_id: str, speech_language: str, *, folder: Path | None = None) -> str:
    """:func:`tip` the first time only across the family, else ``""``.

    Marked said before it is returned; if that cannot be written it is still
    returned (said again next time is better than never said)."""
    path = _tip_path(folder)
    if _said(path):
        return ""
    text = tip(engine_id, speech_language)
    if not text:
        return ""
    try:
        _write(path)
    except OSError as error:
        logger.warning("Could not record the Spanish model tip: %s", error)
    return text
