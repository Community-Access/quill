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

# The episode record moved to models_episode under GATE-11 (extract, never
# rebaseline) when it grew the feed's own season/episode numbering; re-exported
# so every existing ``from ...models import PodcastEpisode`` keeps working.
from quill.core.podcasts.models_episode import PodcastEpisode as PodcastEpisode
from quill.core.podcasts.models_folder import ExpiredEntry as ExpiredEntry
from quill.core.podcasts.models_folder import PodcastFolder as PodcastFolder

# Re-exported so every existing `from ...models import Playlist / QueueItem`
# keeps working: these moved out under GATE-11 (extract, never rebaseline).
from quill.core.podcasts.models_playlists import (
    PLAYLIST_STATUS_MODES,
    Playlist,
    PlaylistRules,
)
from quill.core.podcasts.models_queue import QueueItem

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
    "PodcastEpisode",
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
class PodcastShow:
    """One subscribed feed, or one local (imported) show."""

    id: str
    title: str
    feed_url: str = ""  # "" for is_local shows
    #: The feed's own name when the listener renamed the podcast (ear.md R8);
    #: "" when not renamed. Renaming to nothing puts it back.
    feed_title: str = ""
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
            **({"feed_title": self.feed_title} if self.feed_title else {}),
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
            feed_title=str(data.get("feed_title", "") or ""),
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
