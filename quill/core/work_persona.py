"""Work Personas (#896): a named bundle that ties together a feature profile,
a default working folder, favorite files, and (optionally) a keymap profile,
so a whole context -- school, work, a hobby project -- is one launch away.

Copy Tray, sessions, and feature profiles all already do their part; a
persona is just the small, named object that says which combination of them
belongs together. Applying one is a thin orchestration step (see
``quill.ui.main_frame_work_persona``), not new machinery of its own.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.storage import write_json_atomic

__all__ = ["WorkPersona", "WorkPersonaStore"]


@dataclass(slots=True)
class WorkPersona:
    name: str
    technical_profile: str = "essential"
    working_folder: str = ""
    favorite_files: tuple[str, ...] = field(default_factory=tuple)
    keymap_profile: str = ""

    def display_label(self) -> str:
        folder = f" — {self.working_folder}" if self.working_folder else ""
        return f"{self.name}{folder}"


class WorkPersonaStore:
    """Persistent, named collection of :class:`WorkPersona` bundles."""

    _FILENAME = "work_personas.json"
    _VERSION = 1

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / self._FILENAME
        self._personas: dict[str, WorkPersona] = {}
        self._load()

    def create(self, persona: WorkPersona) -> bool:
        """Add *persona*. Returns False (a no-op) if the name is already taken."""
        if persona.name in self._personas:
            return False
        self._personas[persona.name] = persona
        self._save()
        return True

    def update(self, persona: WorkPersona) -> None:
        """Replace the stored persona sharing *persona*'s name."""
        self._personas[persona.name] = persona
        self._save()

    def remove(self, name: str) -> None:
        self._personas.pop(name, None)
        self._save()

    def get(self, name: str) -> WorkPersona | None:
        return self._personas.get(name)

    def all(self) -> list[WorkPersona]:
        return sorted(self._personas.values(), key=lambda p: p.name.lower())

    def __len__(self) -> int:
        return len(self._personas)

    def _save(self) -> None:
        write_json_atomic(
            self._path,
            {
                "version": self._VERSION,
                "personas": [asdict(p) for p in self._personas.values()],
            },
        )

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw: dict = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw.get("personas", []):
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                self._personas[name] = WorkPersona(
                    name=name,
                    technical_profile=str(item.get("technical_profile", "essential")),
                    working_folder=str(item.get("working_folder", "")),
                    favorite_files=tuple(str(f) for f in item.get("favorite_files", [])),
                    keymap_profile=str(item.get("keymap_profile", "")),
                )
        except Exception:  # noqa: BLE001 - corrupt data -- start fresh
            pass
