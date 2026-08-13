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

from quill.core.audio.channel_mode import normalize as normalize_channel_mode
from quill.core.audio_enhance import clamp_eq_gain

#: Playback speed range (1.1.0). The old six-choice dropdown only offered
#: 0.75x-2.0x; the model always permitted anything, and the engines (mpv and
#: wx.media alike) hold pitch across this range. Enforced in ``from_dict`` so a
#: hand-edited or synced settings file can never leave a show unplayably fast.
SPEED_MIN = 0.5
SPEED_MAX = 5.0


def clamp_speed(value: float) -> float:
    """Playback speed, held inside :data:`SPEED_MIN`..:data:`SPEED_MAX`."""
    return max(SPEED_MIN, min(SPEED_MAX, float(value)))


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


@dataclass(slots=True)
class QueueItem:
    """One Play Queue slot: a cross-show episode reference (Phase 4 §Queue).

    Stored by ids, not object references, so the queue survives restarts and
    tolerates an episode disappearing (its slot resolves to nothing and is
    skipped at play time rather than crashing).
    """

    show_id: str
    episode_guid: str
    #: When this slot entered the queue (ISO 8601 UTC) -- the age Queue
    #: Expiration measures against ``PodcastSettings.queue_age_limit_days``.
    #: Additive: a queue written before 1.1.0 has no timestamp at all, and an
    #: empty value must read as "age unknown", which
    #: ``expiration.stamp_missing_added_at`` turns into "added just now" on
    #: first load. Reading it as "infinitely old" would silently empty
    #: everybody's queue on the first launch after updating.
    added_at: str = ""

    def to_dict(self) -> dict:
        return {
            "show_id": self.show_id,
            "episode_guid": self.episode_guid,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> QueueItem | None:
        if not isinstance(data, dict):
            return None
        show_id = str(data.get("show_id", "")).strip()
        episode_guid = str(data.get("episode_guid", "")).strip()
        if not show_id or not episode_guid:
            return None
        return cls(
            show_id=show_id,
            episode_guid=episode_guid,
            added_at=str(data.get("added_at", "")).strip(),
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
PLAYLIST_STATUS_MODES = ("any", "unplayed", "in_progress", "played")


@dataclass(slots=True)
class PlaylistRules:
    """A Smart Playlist's matching criteria (Phase 5 §Playlists). Every
    field is a filter; its "no restriction" value (an empty list, 0, or
    "any") means that field doesn't narrow the result at all -- an
    all-defaults record matches every episode of every subscribed show."""

    #: Empty = every subscribed show.
    show_ids: list[str] = field(default_factory=list)
    episode_status: str = "any"  # one of PLAYLIST_STATUS_MODES
    published_within_days: int = 0  # 0 = no limit
    min_duration_minutes: int = 0  # 0 = no limit
    max_duration_minutes: int = 0  # 0 = no limit
    sort_mode: str = "date_newest"  # one of podcasts.sorting.EPISODE_SORT_MODES

    def to_dict(self) -> dict[str, object]:
        return {
            "show_ids": list(self.show_ids),
            "episode_status": self.episode_status,
            "published_within_days": self.published_within_days,
            "min_duration_minutes": self.min_duration_minutes,
            "max_duration_minutes": self.max_duration_minutes,
            "sort_mode": self.sort_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PlaylistRules:
        raw_show_ids = data.get("show_ids")
        status = str(data.get("episode_status", "any"))
        return cls(
            show_ids=[str(s) for s in raw_show_ids] if isinstance(raw_show_ids, list) else [],
            episode_status=status if status in PLAYLIST_STATUS_MODES else "any",
            published_within_days=max(0, _coerce_int(data.get("published_within_days"), 0)),
            min_duration_minutes=max(0, _coerce_int(data.get("min_duration_minutes"), 0)),
            max_duration_minutes=max(0, _coerce_int(data.get("max_duration_minutes"), 0)),
            sort_mode=str(data.get("sort_mode", "date_newest")),
        )


@dataclass(slots=True)
class Playlist:
    """A saved, named collection of episodes (Phase 5 §Playlists) -- either
    a rule-based "Smart Playlist" (``kind="smart"``, auto-updating, resolved
    live from ``rules`` every time it's opened, the user-configurable
    counterpart to the built-in pinned views) or a manually curated
    "Playlist" (``kind="manual"``, an ordered list of specific episode
    references, the saved counterpart to the transient Play Queue)."""

    id: str
    name: str
    kind: str = "manual"  # "smart" | "manual"
    rules: PlaylistRules = field(default_factory=PlaylistRules)  # smart only
    items: list[QueueItem] = field(default_factory=list)  # manual only

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "rules": self.rules.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: object) -> Playlist | None:
        if not isinstance(data, dict):
            return None
        playlist_id = str(data.get("id", "")).strip()
        name = str(data.get("name", "")).strip()
        if not playlist_id or not name:
            return None
        kind = str(data.get("kind", "manual"))
        rules_data = data.get("rules")
        items_raw = data.get("items")
        items: list[QueueItem] = []
        for entry in items_raw if isinstance(items_raw, list) else []:
            item = QueueItem.from_dict(entry)
            if item is not None:
                items.append(item)
        rules = (
            PlaylistRules.from_dict(rules_data) if isinstance(rules_data, dict) else PlaylistRules()
        )
        return cls(
            id=playlist_id,
            name=name,
            kind=kind if kind in ("smart", "manual") else "manual",
            rules=rules,
            items=items,
        )


@dataclass(slots=True)
class PodcastSettings:
    """One global defaults record; a show's own ``PodcastShow.settings`` only
    stores the fields it overrides (``None`` = inherit the global value)."""

    playback_mode: str = "download"  # "stream" | "download"
    retention: str = "keep_all"  # "keep_all" | "keep_last_n" | "delete_after_play"
    retention_count: int = 5
    speed: float = 1.0
    download_root: str = ""  # "" = default (<data_dir>/podcasts)
    delete_files_on_remove: str = "ask"  # "ask" | "always" | "never" -- on Unsubscribe
    #: Always Sync (Phase 4): beyond the routine refresh, also download every
    #: catalog episode the live feed still exposes (download-mode shows only).
    #: In tension with keep_last_n retention -- the settings UI nudges toward
    #: keep_all when this is on.
    always_sync_full_catalog: bool = False
    #: Download-time audio processing (Phase 4): the audiobook builder's own
    #: ffmpeg passes, applied to a finished download. Off by default.
    auto_trim_silence: bool = False
    normalize_loudness: bool = False
    #: If the connection drops mid-download: retry automatically instead of
    #: landing in a hard "failed" state (mirrors RadioRecordingSettings).
    reconnect_enabled: bool = True
    reconnect_max_attempts: int = 5
    reconnect_wait_seconds: int = 10
    #: How a cross-show episode list (Inbox, New Episodes, Continue
    #: Listening, Favorites) presents multiple shows at once. "flat": one
    #: stream sorted by episode_sort_mode across every show (per-show sort
    #: overrides below do not apply -- there is no single well-defined
    #: order once different shows compare by different keys). "grouped":
    #: the same flat list, but each show's episodes cluster together
    #: (shows ordered by title), each group sorted by that show's own
    #: effective sort mode. "folders": the same per-show grouping as
    #: "grouped", presented as real expandable tree nodes, one per show,
    #: instead of a flat list -- see manager_phase4.py. Global only (does
    #: not make sense per-show: a single show has no "grouped vs flat"
    #: shape of its own).
    episode_list_view_mode: str = "grouped"  # "flat" | "grouped" | "folders"
    #: How one show's own episode list (or its slice of a "grouped"/
    #: "folders" cross-show view) is ordered -- one of
    #: podcasts.sorting.EPISODE_SORT_MODES. Global default; a show
    #: overrides it the same way it overrides speed (PodcastLibrary.
    #: apply_show_override), so "oldest-first to clear a backlog" can
    #: differ per podcast while everything else stays on the shared default.
    episode_sort_mode: str = "date_newest"
    #: Sound Enhancements (Playback menu): three adjustable EQ bands (dB,
    #: see audio_enhance.EQ_BAND_MIN_DB/MAX_DB), the compressor ("Even Out
    #: Volume"), and Smart Speed (silence trimming). All default to off,
    #: and all are per-show overridable the same way speed is -- one
    #: podcast can sound different from another without touching the
    #: shared default.
    eq_bass_db: float = 0.0
    eq_mid_db: float = 0.0
    eq_treble_db: float = 0.0
    compressor_enabled: bool = False
    smart_speed_enabled: bool = False
    #: Where the audio comes out: stereo / mono / left / right. An
    #: accessibility setting before a sound one -- mono keeps hard-panned
    #: content audible to someone listening with one ear, and the single-ear
    #: modes leave the other ear free for a screen reader. Shared vocabulary
    #: with Quill Radio (quill.core.audio.channel_mode).
    channel_mode: str = "stereo"
    #: Skip Forward/Back (Episode menu): how far each command jumps.
    #: Per-show overridable the same way speed is.
    skip_forward_seconds: int = 30
    skip_back_seconds: int = 15
    #: Auto-skip (per-show only -- a global default would be a strange
    #: "skip N seconds of every podcast" behavior nobody wants): 0 = off.
    #: auto_skip_intro_seconds jumps forward once when an episode starts
    #: fresh (never on resume, so a checkpointed position is never lost
    #: under it). auto_skip_outro_seconds ends playback that many seconds
    #: before the episode's own end, checked by a position poll -- treated
    #: exactly like the episode finishing naturally (auto-advance,
    #: delete-after-play, etc. all still fire).
    auto_skip_intro_seconds: int = 0
    auto_skip_outro_seconds: int = 0
    #: Auto-download (1.1.0) -- an *acquisition* policy, the counterpart to
    #: the retention policy above. How many of the newest episodes to fetch
    #: without being asked, on subscribe and on every refresh: 0 = off
    #: (download by hand, the behavior through 1.0.x), -1 = every episode the
    #: feed still offers (what ``always_sync_full_catalog`` has always meant,
    #: which is why turning that on now also reads as -1 here). Per-show
    #: overridable, so a daily news show can fetch 1 while a weekly show
    #: fetches 5.
    auto_download_count: int = 0
    #: Also auto-download an episode the moment it is added to the Play Queue
    #: / routed to the Inbox, regardless of how new it is. Queue on by
    #: default (something you queued is something you mean to play); Inbox
    #: off, since the Inbox is a triage surface, not a commitment.
    auto_download_queued: bool = True
    auto_download_inbox: bool = False
    #: Queue Expiration (1.1.0): a queued episode older than this many days
    #: leaves the Play Queue for Recently Expired. 0 = off, and off is the
    #: only sensible *global* value -- the useful number differs per show
    #: (2 days for a daily news show, 2 weeks for weekly long-form), so this
    #: is set per podcast and the shared default stays off.
    queue_age_limit_days: int = 0
    #: Inbox caps (1.1.0): trim the Inbox to at most this many episodes, and
    #: drop episodes that have sat there longer than this many hours. 0 = no
    #: limit for either. Trimming never deletes anything: a trimmed episode
    #: simply leaves the Inbox and stays unplayed in its show's own list, and
    #: anything played, in progress, or queued is never trimmed at all.
    inbox_max_episodes: int = 0
    inbox_age_limit_hours: int = 0
    #: Storage management (1.1.0). ``download_retention_days``: delete a
    #: downloaded file older than N days (0 = off). ``storage_cap_mb``: a
    #: ceiling on total podcast download storage (0 = no cap); when it is
    #: exceeded, the oldest played downloads are evicted first and a queued or
    #: in-progress episode is never evicted.
    download_retention_days: int = 0
    storage_cap_mb: int = 0
    #: Streamed episodes are fully capable episodes: while one plays its bytes
    #: are also written to a bounded, self-evicting cache (playback_cache.py),
    #: which is what lets a dropped connection keep playing, "Keep This
    #: Episode" be a move not a second download, and chapter inference run on a
    #: streamed episode at all. Per-show overridable;
    #: ``playback_cache_cap_mb`` is the global cache ceiling (0 = no cap).
    playback_cache: bool = True
    playback_cache_cap_mb: int = 1024
    #: Playback session (1.1.0). ``continue_after_queue``: when an episode
    #: finishes, start the Play Queue's next item -- on, because that is what
    #: auto-advance has always done. ``continue_after_group``: when the queue
    #: is empty, keep going with the same show's next unplayed episode -- off,
    #: because it is new behavior and nobody asked for their evening to
    #: continue on its own. With both off, playback stops at the end of the
    #: current episode, which is the whole point of having the pair.
    continue_after_queue: bool = True
    continue_after_group: bool = False
    #: How a cross-show row reads (1.1.0). Off: "Episode title -- Podcast".
    #: On: "Podcast -- Episode title". An accessibility preference, not a
    #: cosmetic one: in a list of two hundred rows from forty shows, whichever
    #: comes first is what you can skim by first letter, and which one that
    #: should be depends entirely on how you look for things.
    announce_show_name_first: bool = False
    #: Which node the library tree lands on at launch (1.1.0): a virtual view
    #: id ("new_episodes", "continue_listening", "inbox", "favorites",
    #: "recently_expired") or "" for the top of the tree.
    default_launch_view: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "playback_mode": self.playback_mode,
            "retention": self.retention,
            "retention_count": self.retention_count,
            "speed": self.speed,
            "download_root": self.download_root,
            "delete_files_on_remove": self.delete_files_on_remove,
            "always_sync_full_catalog": self.always_sync_full_catalog,
            "auto_trim_silence": self.auto_trim_silence,
            "normalize_loudness": self.normalize_loudness,
            "reconnect_enabled": self.reconnect_enabled,
            "reconnect_max_attempts": self.reconnect_max_attempts,
            "reconnect_wait_seconds": self.reconnect_wait_seconds,
            "episode_list_view_mode": self.episode_list_view_mode,
            "episode_sort_mode": self.episode_sort_mode,
            "eq_bass_db": self.eq_bass_db,
            "eq_mid_db": self.eq_mid_db,
            "eq_treble_db": self.eq_treble_db,
            "compressor_enabled": self.compressor_enabled,
            "smart_speed_enabled": self.smart_speed_enabled,
            "channel_mode": self.channel_mode,
            "skip_forward_seconds": self.skip_forward_seconds,
            "skip_back_seconds": self.skip_back_seconds,
            "auto_skip_intro_seconds": self.auto_skip_intro_seconds,
            "auto_skip_outro_seconds": self.auto_skip_outro_seconds,
            "auto_download_count": self.auto_download_count,
            "auto_download_queued": self.auto_download_queued,
            "auto_download_inbox": self.auto_download_inbox,
            "queue_age_limit_days": self.queue_age_limit_days,
            "inbox_max_episodes": self.inbox_max_episodes,
            "inbox_age_limit_hours": self.inbox_age_limit_hours,
            "download_retention_days": self.download_retention_days,
            "storage_cap_mb": self.storage_cap_mb,
            "playback_cache": self.playback_cache,
            "playback_cache_cap_mb": self.playback_cache_cap_mb,
            "continue_after_queue": self.continue_after_queue,
            "continue_after_group": self.continue_after_group,
            "announce_show_name_first": self.announce_show_name_first,
            "default_launch_view": self.default_launch_view,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastSettings:
        delete_policy = str(data.get("delete_files_on_remove", "ask"))
        view_mode = str(data.get("episode_list_view_mode", "grouped"))
        sort_mode = str(data.get("episode_sort_mode", "date_newest"))
        return cls(
            playback_mode=str(data.get("playback_mode", "download")),
            retention=str(data.get("retention", "keep_all")),
            retention_count=_coerce_int(data.get("retention_count"), 5),
            speed=clamp_speed(_coerce_float(data.get("speed"), 1.0)),
            download_root=str(data.get("download_root", "")),
            delete_files_on_remove=delete_policy
            if delete_policy in ("ask", "always", "never")
            else "ask",
            always_sync_full_catalog=bool(data.get("always_sync_full_catalog", False)),
            auto_trim_silence=bool(data.get("auto_trim_silence", False)),
            normalize_loudness=bool(data.get("normalize_loudness", False)),
            reconnect_enabled=bool(data.get("reconnect_enabled", True)),
            reconnect_max_attempts=max(0, _coerce_int(data.get("reconnect_max_attempts"), 5)),
            reconnect_wait_seconds=max(1, _coerce_int(data.get("reconnect_wait_seconds"), 10)),
            episode_list_view_mode=view_mode
            if view_mode in ("flat", "grouped", "folders")
            else "grouped",
            episode_sort_mode=sort_mode,
            eq_bass_db=clamp_eq_gain(_coerce_float(data.get("eq_bass_db"), 0.0)),
            eq_mid_db=clamp_eq_gain(_coerce_float(data.get("eq_mid_db"), 0.0)),
            eq_treble_db=clamp_eq_gain(_coerce_float(data.get("eq_treble_db"), 0.0)),
            compressor_enabled=bool(data.get("compressor_enabled", False)),
            smart_speed_enabled=bool(data.get("smart_speed_enabled", False)),
            channel_mode=normalize_channel_mode(str(data.get("channel_mode", "stereo"))),
            skip_forward_seconds=max(1, _coerce_int(data.get("skip_forward_seconds"), 30)),
            skip_back_seconds=max(1, _coerce_int(data.get("skip_back_seconds"), 15)),
            auto_skip_intro_seconds=max(0, _coerce_int(data.get("auto_skip_intro_seconds"), 0)),
            auto_skip_outro_seconds=max(0, _coerce_int(data.get("auto_skip_outro_seconds"), 0)),
            auto_download_count=max(-1, _coerce_int(data.get("auto_download_count"), 0)),
            auto_download_queued=bool(data.get("auto_download_queued", True)),
            auto_download_inbox=bool(data.get("auto_download_inbox", False)),
            queue_age_limit_days=max(0, _coerce_int(data.get("queue_age_limit_days"), 0)),
            inbox_max_episodes=max(0, _coerce_int(data.get("inbox_max_episodes"), 0)),
            inbox_age_limit_hours=max(0, _coerce_int(data.get("inbox_age_limit_hours"), 0)),
            download_retention_days=max(0, _coerce_int(data.get("download_retention_days"), 0)),
            storage_cap_mb=max(0, _coerce_int(data.get("storage_cap_mb"), 0)),
            playback_cache=bool(data.get("playback_cache", True)),
            playback_cache_cap_mb=max(0, _coerce_int(data.get("playback_cache_cap_mb"), 1024)),
            continue_after_queue=bool(data.get("continue_after_queue", True)),
            continue_after_group=bool(data.get("continue_after_group", False)),
            announce_show_name_first=bool(data.get("announce_show_name_first", False)),
            default_launch_view=str(data.get("default_launch_view", "")),
        )

    @property
    def effective_auto_download_count(self) -> int:
        """How many newest episodes auto-download, folding in Always Sync.

        ``always_sync_full_catalog`` predates the auto-download policy and
        means exactly what ``auto_download_count == -1`` means, so the old
        checkbox keeps working and the two never disagree.
        """
        if self.always_sync_full_catalog:
            return -1
        return self.auto_download_count


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
            "is_local": self.is_local,
            "watched_folder": self.watched_folder,
            "folder_id": self.folder_id,
            "paused": self.paused,
            "is_favorite": self.is_favorite,
            "route_to_inbox": self.route_to_inbox,
            "inbox_default_folder_id": self.inbox_default_folder_id,
            "auto_queue": self.auto_queue,
            "notify_new_episodes": self.notify_new_episodes,
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
            is_local=bool(data.get("is_local", False)),
            watched_folder=str(data.get("watched_folder", "")),
            folder_id=str(folder_id) if isinstance(folder_id, str) and folder_id else None,
            paused=bool(data.get("paused", False)),
            is_favorite=bool(data.get("is_favorite", False)),
            route_to_inbox=bool(data.get("route_to_inbox", False)),
            auto_queue=bool(data.get("auto_queue", False)),
            notify_new_episodes=bool(data.get("notify_new_episodes", False)),
            inbox_default_folder_id=(
                str(inbox_folder_id)
                if isinstance(inbox_folder_id, str) and inbox_folder_id
                else None
            ),
            settings=settings,
            episodes=episodes,
        )


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value)) if value.strip() else default
        except ValueError:
            return default
    return default


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value) if value.strip() else default
        except ValueError:
            return default
    return default
