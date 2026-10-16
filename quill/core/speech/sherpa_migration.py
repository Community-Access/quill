"""Bringing QUILL's older sherpa-onnx engines onto the shared layer (dict.md D-26).

Until 2026-10-16 QUILL's Locked Dictation and offline transcription had two
sherpa-onnx engines of their own, ``nemotron`` and ``parakeet``, each with its
own model folder under ``<app data>/speech-models/<engine>/<model>``. Live
dictation, QUILL Lite and QUILL Transcribe ran the same models from the family
store (:mod:`quill.core.windows_dictation.model_store`), so a person who used
both could download Parakeet twice. The two engines are gone; one provider
(:mod:`quill.core.speech.providers.sherpa_shared`, id ``sherpa``) runs every
model in the one store. This module moves what people already have:

* :func:`migrate_choice` is what ``Settings.from_dict`` calls: a saved engine of
  ``nemotron`` or ``parakeet`` becomes ``sherpa``, and the old model ids become
  the catalogue's (``parakeet-tdt-0.6b-v3`` is ``parakeet``). Before this, a
  saved ``parakeet`` was not even accepted (the ladder chose it), so only
  ``nemotron`` was ever kept.
* :func:`adopt_legacy_models` gives the store a Parakeet that was downloaded
  the old way, **never downloading twice**: each file is hard-linked (moved
  when the two folders are on different drives) into the store's folder, and
  only when every file is there at the catalogue's pinned size -- a model is
  adopted whole or not at all. The bytes were checked against their SHA-256
  when they arrived, which is the store's own rule for what counts as
  installed (``model_store``: hashing 650 MB on every start costs more than it
  protects). The older Nemotron is a different model from the catalogue's
  Nemotron 3.5 (80 mel features, not 128), so it is not adopted; a person who
  chose it gets the most accurate model they have until they download
  Nemotron 3.5 in Dictation Settings, Speech Models.

wx-free.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

__all__ = [
    "ACCEPTED_PROVIDERS",
    "LEGACY_MODEL_IDS",
    "LEGACY_PROVIDER_IDS",
    "SHARED_PROVIDER_ID",
    "adopt_legacy_models",
    "migrate_choice",
]

SHARED_PROVIDER_ID = "sherpa"
LEGACY_PROVIDER_IDS = frozenset({"nemotron", "parakeet"})
#: The engines ``speech_provider`` may name; ``""`` is the preference ladder.
ACCEPTED_PROVIDERS = frozenset({"", "whispercpp", "fasterwhisper", SHARED_PROVIDER_ID})
#: Old model id -> catalogue id.
LEGACY_MODEL_IDS: dict[str, str] = {
    "nemotron-streaming-en-0.6b": "nemotron",
    "parakeet-tdt-0.6b-v3": "parakeet",
}
#: Old ``(engine folder, model folder)`` -> catalogue id, for models whose files
#: are the catalogue's own (the same upstream sherpa-onnx export).
_ADOPTABLE: dict[tuple[str, str], str] = {("parakeet", "parakeet-tdt-0.6b-v3"): "parakeet"}


def migrate_choice(data: Mapping[str, object]) -> tuple[str, str]:
    """``(speech_provider, speech_default_model_id)`` for saved *data*."""
    provider = str(data.get("speech_provider", "") or "").strip().lower()
    model = str(data.get("speech_default_model_id", "") or "").strip()
    if provider in LEGACY_PROVIDER_IDS:
        provider = SHARED_PROVIDER_ID
    if provider not in ACCEPTED_PROVIDERS:
        provider = ""
    return provider, LEGACY_MODEL_IDS.get(model, model)


def _find(root: Path, name: str, size: int) -> Path | None:
    """*name* at exactly *size* in *root* or one folder below (an extracted
    bundle sometimes keeps its archive's top folder)."""
    folders = [path for path in sorted(root.iterdir()) if path.is_dir()]
    for candidate in (root / name, *(folder / name for folder in folders)):
        try:
            if candidate.is_file() and candidate.stat().st_size == size:
                return candidate
        except OSError:
            continue
    return None


def _place(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except OSError:
        shutil.move(str(source), str(target))  # another drive: move, never copy twice


def adopt_legacy_models(legacy_root: Path | None = None) -> list[str]:
    """Hard-link (or move) old-style downloads into the shared store; return
    the catalogue ids adopted. Never raises: a model that cannot be adopted is
    simply not, and can still be downloaded."""
    from quill.core.windows_dictation.model_catalog import downloadable
    from quill.core.windows_dictation.model_store import installed, model_folder

    if legacy_root is None:
        from quill.core.speech.models import models_root

        legacy_root = models_root()
    adopted: list[str] = []
    for (engine, folder), model_id in _ADOPTABLE.items():
        model = downloadable(model_id)
        old = legacy_root / engine / folder
        if model is None or not old.is_dir() or installed(model):
            continue
        found = {item.name: _find(old, item.name, item.size) for item in model.files}
        if any(path is None for path in found.values()):
            continue
        target = model_folder(model)
        try:
            target.mkdir(parents=True, exist_ok=True)
            for item in model.files:
                final = target / item.name
                source = found[item.name]
                if source is not None and not final.exists():
                    _place(source, final)
        except OSError:
            continue
        if installed(model):
            adopted.append(model_id)
            _forget_legacy_record(folder, engine)
    return adopted


def _forget_legacy_record(model_id: str, engine: str) -> None:
    try:
        from quill.core.speech.models import remove_installed_model

        remove_installed_model(model_id, engine)
    except Exception:  # noqa: BLE001 - a stale record is harmless
        pass
