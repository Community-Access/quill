"""The podcast library: subscriptions, folders, and global settings.

One atomic-JSON store, the standard QUILL settings-surface pattern (see
``core/publish/destinations.py``). The episode catalog is durable, not an
ephemeral re-fetch: :func:`merge_episodes` adds new episodes and refreshes
metadata for ones already known, but never drops an episode just because a
feed refresh no longer lists it -- an old episode can scroll off a feed's
live listing while you still have it downloaded, or care about its played
state. wx-free, strict-typed.
"""

from __future__ import annotations

import dataclasses
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.podcasts.models import (
    ExpiredEntry,
    Playlist,
    PodcastEpisode,
    PodcastFolder,
    PodcastSettings,
    PodcastShow,
    QueueItem,
    now_iso,
)
from quill.core.podcasts.onboarding import OnboardingState

_FILE_NAME = "podcasts_library.json"


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class PodcastLibrary:
    """Every subscribed show, every library folder, and the global defaults."""

    shows: list[PodcastShow] = field(default_factory=list)
    folders: list[PodcastFolder] = field(default_factory=list)
    settings: PodcastSettings = field(default_factory=PodcastSettings)
    #: The cross-show Play Queue (Phase 4): ordered episode references,
    #: persisted with the library. Operations live in podcasts.queue.
    queue: list[QueueItem] = field(default_factory=list)
    #: The Inbox's own folder tree (Phase 4) -- independent of the library
    #: folders; organizes episodes, not shows. Operations live in
    #: podcasts.inbox.
    inbox_folders: list[PodcastFolder] = field(default_factory=list)
    #: Manual Inbox filings: inbox_key(show, episode) -> folder id ("" =
    #: explicitly unfiled at the Inbox top level).
    inbox_assignments: dict[str, str] = field(default_factory=dict)
    #: Saved playlists (Phase 5) -- Smart (rule-based, auto-updating) and
    #: manual (a curated, ordered episode list). Operations live in
    #: podcasts.playlists.
    playlists: list[Playlist] = field(default_factory=list)
    #: Recently Expired (1.1.0): episodes Queue Expiration lifted out of the
    #: Play Queue, restorable for a week. A real stored list, not a derived
    #: view -- which is why it lives here and not in virtual_views.py.
    #: Operations live in podcasts.expiration.
    recently_expired: list[ExpiredEntry] = field(default_factory=list)
    #: What the listener has already been shown: the first-run flow, and which
    #: one-shot tips have fired. Stored as a set of ids rather than a version
    #: stamp, so a tip added next year still fires for somebody who has been
    #: using Cast for a year. Operations live in podcasts.onboarding.
    onboarding: OnboardingState = field(default_factory=OnboardingState)

    def queue_episode(self, show_id: str, episode_guid: str) -> bool:
        """Append an episode to the Play Queue (False when already queued).
        Thin convenience over podcasts.queue.add_to_queue for callers that
        only have the library."""
        for item in self.queue:
            if item.show_id == show_id and item.episode_guid == episode_guid:
                return False
        self.queue.append(QueueItem(show_id=show_id, episode_guid=episode_guid, added_at=now_iso()))
        return True

    def find_show(self, show_id: str) -> PodcastShow | None:
        for show in self.shows:
            if show.id == show_id:
                return show
        return None

    def find_show_by_feed_url(self, feed_url: str) -> PodcastShow | None:
        for show in self.shows:
            if show.feed_url and show.feed_url == feed_url:
                return show
        return None

    def find_folder(self, folder_id: str) -> PodcastFolder | None:
        for folder in self.folders:
            if folder.id == folder_id:
                return folder
        return None

    def add_show(self, show: PodcastShow) -> bool:
        """Add *show*; returns False without changes if its feed URL is
        already subscribed (duplicate detection)."""
        if show.feed_url and self.find_show_by_feed_url(show.feed_url) is not None:
            return False
        self.shows.append(show)
        return True

    def remove_show(self, show_id: str) -> bool:
        before = len(self.shows)
        self.shows = [s for s in self.shows if s.id != show_id]
        return len(self.shows) != before

    def move_show(self, show_id: str, offset: int) -> bool:
        """Move a show one place up (*offset* -1) or down (+1) among the
        shows of its own folder -- the Move Up/Down behind the ``"custom"``
        show sort. Shows in other folders are untouched: swapping with the
        adjacent *sibling* keeps every folder's own custom order intact even
        though all shows live in one flat list. Returns False at the edge."""
        show = self.find_show(show_id)
        if show is None:
            return False
        siblings = [s for s in self.shows if s.folder_id == show.folder_id]
        position = siblings.index(show) + offset
        if offset not in (-1, 1) or not 0 <= position < len(siblings):
            return False
        other = siblings[position]
        i, j = self.shows.index(show), self.shows.index(other)
        self.shows[i], self.shows[j] = self.shows[j], self.shows[i]
        return True

    def add_folder(self, name: str, *, parent_folder_id: str | None = None) -> PodcastFolder:
        folder = PodcastFolder(id=new_id(), name=name, parent_folder_id=parent_folder_id)
        self.folders.append(folder)
        return folder

    def delete_folder(self, folder_id: str, *, contents: str = "promote") -> list[PodcastShow]:
        """Delete a library folder and its whole subtree.

        ``contents="promote"`` (the safe default) moves the subtree's shows
        and immediate subfolders up to the deleted folder's parent, so
        nothing is ever silently unsubscribed. ``contents="remove"``
        unsubscribes every show in the subtree; the removed shows are
        returned so the caller can apply its downloaded-files policy.
        """
        folder = self.find_folder(folder_id)
        if folder is None:
            return []
        subtree = {folder_id}
        grew = True
        while grew:
            grew = False
            for candidate in self.folders:
                if candidate.parent_folder_id in subtree and candidate.id not in subtree:
                    subtree.add(candidate.id)
                    grew = True
        parent_id = folder.parent_folder_id
        removed: list[PodcastShow] = []
        if contents == "remove":
            removed = [s for s in self.shows if s.folder_id in subtree]
            self.shows = [s for s in self.shows if s.folder_id not in subtree]
            self.folders = [f for f in self.folders if f.id not in subtree]
        else:
            # Promote keeps the subtree's inner structure intact: only the
            # deleted folder itself goes. Its DIRECT contents (shows filed
            # right in it, and its immediate subfolders) move up to its
            # parent; anything deeper stays inside those surviving folders.
            for show in self.shows:
                if show.folder_id == folder_id:
                    show.folder_id = parent_id
            for candidate in self.folders:
                if candidate.parent_folder_id == folder_id:
                    candidate.parent_folder_id = parent_id
            self.folders = [f for f in self.folders if f.id != folder_id]
        return removed

    def find_or_create_folder_path(self, names: list[str]) -> str | None:
        """Walk/create a folder chain by name (used by OPML import, whose
        nested <outline> folders are addressed by name, not id)."""
        parent_id: str | None = None
        for name in names:
            existing = next(
                (f for f in self.folders if f.name == name and f.parent_folder_id == parent_id),
                None,
            )
            if existing is not None:
                parent_id = existing.id
            else:
                parent_id = self.add_folder(name, parent_folder_id=parent_id).id
        return parent_id

    def effective_settings(self, show: PodcastShow) -> PodcastSettings:
        """The show's own settings where it overrides, the library defaults
        elsewhere. Phase 1 only stores whole-record overrides (no per-field
        merge yet), so this is currently just "show's or global's"."""
        return show.settings if show.settings is not None else self.settings

    def apply_show_override(self, show: PodcastShow, **updates: object) -> PodcastSettings:
        """Set field(s) on *show*'s own settings override, cloning from
        whatever is currently effective for it (its own override if it
        already has one, else the library default) so any other override
        this show already carries survives -- never resets sibling fields
        to the class defaults. The one correct way to write a per-show
        override; every settings field works this way (speed, sort order,
        etc.), not just the field being changed right now."""
        base = self.effective_settings(show)
        # dataclasses.replace's overload can't verify heterogeneous **kwargs
        # against each field's own type; the caller passing a genuine
        # PodcastSettings field name/value is on them, same as **kwargs
        # anywhere else in the codebase that fans out into a typed callee.
        show.settings = dataclasses.replace(base, **updates)  # type: ignore[arg-type]
        return show.settings

    def find_playlist(self, playlist_id: str) -> Playlist | None:
        for playlist in self.playlists:
            if playlist.id == playlist_id:
                return playlist
        return None

    def add_playlist(self, playlist: Playlist) -> None:
        self.playlists.append(playlist)

    def remove_playlist(self, playlist_id: str) -> bool:
        before = len(self.playlists)
        self.playlists = [p for p in self.playlists if p.id != playlist_id]
        return len(self.playlists) != before

    def rename_playlist(self, playlist_id: str, name: str) -> bool:
        playlist = self.find_playlist(playlist_id)
        if playlist is None:
            return False
        cleaned = name.strip()
        if not cleaned:
            return False
        playlist.name = cleaned
        return True


def merge_episodes(
    show: PodcastShow,
    fetched: list[PodcastEpisode],
    *,
    republished: list[str] | None = None,
) -> int:
    """Merge freshly-fetched episodes into *show* in place; returns the
    count of genuinely new episodes. Existing episodes (matched by guid) get
    their feed-supplied metadata refreshed but keep their local state
    (played, position, downloaded_path, mode_override) untouched -- a feed
    republishing an old guid with new text must not reset what you already
    did with that episode.

    *republished*, when given, collects the guids of episodes the publisher
    **re-published**: the feed now carries a later ``published`` stamp for a
    guid already in the library. That is a deliberate act by the publisher --
    a corrected file, a re-cut, an episode pulled and reissued -- and it is
    the signal :func:`quill.core.podcasts.inbox.resurface_republished` uses to
    bring an episode back to the Inbox.

    Collected here rather than computed by the caller because this is the only
    moment both stamps exist: the line below overwrites the old one.
    """
    existing_by_guid = {e.guid: e for e in show.episodes}
    new_count = 0
    for fetched_episode in fetched:
        current = existing_by_guid.get(fetched_episode.guid)
        if current is None:
            show.episodes.append(fetched_episode)
            new_count += 1
            continue
        if (
            republished is not None
            and fetched_episode.published
            and current.published
            and fetched_episode.published > current.published
        ):
            republished.append(current.guid)
        current.title = fetched_episode.title
        current.audio_url = fetched_episode.audio_url
        current.published = fetched_episode.published
        current.duration_seconds = fetched_episode.duration_seconds
        current.description = fetched_episode.description
        current.chapters_url = fetched_episode.chapters_url
        current.transcript_url = fetched_episode.transcript_url
        current.transcript_type = fetched_episode.transcript_type
        # Feed-supplied like everything above it: a publisher who adds a guest
        # credit or marks a soundbite after publishing gets it on the next
        # refresh. Never cleared by a feed that has stopped carrying them --
        # a namespace the publisher dropped is not a reason to forget what it
        # said, and an empty replacement is far more often a partial feed.
        if not fetched_episode.tags.is_empty:
            current.tags = fetched_episode.tags
    return new_count


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_library(data_dir: Path) -> PodcastLibrary:
    """Read the saved library (an absent or broken file reads as empty)."""
    path = _store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return PodcastLibrary()
    if not isinstance(raw, dict):
        return PodcastLibrary()
    shows: list[PodcastShow] = []
    for entry in raw.get("shows", []) if isinstance(raw.get("shows"), list) else []:
        if not isinstance(entry, dict):
            continue
        show = PodcastShow.from_dict(entry)
        if show is not None:
            shows.append(show)
    folders: list[PodcastFolder] = []
    for entry in raw.get("folders", []) if isinstance(raw.get("folders"), list) else []:
        if not isinstance(entry, dict):
            continue
        folder_id = str(entry.get("id", "")).strip()
        name = str(entry.get("name", "")).strip()
        if not folder_id or not name:
            continue
        parent_id = entry.get("parent_folder_id")
        folders.append(
            PodcastFolder(
                id=folder_id,
                name=name,
                parent_folder_id=str(parent_id)
                if isinstance(parent_id, str) and parent_id
                else None,
            )
        )
    settings_data = raw.get("settings")
    settings = (
        PodcastSettings.from_dict(settings_data)
        if isinstance(settings_data, dict)
        else PodcastSettings()
    )
    queue: list[QueueItem] = []
    for entry in raw.get("queue", []) if isinstance(raw.get("queue"), list) else []:
        item = QueueItem.from_dict(entry)
        if item is not None:
            queue.append(item)
    inbox_folders: list[PodcastFolder] = []
    for entry in raw.get("inbox_folders", []) if isinstance(raw.get("inbox_folders"), list) else []:
        if not isinstance(entry, dict):
            continue
        folder_id = str(entry.get("id", "")).strip()
        name = str(entry.get("name", "")).strip()
        if not folder_id or not name:
            continue
        parent_id = entry.get("parent_folder_id")
        inbox_folders.append(
            PodcastFolder(
                id=folder_id,
                name=name,
                parent_folder_id=str(parent_id)
                if isinstance(parent_id, str) and parent_id
                else None,
            )
        )
    assignments_raw = raw.get("inbox_assignments")
    inbox_assignments = (
        {str(k): str(v) for k, v in assignments_raw.items()}
        if isinstance(assignments_raw, dict)
        else {}
    )
    playlists: list[Playlist] = []
    for entry in raw.get("playlists", []) if isinstance(raw.get("playlists"), list) else []:
        playlist = Playlist.from_dict(entry)
        if playlist is not None:
            playlists.append(playlist)
    recently_expired: list[ExpiredEntry] = []
    expired_raw = raw.get("recently_expired")
    for entry in expired_raw if isinstance(expired_raw, list) else []:
        expired_entry = ExpiredEntry.from_dict(entry)
        if expired_entry is not None:
            recently_expired.append(expired_entry)
    return PodcastLibrary(
        shows=shows,
        folders=folders,
        settings=settings,
        queue=queue,
        inbox_folders=inbox_folders,
        inbox_assignments=inbox_assignments,
        playlists=playlists,
        recently_expired=recently_expired,
        onboarding=OnboardingState.from_dict(raw.get("onboarding")),
    )


def save_library(data_dir: Path, library: PodcastLibrary) -> None:
    """Persist the library atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "shows": [s.to_dict() for s in library.shows],
            "folders": [
                {"id": f.id, "name": f.name, "parent_folder_id": f.parent_folder_id}
                for f in library.folders
            ],
            "settings": library.settings.to_dict(),
            "queue": [q.to_dict() for q in library.queue],
            "inbox_folders": [
                {"id": f.id, "name": f.name, "parent_folder_id": f.parent_folder_id}
                for f in library.inbox_folders
            ],
            "inbox_assignments": dict(library.inbox_assignments),
            "playlists": [p.to_dict() for p in library.playlists],
            "recently_expired": [e.to_dict() for e in library.recently_expired],
            "onboarding": library.onboarding.to_dict(),
        },
    )
