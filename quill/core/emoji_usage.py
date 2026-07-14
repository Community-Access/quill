"""Recently-used and favorited emoji (Insert > Emoji...), persisted per user.

Same shape as :mod:`quill.core.github.saved_items` (pinned repos +
favorites): atomic JSON writes under the app data dir, a corrupt file
degrades to empty rather than crashing, dedup on write. A separate module
from :mod:`quill.core.emoji_data` on purpose -- that module is the read-only,
committed catalog every user shares; this one is small, mutable, per-user
state layered on top of it. Un-favoriting or clearing recents never touches
the catalog itself -- an emoji removed from either list is still fully
present and searchable, just no longer shortcut-listed.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = ["EmojiUsage"]

_FILENAME = "emoji_usage.json"
_MAX_RECENT = 30


@dataclass(slots=True)
class EmojiUsage:
    """One store, two lists: recently-inserted emoji and favorited emoji.

    Both are plain lists of the emoji character itself (the catalog's own
    stable key) -- resolve them back to full :class:`~quill.core.emoji_data.EmojiEntry`
    rows with ``emoji_data.entries_by_chars()`` for display.
    """

    path: Path
    recent: list[str]
    favorites: list[str]

    @classmethod
    def load(cls, path: Path | None = None) -> EmojiUsage:
        target = path if path is not None else app_data_dir() / _FILENAME
        raw = read_json(target, default={})
        recent: list[str] = []
        favorites: list[str] = []
        if isinstance(raw, dict):
            recent = [c for c in raw.get("recent", []) if isinstance(c, str) and c]
            favorites = [c for c in raw.get("favorites", []) if isinstance(c, str) and c]
        return cls(path=target, recent=recent, favorites=favorites)

    def save(self) -> None:
        write_json_atomic(
            self.path,
            {"recent": list(self.recent), "favorites": list(self.favorites)},
        )

    # -- recently used -------------------------------------------------------- #

    def record_used(self, char: str) -> None:
        """Move *char* to the front of Recent (most-recent-first), capped at
        :data:`_MAX_RECENT`. Called once per successful Insert."""
        if not char:
            return
        self.recent = [char] + [c for c in self.recent if c != char]
        del self.recent[_MAX_RECENT:]
        self.save()

    def clear_recent(self) -> None:
        if self.recent:
            self.recent = []
            self.save()

    # -- favorites -------------------------------------------------------------- #

    def is_favorite(self, char: str) -> bool:
        return char in self.favorites

    def add_favorite(self, char: str) -> bool:
        """True when newly added; False if *char* was already a favorite."""
        if not char or char in self.favorites:
            return False
        self.favorites.append(char)
        self.save()
        return True

    def remove_favorite(self, char: str) -> bool:
        """Un-favorite *char*. True when it was a favorite; never touches the
        emoji catalog itself, only membership in this list."""
        if char not in self.favorites:
            return False
        self.favorites.remove(char)
        self.save()
        return True

    def toggle_favorite(self, char: str) -> bool:
        """Flip favorite status; returns the new state (True = now a favorite)."""
        if self.remove_favorite(char):
            return False
        self.add_favorite(char)
        return True
