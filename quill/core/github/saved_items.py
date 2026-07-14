"""Pinned repositories + favorited items for the GitHub Items viewer.

Ported from GHManage (https://github.com/kellylford/GHManage —
``pinned_repos.py`` / ``favorites.py``) onto QUILL's persistence conventions:
atomic JSON writes under the app data dir, corrupt files degrade to empty
(never a crash), keys deduplicate case-insensitively.

* **Pinned repositories** — a short, curated ``owner/repo`` list so switching
  between the handful of repos you actually work in is one pick, not retyping.
* **Favorites** — bookmarked items (an issue, a PR, a branch, a release...)
  from any repo, carrying enough metadata to list them in one mixed view and
  reopen them in the browser.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "FavoriteItem",
    "GitHubSavedItems",
]

_FILENAME = "github_saved_items.json"


@dataclass(frozen=True, slots=True)
class FavoriteItem:
    """A bookmarked GitHub item from any view, across any repo (GHManage parity)."""

    repo: str
    item_type: str  # "issue" / "pr" / "branch" / "commit" / "tag" / "release" / "workflow"
    url: str
    title: str
    subtitle: str = ""
    added_at: str = ""

    @property
    def key(self) -> str:
        return f"{self.repo.lower()}|{self.item_type}|{self.url}"


@dataclass(slots=True)
class GitHubSavedItems:
    """One store, three things: pinned repos, favorited items, and each
    view's column-visibility choice (Columns... menu, GHManage parity)."""

    path: Path
    pinned: list[str]
    favorites: list[FavoriteItem]
    columns: dict[str, list[str]]

    @classmethod
    def load(cls, path: Path | None = None) -> GitHubSavedItems:
        target = path if path is not None else app_data_dir() / _FILENAME
        raw = read_json(target, default={})
        pinned: list[str] = []
        favorites: list[FavoriteItem] = []
        columns: dict[str, list[str]] = {}
        if isinstance(raw, dict):
            for entry in raw.get("pinned", []):
                if isinstance(entry, str) and "/" in entry:
                    pinned.append(entry)
            for entry in raw.get("favorites", []):
                if not isinstance(entry, dict):
                    continue
                repo = str(entry.get("repo", ""))
                url = str(entry.get("url", ""))
                if not repo or not url:
                    continue
                favorites.append(
                    FavoriteItem(
                        repo=repo,
                        item_type=str(entry.get("item_type", "issue")),
                        url=url,
                        title=str(entry.get("title", "")),
                        subtitle=str(entry.get("subtitle", "")),
                        added_at=str(entry.get("added_at", "")),
                    )
                )
            raw_columns = raw.get("columns", {})
            if isinstance(raw_columns, dict):
                for view, cols in raw_columns.items():
                    if isinstance(view, str) and isinstance(cols, list):
                        names = [c for c in cols if isinstance(c, str)]
                        if names:
                            columns[view] = names
        return cls(path=target, pinned=pinned, favorites=favorites, columns=columns)

    def save(self) -> None:
        write_json_atomic(
            self.path,
            {
                "pinned": list(self.pinned),
                "favorites": [asdict(entry) for entry in self.favorites],
                "columns": {view: list(cols) for view, cols in self.columns.items()},
            },
        )

    # -- pinned repositories ------------------------------------------------ #

    def pin_repo(self, repo: str) -> bool:
        """Pin ``owner/repo`` (case-insensitive dedup). True when newly added."""
        name = repo.strip()
        if not name or "/" not in name:
            return False
        if name.lower() in (existing.lower() for existing in self.pinned):
            return False
        self.pinned.append(name)
        self.save()
        return True

    def unpin_repo(self, repo: str) -> bool:
        """Remove ``owner/repo`` from the pinned list. True when it was pinned."""
        before = len(self.pinned)
        self.pinned = [entry for entry in self.pinned if entry.lower() != repo.strip().lower()]
        if len(self.pinned) != before:
            self.save()
            return True
        return False

    def is_pinned(self, repo: str) -> bool:
        return repo.strip().lower() in (entry.lower() for entry in self.pinned)

    # -- favorites ------------------------------------------------------------ #

    def add_favorite(self, item: FavoriteItem) -> bool:
        """Bookmark an item (dedup by repo+type+url). True when newly added."""
        if not item.repo or not item.url:
            return False
        if any(existing.key == item.key for existing in self.favorites):
            return False
        stamped = (
            item
            if item.added_at
            else FavoriteItem(
                repo=item.repo,
                item_type=item.item_type,
                url=item.url,
                title=item.title,
                subtitle=item.subtitle,
                added_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        )
        self.favorites.append(stamped)
        self.save()
        return True

    def remove_favorite(self, key: str) -> bool:
        before = len(self.favorites)
        self.favorites = [entry for entry in self.favorites if entry.key != key]
        if len(self.favorites) != before:
            self.save()
            return True
        return False

    # -- per-view column visibility (Columns... menu) ------------------------ #

    def get_columns(self, view: str, default: list[str]) -> list[str]:
        """Saved visible columns for *view*, or *default* if never set."""
        saved = self.columns.get(view)
        return list(saved) if saved else list(default)

    def set_columns(self, view: str, visible: list[str]) -> None:
        """Persist *visible* as the chosen columns for *view*."""
        self.columns[view] = list(visible)
        self.save()
