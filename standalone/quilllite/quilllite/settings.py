"""Settings: one small JSON file, written atomically."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from quilllite.paths import settings_path

MAX_RECENT = 10


@dataclass
class Settings:
    theme: str = "dark"  # "dark" or "system"; dark by default for light sensitivity
    font_name: str = ""  # empty = system default
    font_size: int = 12
    word_wrap: bool = True
    default_mode: str = "plain"  # what Ctrl+N creates: "plain" or "rich"
    window_width: int = 900
    window_height: int = 650
    window_maximized: bool = False
    recent_files: list[str] = field(default_factory=list)
    autosave_seconds: int = 60

    def remember_recent(self, path: str) -> None:
        path = str(path)
        self.recent_files = [p for p in self.recent_files if p != path]
        self.recent_files.insert(0, path)
        del self.recent_files[MAX_RECENT:]


def load(path: Path | None = None) -> Settings:
    path = path or settings_path()
    settings = Settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if not isinstance(raw, dict):
        return settings
    known = {f.name: f for f in fields(Settings)}
    for key, value in raw.items():
        if key in known and isinstance(value, type(getattr(settings, key))):
            setattr(settings, key, value)
    if settings.theme not in {"dark", "system"}:
        settings.theme = "dark"
    if settings.default_mode not in {"plain", "rich"}:
        settings.default_mode = "plain"
    settings.font_size = max(6, min(72, int(settings.font_size)))
    return settings


def save(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    write_json_atomic(path, asdict(settings))


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)
