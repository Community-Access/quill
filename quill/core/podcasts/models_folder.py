"""Library folders and Recently Expired entries (extracted from ``models.py``).

Moved under GATE-11 so ``PodcastShow`` and ``PodcastEpisode`` could keep the
feed's own name beside a rename (ear.md R8). ``models.py`` re-exports both, so
every import of them from there still works. wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.podcasts.models_queue import coerce_int as _coerce_int


@dataclass(slots=True)
class PodcastFolder:
    """Organizes shows. A show lives in exactly one folder (or none).
    Arbitrarily deep nesting via ``parent_folder_id`` (adjacency list)."""

    id: str
    name: str
    parent_folder_id: str | None = None
    #: Where this folder sits among its siblings. Move Up / Move Down write it
    #: (``folder_actions.reorder_folder``), and it exists because a tree that
    #: can only be rearranged by dragging is a tree somebody using a screen
    #: reader cannot rearrange at all.
    sort_order: int = 0

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {"id": self.id, "name": self.name}
        if self.parent_folder_id:
            row["parent_folder_id"] = self.parent_folder_id
        if self.sort_order:
            row["sort_order"] = self.sort_order
        return row

    @classmethod
    def from_dict(cls, data: object) -> PodcastFolder | None:
        if not isinstance(data, dict):
            return None
        folder_id = str(data.get("id", "")).strip()
        name = str(data.get("name", "")).strip()
        if not folder_id or not name:
            return None
        parent = str(data.get("parent_folder_id", "") or "").strip()
        return cls(
            id=folder_id,
            name=name,
            parent_folder_id=parent or None,
            sort_order=_coerce_int(data.get("sort_order"), 0),
        )


@dataclass(slots=True)
class ExpiredEntry:
    """One episode Queue Expiration lifted out of the Play Queue (1.1.0).

    Held in ``PodcastLibrary.recently_expired`` for
    :data:`~quill.core.podcasts.expiration.RECENTLY_EXPIRED_HOLD_DAYS` days so
    it can be restored, then swept -- at which point (and only then) its
    downloaded file is deleted. Nothing is ever removed from the library
    itself: expiring is a queue action, not a delete.
    """

    show_id: str
    episode_guid: str
    expired_at: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "show_id": self.show_id,
            "episode_guid": self.episode_guid,
            "expired_at": self.expired_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> ExpiredEntry | None:
        if not isinstance(data, dict):
            return None
        show_id = str(data.get("show_id", "")).strip()
        episode_guid = str(data.get("episode_guid", "")).strip()
        if not show_id or not episode_guid:
            return None
        return cls(
            show_id=show_id,
            episode_guid=episode_guid,
            expired_at=str(data.get("expired_at", "")).strip(),
        )
