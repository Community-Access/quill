from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Document:
    text: str = ""
    path: Path | None = None
    modified: bool = False
    encoding: str = "utf-8"
    line_ending: str = "\n"
    source_metadata: dict[str, object] = field(default_factory=dict)
    _revision: int = field(default=0, repr=False)

    @property
    def name(self) -> str:
        if self.path is not None:
            return self.path.name
        display_name = str(self.source_metadata.get("display_name", "")).strip()
        if display_name:
            return " ".join(display_name.split())
        return "Untitled"

    @property
    def revision(self) -> int:
        return self._revision

    def set_text(self, value: str) -> None:
        if value == self.text:
            return
        self.text = value
        self.modified = True
        self._revision += 1

    def mark_saved(self, path: Path | None = None) -> None:
        if path is not None:
            self.path = path
        self.modified = False
