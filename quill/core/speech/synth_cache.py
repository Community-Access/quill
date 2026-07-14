"""Incremental rebuild cache for the Audio Studio (item: the authoring loop).

Each successfully synthesized document is remembered in
``<source folder>/.quill/speech-cache.json`` as a fingerprint over the
document's bytes plus every setting that shapes its audio. On the next run,
a document whose fingerprint matches — and whose output file still exists —
is reused instead of re-synthesized, so editing one chapter of a 40-document
book costs minutes, not the whole overnight run.

The fingerprint is deliberately conservative: any settings change (voice,
gaps, sounder, translations, dictionaries, ...) changes the key and forces a
fresh synthesis. Secrets never enter the fingerprint. wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from quill.core.storage import write_json_atomic

#: Same project folder the speech profile and feed config use.
CACHE_DIRNAME = ".quill"
CACHE_FILENAME = "speech-cache.json"


def _cache_path(folder: Path) -> Path:
    return folder / CACHE_DIRNAME / CACHE_FILENAME


def settings_digest(settings: Mapping[str, object]) -> str:
    """A stable digest of the audio-shaping settings (canonical JSON, sorted)."""
    canonical = json.dumps(settings, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fingerprint(source: Path, settings: Mapping[str, object]) -> str:
    """The reuse key for *source* under *settings* (content hash + settings)."""
    digest = hashlib.sha256()
    digest.update(settings_digest(settings).encode("ascii"))
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_cache(folder: Path) -> dict[str, str]:
    """The folder's remembered fingerprints (empty on absence or junk)."""
    try:
        data = json.loads(_cache_path(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return {}
    return {str(k): str(v) for k, v in entries.items() if isinstance(v, str)}


def save_cache(folder: Path, entries: Mapping[str, str]) -> None:
    """Persist *entries* atomically; a failure is never worth failing a run."""
    try:
        path = _cache_path(folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, {"version": 1, "entries": dict(sorted(entries.items()))})
    except OSError:
        pass


def can_reuse(
    entries: Mapping[str, str],
    key: str,
    source: Path,
    output: Path,
    settings: Mapping[str, object],
) -> bool:
    """True when *output* exists and *source* + *settings* match the record."""
    if not output.is_file():
        return False
    recorded = entries.get(key)
    if not recorded:
        return False
    try:
        return recorded == fingerprint(source, settings)
    except OSError:
        return False
