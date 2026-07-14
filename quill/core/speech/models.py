"""Installed speech-model store (#617 section 8.3).

Tracks which speech models are on disk via a small JSON file under the data
directory (``<data>/speech-models/installed.json``), written atomically. Pure and
wx-free; model *download* is a provider concern, this module only records what is
installed so the model manager and providers agree.
"""

from __future__ import annotations

from json import JSONDecodeError
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.speech.provider import InstalledSpeechModel
from quill.core.storage import read_json, write_json_atomic

SCHEMA_VERSION = 1


def models_root() -> Path:
    """Directory where speech models and their metadata live."""
    return app_data_dir() / "speech-models"


def _metadata_path() -> Path:
    return models_root() / "installed.json"


def _to_dict(model: InstalledSpeechModel) -> dict[str, object]:
    return {
        "id": model.id,
        "display_name": model.display_name,
        "path": str(model.path),
        "size_mb": model.size_mb,
        "provider_id": model.provider_id,
        "sha256": model.sha256,
        "installed_at": model.installed_at,
    }


def load_installed_models() -> list[InstalledSpeechModel]:
    """Return the recorded installed models (empty list if none or unreadable)."""
    try:
        data = read_json(_metadata_path(), default={"models": []})
    except JSONDecodeError:
        return []
    raw = data.get("models", []) if isinstance(data, dict) else []
    out: list[InstalledSpeechModel] = []
    for entry in raw:
        if not isinstance(entry, dict) or "id" not in entry or "path" not in entry:
            continue
        out.append(
            InstalledSpeechModel(
                id=str(entry["id"]),
                display_name=str(entry.get("display_name", entry["id"])),
                path=Path(str(entry["path"])),
                size_mb=int(entry.get("size_mb", 0)),
                provider_id=str(entry.get("provider_id", "")),
                sha256=entry.get("sha256"),
                installed_at=str(entry.get("installed_at", "")),
            )
        )
    return out


def save_installed_models(models: list[InstalledSpeechModel]) -> None:
    """Atomically persist the installed-model list."""
    write_json_atomic(
        _metadata_path(),
        {"schema_version": SCHEMA_VERSION, "models": [_to_dict(m) for m in models]},
    )


def record_installed_model(model: InstalledSpeechModel) -> None:
    """Add (or replace) ``model`` in the store, keyed by (provider_id, id)."""
    models = [
        m
        for m in load_installed_models()
        if not (m.id == model.id and m.provider_id == model.provider_id)
    ]
    models.append(model)
    save_installed_models(models)


def remove_installed_model(model_id: str, provider_id: str) -> bool:
    """Drop a model from the store. Returns True if one was removed."""
    models = load_installed_models()
    kept = [m for m in models if not (m.id == model_id and m.provider_id == provider_id)]
    if len(kept) == len(models):
        return False
    save_installed_models(kept)
    return True
