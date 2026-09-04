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
from quill.core.podcasts.models_filters import EpisodeFilterConfiguration
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
    #: When an automatic check last read these feeds, whichever app ran it
    #: (ISO-8601 UTC; "" = never). Shared deliberately: the *cadence* is each
    #: app's own -- one switch for both would mean turning the check on in Cast
    #: turned it on in Radio -- but the *work* is one job over one set of feeds,
    #: so whichever app does it says when, and the other stays quiet inside the
    #: same interval. See refresh_policy.is_due.
    last_auto_check: str = ""
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
    #: Episode Filters: show id -> that podcast's ingest rule set. Held here
    #: rather than on ``PodcastShow`` for the same reason the Inbox's own
    #: assignments are: it is *local curation*, it has no OPML equivalent in
    #: either direction, and a show that is unsubscribed and re-added is a new
    #: subscription that should not inherit somebody's forgotten rules.
    #: Absent = no filter, which is exactly how every podcast behaved before
    #: the feature existed. Operations live in podcasts.episode_filters and
    #: podcasts.episode_filter_maintenance.
    episode_filters: dict[str, EpisodeFilterConfiguration] = field(default_factory=dict)
    #: The Episode Filters runtime safety warning: show id -> when a refresh
    #: found that Keep matching had rejected *everything* new. Separate from
    #: the configuration on purpose -- the rules are a decision the listener
    #: made, and this is a thing that happened to them, which Podcast Settings
    #: surfaces as Needs review until they look. Reviewing and saving clears it.
    episode_filter_reviews: dict[str, str] = field(default_factory=dict)
    #: Episode Filter exemptions: show id -> the guids of episodes the filter
    #: is told to skip. A rule is a guess about a pattern; an exemption is the
    #: listener being specific about one episode, and specific wins. Kept
    #: beside the rules rather than on the episode so an exemption survives a
    #: feed re-fetch and costs nothing for the vast majority of episodes that
    #: have none.
    episode_filter_exceptions: dict[str, list[str]] = field(default_factory=dict)
    #: Settings that arrived after ``PodcastSettings`` stopped being able to
    #: grow: setting id -> the shared default's value. Only ids the catalogue
    #: knows are ever read (``settings_resolver``), so a value written by a
    #: newer build is carried through a downgrade rather than acted on.
    extra_settings: dict[str, object] = field(default_factory=dict)
    #: The inheritance chain's storage: ``"folder:<id>"`` / ``"show:<id>"`` ->
    #: the settings **that level has an opinion about**, and only those.
    #:
    #: Sparse on purpose, and it is the whole of the fix. A whole-record copy
    #: cannot tell "I have no opinion" from "I want exactly this", so the first
    #: time anything wrote one, that podcast stopped following the shared
    #: default forever. An absent key here means the level above answers.
    #: Operations live in podcasts.settings_resolver.
    scope_overrides: dict[str, dict[str, object]] = field(default_factory=dict)
    #: Free-text labels per podcast: show id -> the listener's own words for
    #: it. A folder is one home; labels are as many as somebody likes, which is
    #: why they -- not folders-as-a-set -- are the answer to "this show is both
    #: news and short". Usable as a smart-playlist rule and as a tree filter.
    show_labels: dict[str, list[str]] = field(default_factory=dict)
    #: Per-podcast check bookkeeping: show id -> ``{"checked", "failures",
    #: "published"}``. Needed the moment a podcast can have a cadence of its
    #: own (7.1): one shared stamp can say when *a* check ran, and cannot say
    #: whether this podcast's own interval has elapsed. Also carries the two
    #: counters the gone-quiet and failed-check notices read (7.19).
    show_check_state: dict[str, dict[str, object]] = field(default_factory=dict)
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
        """The whole settings record in force for *show*.

        Resolved through the four-level chain -- shared default, folder
        (outermost first), podcast -- by
        :func:`quill.core.podcasts.settings_resolver.effective_settings`. Kept
        as a method because every caller in the app already asks the library
        this question; what changed underneath is that a folder is now a real
        level and an override stores only the fields it has an opinion about.
        """
        from quill.core.podcasts.settings_resolver import effective_settings

        return effective_settings(self, show)

    def apply_show_override(self, show: PodcastShow, **updates: object) -> PodcastSettings:
        """Set field(s) as *this podcast's* opinion, and only those fields.

        The one correct way to write a per-show override, and its behaviour
        changed in an important way: it used to clone the whole effective
        record, which froze every *other* setting at whatever the shared
        default happened to be that day. It now writes exactly the fields
        named, so everything else keeps following the folder and the shared
        default -- which is the difference between "I have no opinion" and "I
        want exactly this", and the reason changing a shared default is worth
        doing at all.
        """
        from quill.core.podcasts import settings_catalog
        from quill.core.podcasts.settings_resolver import (
            LEVEL_SHOW,
            migrate_show,
            set_value,
        )

        migrate_show(self, show)
        for name, value in updates.items():
            definition = settings_catalog.by_field(name)
            if definition is None:
                # A field with no catalogue entry is still a real field; store
                # it by name so nothing is silently dropped, and let the
                # catalogue catch up.
                bucket = self.scope_overrides.setdefault(f"show:{show.id}", {})
                bucket[name] = value
                continue
            set_value(self, definition, value, level=LEVEL_SHOW, scope_id=show.id)
        return self.effective_settings(show)

    def labels_for(self, show_id: str) -> list[str]:
        """This podcast's labels, in the order they were added."""
        return list(self.show_labels.get(show_id, ()))

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
        # Feed-supplied like everything around it, and only ever *upward*: a
        # publisher who adds numbering later gets it on the next refresh, and
        # a partial feed that stopped sending it does not un-number episodes
        # that a sort is currently relying on.
        current.season = fetched_episode.season or current.season
        current.episode_number = fetched_episode.episode_number or current.episode_number
        current.episode_type = fetched_episode.episode_type or current.episode_type
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
    # Through the model rather than field by field: PodcastFolder gained
    # sort_order (Move Up / Move Down), and a second reader here would have
    # silently dropped it on every save.
    for entry in raw.get("folders", []) if isinstance(raw.get("folders"), list) else []:
        folder = PodcastFolder.from_dict(entry)
        if folder is not None:
            folders.append(folder)
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
        folder = PodcastFolder.from_dict(entry)
        if folder is not None:
            inbox_folders.append(folder)
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
    # Episode Filters. A configuration this build cannot read (a newer
    # version, a malformed record) is dropped rather than half-understood:
    # ``from_dict`` answers None and the podcast simply has no filter, which
    # is the behaviour it had before the feature existed.
    episode_filters: dict[str, EpisodeFilterConfiguration] = {}
    filters_raw = raw.get("episode_filters")
    if isinstance(filters_raw, dict):
        for show_id, entry in filters_raw.items():
            config = EpisodeFilterConfiguration.from_dict(entry)
            if config is not None:
                episode_filters[str(show_id)] = config
    reviews_raw = raw.get("episode_filter_reviews")
    episode_filter_reviews = (
        {str(k): str(v) for k, v in reviews_raw.items()} if isinstance(reviews_raw, dict) else {}
    )
    extra_raw = raw.get("extra_settings")
    extra_settings = (
        {str(k): v for k, v in extra_raw.items()} if isinstance(extra_raw, dict) else {}
    )
    overrides_raw = raw.get("scope_overrides")
    scope_overrides: dict[str, dict[str, object]] = {}
    if isinstance(overrides_raw, dict):
        for scope, values in overrides_raw.items():
            if isinstance(values, dict) and values:
                scope_overrides[str(scope)] = {str(k): v for k, v in values.items()}
    check_raw = raw.get("show_check_state")
    show_check_state: dict[str, dict[str, object]] = {}
    if isinstance(check_raw, dict):
        for show_id, state in check_raw.items():
            if isinstance(state, dict):
                show_check_state[str(show_id)] = {str(k): v for k, v in state.items()}
    labels_raw = raw.get("show_labels")
    show_labels: dict[str, list[str]] = {}
    if isinstance(labels_raw, dict):
        for show_id, names in labels_raw.items():
            if isinstance(names, list):
                cleaned = [str(name).strip() for name in names if str(name).strip()]
                if cleaned:
                    show_labels[str(show_id)] = cleaned
    exceptions_raw = raw.get("episode_filter_exceptions")
    episode_filter_exceptions: dict[str, list[str]] = {}
    if isinstance(exceptions_raw, dict):
        for show_id, guids in exceptions_raw.items():
            if isinstance(guids, list):
                cleaned = [str(guid) for guid in guids if str(guid)]
                if cleaned:
                    episode_filter_exceptions[str(show_id)] = cleaned
    library = PodcastLibrary(
        shows=shows,
        folders=folders,
        settings=settings,
        queue=queue,
        inbox_folders=inbox_folders,
        inbox_assignments=inbox_assignments,
        playlists=playlists,
        recently_expired=recently_expired,
        episode_filters=episode_filters,
        episode_filter_reviews=episode_filter_reviews,
        episode_filter_exceptions=episode_filter_exceptions,
        extra_settings=extra_settings,
        scope_overrides=scope_overrides,
        show_labels=show_labels,
        show_check_state=show_check_state,
        onboarding=OnboardingState.from_dict(raw.get("onboarding")),
        last_auto_check=str(raw.get("last_auto_check", "") or ""),
    )
    # A library written before the four-level chain carries whole-record
    # overrides. Converted here, once, on the way in -- so nothing downstream
    # has to know two storage shapes, and so a podcast whose frozen copy
    # matched the shared default starts following it again.
    from quill.core.podcasts.settings_resolver import migrate_legacy_overrides

    migrate_legacy_overrides(library)
    _migrate_row_order(library)
    return library


def _migrate_row_order(library: PodcastLibrary) -> None:
    """``announce_show_name_first`` becomes one value of ``row_order``.

    A boolean over a question with three answers. The old field stays in the
    record (it is schema, and removing it would drop the value on a downgrade)
    but nothing reads it after this: whoever had it switched on gets
    *podcast first*, which is exactly what it meant.
    """
    if "row_order" in library.extra_settings:
        return
    if getattr(library.settings, "announce_show_name_first", False):
        library.extra_settings["row_order"] = "podcast_first"


def save_library(data_dir: Path, library: PodcastLibrary) -> None:
    """Persist the library atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "shows": [s.to_dict() for s in library.shows],
            "folders": [f.to_dict() for f in library.folders],
            "settings": library.settings.to_dict(),
            "queue": [q.to_dict() for q in library.queue],
            "inbox_folders": [f.to_dict() for f in library.inbox_folders],
            "inbox_assignments": dict(library.inbox_assignments),
            "playlists": [p.to_dict() for p in library.playlists],
            "recently_expired": [e.to_dict() for e in library.recently_expired],
            "episode_filters": {
                show_id: config.to_dict() for show_id, config in library.episode_filters.items()
            },
            "episode_filter_reviews": dict(library.episode_filter_reviews),
            "episode_filter_exceptions": {
                show_id: list(guids) for show_id, guids in library.episode_filter_exceptions.items()
            },
            "extra_settings": dict(library.extra_settings),
            # Empty buckets are dropped rather than written: an override map
            # with nothing in it is the absence of an opinion, and storing one
            # would make "has this level said anything?" answerable two ways.
            "scope_overrides": {
                scope: dict(values) for scope, values in library.scope_overrides.items() if values
            },
            "show_labels": {
                show_id: list(names) for show_id, names in library.show_labels.items() if names
            },
            "show_check_state": {
                show_id: dict(state) for show_id, state in library.show_check_state.items() if state
            },
            "onboarding": library.onboarding.to_dict(),
            "last_auto_check": library.last_auto_check,
        },
    )
