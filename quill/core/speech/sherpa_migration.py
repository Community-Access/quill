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
* **Deprecated, and said once (2026-10-17).** The duplicate path is deprecated
  in QUILL 1.1 and this adoption code goes in QUILL 1.2 (design record sections
  32.6 and 41). :func:`migration_notice` marks a moved engine choice as owed a
  sentence, and :func:`legacy_leftovers` finds old folders nothing uses (the
  older Nemotron above), which :mod:`quill.ui.sherpa_migration_notice` offers
  once to delete, No by default; :func:`remove_leftovers` reports the bytes it
  actually freed. Nothing is ever deleted without that Yes.

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
    "legacy_leftovers",
    "migrate_choice",
    "migration_notice",
    "remove_leftovers",
]

#: The deprecation (design record sections 32.6 and 41): the duplicate path is
#: deprecated in QUILL 1.1 and its adoption code goes in QUILL 1.2. A saved
#: ``nemotron`` or ``parakeet`` keeps loading as ``sherpa`` after that.
DEPRECATED_IN = "QUILL 1.1"
REMOVED_IN = "QUILL 1.2"
_NOTICE_STATES = frozenset({"", "pending", "done"})

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


def migration_notice(data: Mapping[str, object]) -> str:
    """``sherpa_migration_notice`` for saved *data*: ``"pending"`` when a saved
    engine of ``nemotron`` or ``parakeet`` is being moved to ``sherpa`` now and
    the person has not been told, else what was saved (``""`` or ``"done"``).
    The policy's "never silently" (section 32.6): the move is said once, by
    :mod:`quill.ui.sherpa_migration_notice`."""
    saved = str(data.get("sherpa_migration_notice", "") or "").strip().lower()
    if saved not in _NOTICE_STATES:
        saved = ""
    provider = str(data.get("speech_provider", "") or "").strip().lower()
    if provider in LEGACY_PROVIDER_IDS and saved != "done":
        return "pending"
    return saved


def _is_link(path: Path) -> bool:
    """A symbolic link or an NTFS junction: something that may point outside
    the folder, so it is never walked into or counted, only unlinked."""
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return True


def _walk_files(folder: Path) -> list[Path]:
    """Every file under *folder*, never through a link or junction."""
    files: list[Path] = []
    try:
        entries = list(folder.iterdir())
    except OSError:
        return files
    for entry in entries:
        if _is_link(entry):
            continue
        if entry.is_dir():
            files.extend(_walk_files(entry))
        elif entry.is_file():
            files.append(entry)
    return files


def _bytes_only_here(folder: Path) -> int:
    """Bytes under *folder* that deleting it would free: files with no other
    hard link (an adopted Parakeet's files are links into the store, so
    deleting the old folder frees nothing and is not worth offering). Links
    and junctions are not followed."""
    total = 0
    for path in _walk_files(folder):
        try:
            info = path.stat()
        except OSError:
            continue
        if info.st_nlink <= 1:
            total += info.st_size
    return total


def _remove_tree(folder: Path) -> int:
    """Delete *folder*'s contents, bottom up, and return the bytes freed. A
    link or junction inside is removed as a link; what it points at is never
    touched."""
    freed = 0
    try:
        entries = list(folder.iterdir())
    except OSError:
        return 0
    for entry in entries:
        try:
            if _is_link(entry):
                if entry.is_dir():
                    os.rmdir(entry)  # removes a directory link or junction itself
                else:
                    entry.unlink()
            elif entry.is_dir():
                freed += _remove_tree(entry)
                entry.rmdir()
            else:
                info = entry.stat()
                entry.unlink()
                if info.st_nlink <= 1:
                    freed += info.st_size
        except OSError:
            continue
    return freed


def legacy_leftovers(legacy_root: Path | None = None) -> list[tuple[Path, int]]:
    """Old-style model folders nothing uses any more, with the bytes deleting
    each would free: the older Nemotron (never adopted, section 22) and any old
    Parakeet copy whose files are not links into the shared store. Folders that
    would free nothing are left out. Never raises."""
    try:
        if legacy_root is None:
            from quill.core.speech.models import models_root

            legacy_root = models_root()
        found: list[tuple[Path, int]] = []
        for engine in sorted(LEGACY_PROVIDER_IDS):
            parent = legacy_root / engine
            if not parent.is_dir():
                continue
            for folder in sorted(p for p in parent.iterdir() if p.is_dir()):
                size = _bytes_only_here(folder)
                if size > 0:
                    found.append((folder, size))
        return found
    except OSError:
        return []


def remove_leftovers(folders: list[Path], legacy_root: Path | None = None) -> int:
    """Delete *folders* (only ever ones :func:`legacy_leftovers` named, inside
    the old ``speech-models/nemotron`` or ``parakeet`` folders) and return the
    bytes actually freed, measured file by file as each is removed -- never an
    estimate. Called only after the person answered Yes."""
    if legacy_root is None:
        from quill.core.speech.models import models_root

        legacy_root = models_root()
    allowed = [(legacy_root / engine).resolve() for engine in LEGACY_PROVIDER_IDS]
    freed = 0
    for folder in folders:
        if _is_link(folder):
            continue  # a link named as the folder: never followed
        target = folder.resolve()
        if not any(parent in target.parents for parent in allowed):
            continue  # never outside the old engines' own folders
        freed += _remove_tree(target)
        try:
            target.rmdir()
        except OSError:
            pass
    return freed


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
