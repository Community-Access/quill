"""Task-aware profile suggestions (verbosity §31).

QUILL can notice the kind of file you opened — Markdown, code, a braille file —
and *suggest* a matching verbosity profile. In 0.7.0 there is no forced
switching: suggestions are off by default, opt-in, reversible, and configurable
per file type. :class:`TaskProfileSuggester` owns the per-extension mapping and
the accept/reject memory.

Pure and wx-free.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["DEFAULT_TASK_MAPPING", "TaskProfileSuggester"]

#: A sensible starting map of file extension to suggested profile.
DEFAULT_TASK_MAPPING: dict[str, str] = {
    ".md": "Normal",
    ".markdown": "Normal",
    ".py": "Expert",
    ".js": "Expert",
    ".ts": "Expert",
    ".brf": "Normal",
    ".brl": "Normal",
}


class TaskProfileSuggester:
    """Suggests a profile for an opened file, only when enabled and not rejected."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        mapping: dict[str, str] | None = None,
    ) -> None:
        self._enabled = enabled
        self._mapping = dict(mapping) if mapping is not None else dict(DEFAULT_TASK_MAPPING)
        self._rejected: set[str] = set()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def suggestion_for(self, path: str | Path) -> str | None:
        """Return the suggested profile name for ``path``, or ``None``.

        Returns ``None`` when suggestions are off, the extension is unmapped, or
        the user previously rejected suggestions for that extension.
        """
        if not self._enabled:
            return None
        ext = Path(path).suffix.lower()
        if ext in self._rejected:
            return None
        return self._mapping.get(ext)

    def accept(self, ext: str, profile: str) -> None:
        """Map ``ext`` to ``profile`` and clear any prior rejection."""
        ext = ext.lower()
        self._mapping[ext] = profile
        self._rejected.discard(ext)

    def reject(self, ext: str) -> None:
        """Stop suggesting for ``ext`` until the user accepts it again."""
        self._rejected.add(ext.lower())

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "mapping": dict(self._mapping),
            "rejected": sorted(self._rejected),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskProfileSuggester:
        suggester = cls(
            enabled=bool(data.get("enabled", False)),
            mapping={str(k): str(v) for k, v in data.get("mapping", {}).items()} or None,
        )
        suggester._rejected = {str(v).lower() for v in data.get("rejected", [])}
        return suggester
