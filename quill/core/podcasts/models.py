"""The Podcasts data model: folders, shows, episodes, and settings.

Folders, shows, episodes, and settings for the shipped feature (PRD
§5.84g); a few fields exist now purely as forward schema for later phases
(see ``docs/planning/podcasts.md``) so the on-disk shape never needs a
migration later: ``is_favorite`` for the planned Favorites virtual view,
``route_to_inbox`` / ``inbox_default_folder_id`` for the planned Inbox.
``position_ms`` (resume sync) is already wired up and in active use. The
still-forward-only fields are plain default-off values nothing reads or
writes yet, not a half-built UI. wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

# Re-exported so every existing `from ...models import Playlist / QueueItem`
# keeps working: these moved out under GATE-11 (extract, never rebaseline).
from quill.core.podcasts.models_playlists import (
    PLAYLIST_STATUS_MODES,
    Playlist,
    PlaylistRules,
)
from quill.core.podcasts.models_queue import QueueItem
from quill.core.podcasts.models_queue import coerce_int as _coerce_int

# The settings record and its coercion helpers moved to models_settings under
# GATE-11; re-exported because the call sites import them from ``models`` and
# the split is an organisation decision, not an API one.
from quill.core.podcasts.models_settings import (
    SPEED_MAX as SPEED_MAX,
)
from quill.core.podcasts.models_settings import (
    SPEED_MIN as SPEED_MIN,
)
from quill.core.podcasts.models_settings import (
    PodcastSettings as PodcastSettings,
)
from quill.core.podcasts.models_settings import (
    clamp_speed as clamp_speed,
)
from quill.core.podcasts.namespace_tags import NamespaceTags

__all__ = [
    "PLAYLIST_STATUS_MODES",
    "Playlist",
    "PlaylistRules",
    "QueueItem",
]


#: Playback speed range (1.1.0). The old six-choice dropdown only offered
#: 0.75x-2.0x; the model always permitted anything, and the engines (mpv and
#: wx.media alike) hold pitch across this range. Enforced in ``from_dict`` so a
#: hand-edited or synced settings file can never leave a show unplayably fast.
def now_iso() -> str:
    """The current moment as an ISO 8601 UTC timestamp.

    One helper so every timestamp this feature stores (a queue slot's
    ``added_at``, an expiry, a listening session) is written the same way and
    compares as a plain string.
    """
    return datetime.now(UTC).isoformat()


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


#: PlaylistRules.episode_status.


@dataclass(slots=True)
class PodcastEpisode:
    """One episode of a subscribed (or local) show."""

    guid: str
    title: str
    audio_url: str
    published: str = ""
    duration_seconds: int = 0
    description: str = ""
    chapters_url: str = ""
    transcript_url: str = ""
    transcript_type: str = ""
    downloaded_path: str = ""
    mode_override: str = ""  # "" | "stream" | "download"
    played: bool = False
    position_ms: int = 0  # resume position; syncs via QUILL Sync (guid-keyed)
    #: When the place above was last decided. RFC 3339 UTC ending ``Z``, so
    #: plain string comparison sorts it and the merge needs no date parsing.
    #: Merging positions is last-write-wins, never furthest-wins -- see
    #: ``core/podcasts/position_sync.py`` -- so without this field there is
    #: nothing to merge on and a place cannot travel between devices at all.
    position_updated_at: str = ""
    #: Podcasting 2.0 tags read from this item: who is on it, the moments the
    #: publisher marked, alternate audio, where it is about. Serialised only
    #: when non-empty, so feeds that publish none of it cost nothing.
    tags: NamespaceTags = field(default_factory=NamespaceTags)

    def to_dict(self) -> dict[str, object]:
        return {
            "guid": self.guid,
            "title": self.title,
            "audio_url": self.audio_url,
            "published": self.published,
            "duration_seconds": self.duration_seconds,
            "description": self.description,
            "chapters_url": self.chapters_url,
            "transcript_url": self.transcript_url,
            "transcript_type": self.transcript_type,
            "downloaded_path": self.downloaded_path,
            "mode_override": self.mode_override,
            "played": self.played,
            "position_ms": self.position_ms,
            **(
                {"position_updated_at": self.position_updated_at}
                if self.position_updated_at
                else {}
            ),
            **({"tags": self.tags.to_dict()} if not self.tags.is_empty else {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastEpisode | None:
        guid = str(data.get("guid", "")).strip()
        title = str(data.get("title", "")).strip()
        audio_url = str(data.get("audio_url", "")).strip()
        if not guid or not title or not audio_url:
            return None
        return cls(
            guid=guid,
            title=title,
            audio_url=audio_url,
            published=str(data.get("published", "")),
            duration_seconds=_coerce_int(data.get("duration_seconds"), 0),
            description=str(data.get("description", "")),
            chapters_url=str(data.get("chapters_url", "")),
            transcript_url=str(data.get("transcript_url", "")),
            transcript_type=str(data.get("transcript_type", "")),
            downloaded_path=str(data.get("downloaded_path", "")),
            mode_override=str(data.get("mode_override", "")),
            played=bool(data.get("played", False)),
            position_ms=_coerce_int(data.get("position_ms"), 0),
            position_updated_at=str(data.get("position_updated_at", "")),
            tags=NamespaceTags.from_dict(data.get("tags")),
        )


@dataclass(slots=True)
class PodcastShow:
    """One subscribed feed, or one local (imported) show."""

    id: str
    title: str
    feed_url: str = ""  # "" for is_local shows
    #: Private feeds (HTTP Basic auth): the sign-in username. Not a secret;
    #: the password lives in the platform secret store (feed_auth.py) and is
    #: deliberately NOT a field here -- it must never reach podcasts.json.
    feed_username: str = ""
    homepage: str = ""
    artwork_url: str = ""
    # OPML 2.0's optional presentation attributes, stored so a subscription list
    # survives a round trip -- export used to drop them, silently handing back a
    # poorer file than it was given. Feed-derived, so cheap to carry.
    description: str = ""
    language: str = ""
    category: str = ""
    is_local: bool = False
    folder_id: str | None = None
    paused: bool = False
    is_favorite: bool = False  # Favorites virtual view (Phase 4)
    #: Local shows only (Phase 4): a folder QUILL watches; audio files dropped
    #: there become new episodes on the next scan (local_import.py).
    watched_folder: str = ""
    route_to_inbox: bool = False  # §9, not yet surfaced in the UI this phase
    inbox_default_folder_id: str | None = None  # §9
    #: Auto-Queue (1.1.0): a new episode of this show goes straight into the
    #: Play Queue on refresh, skipping the Inbox even when the show routes
    #: there -- the "I always listen to this one" switch.
    auto_queue: bool = False
    #: Per-show new-episode notification (1.1.0): the background check
    #: announces this show's new episodes by name (speech, braille, and a
    #: tray balloon) instead of only counting them in the shared summary.
    #: Deliberately per show: being told about every feed is being told about
    #: nothing.
    notify_new_episodes: bool = False
    #: The show's own Podcasting 2.0 tags: regular hosts, the shows it
    #: recommends, its support link, any live stream it carries.
    tags: NamespaceTags = field(default_factory=NamespaceTags)
    settings: PodcastSettings | None = None
    episodes: list[PodcastEpisode] = field(default_factory=list)

    def find_episode(self, guid: str) -> PodcastEpisode | None:
        for episode in self.episodes:
            if episode.guid == guid:
                return episode
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "feed_url": self.feed_url,
            "feed_username": self.feed_username,
            "homepage": self.homepage,
            "artwork_url": self.artwork_url,
            "description": self.description,
            "language": self.language,
            "category": self.category,
            "is_local": self.is_local,
            "watched_folder": self.watched_folder,
            "folder_id": self.folder_id,
            "paused": self.paused,
            "is_favorite": self.is_favorite,
            "route_to_inbox": self.route_to_inbox,
            "inbox_default_folder_id": self.inbox_default_folder_id,
            "auto_queue": self.auto_queue,
            "notify_new_episodes": self.notify_new_episodes,
            **({"tags": self.tags.to_dict()} if not self.tags.is_empty else {}),
            "settings": self.settings.to_dict() if self.settings is not None else None,
            "episodes": [e.to_dict() for e in self.episodes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastShow | None:
        show_id = str(data.get("id", "")).strip()
        title = str(data.get("title", "")).strip()
        if not show_id or not title:
            return None
        settings_data = data.get("settings")
        settings = (
            PodcastSettings.from_dict(settings_data) if isinstance(settings_data, dict) else None
        )
        episodes_data = data.get("episodes")
        episodes: list[PodcastEpisode] = []
        for entry in episodes_data if isinstance(episodes_data, list) else []:
            if not isinstance(entry, dict):
                continue
            episode = PodcastEpisode.from_dict(entry)
            if episode is not None:
                episodes.append(episode)
        folder_id = data.get("folder_id")
        inbox_folder_id = data.get("inbox_default_folder_id")
        return cls(
            id=show_id,
            title=title,
            feed_url=str(data.get("feed_url", "")),
            feed_username=str(data.get("feed_username", "")),
            homepage=str(data.get("homepage", "")),
            artwork_url=str(data.get("artwork_url", "")),
            description=str(data.get("description", "")),
            language=str(data.get("language", "")),
            category=str(data.get("category", "")),
            is_local=bool(data.get("is_local", False)),
            watched_folder=str(data.get("watched_folder", "")),
            folder_id=str(folder_id) if isinstance(folder_id, str) and folder_id else None,
            paused=bool(data.get("paused", False)),
            is_favorite=bool(data.get("is_favorite", False)),
            route_to_inbox=bool(data.get("route_to_inbox", False)),
            auto_queue=bool(data.get("auto_queue", False)),
            notify_new_episodes=bool(data.get("notify_new_episodes", False)),
            tags=NamespaceTags.from_dict(data.get("tags")),
            inbox_default_folder_id=(
                str(inbox_folder_id)
                if isinstance(inbox_folder_id, str) and inbox_folder_id
                else None
            ),
            settings=settings,
            episodes=episodes,
        )
