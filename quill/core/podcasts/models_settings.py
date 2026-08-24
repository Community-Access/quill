"""Every switch QUILL Cast and Quill Radio remember about listening.

Split out of :mod:`quill.core.podcasts.models` under GATE-11 (extract, never
rebaseline): that module had become one 750-line file of which this class was
four-fifths, and "the library's data shapes" and "the library's settings" are
two subjects that grow at completely different rates -- a new setting arrives
every few days, a new *model* every few months.

The settings live on the library rather than in a per-app store because they
describe **the listening**, not the window: a per-podcast speed, an inbox limit
or a queue expiry means the same thing whichever of the two apps is on screen,
and a listener who sets one in Cast would be right to be surprised if Radio
disagreed. Per-*app* preferences (spoken transition cues, the transcript export
shape, which window opens at launch) deliberately stay in each app's own
history file instead.

Every field carries its default in the dataclass, and :meth:`from_dict` coerces
anything a stored file offers -- a settings file with a typo in it behaves like
one with nothing in it, never like a crash.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.audio.channel_mode import normalize as normalize_channel_mode
from quill.core.audio_enhance import clamp_eq_gain
from quill.core.podcasts.models_queue import coerce_int as _coerce_int

SPEED_MIN = 0.5
SPEED_MAX = 5.0


def clamp_speed(value: float) -> float:
    """Playback speed, held inside :data:`SPEED_MIN`..:data:`SPEED_MAX`."""
    return max(SPEED_MIN, min(SPEED_MAX, float(value)))


def _one_of(value: object, allowed: set[str], default: str) -> str:
    """*value* when it is one of *allowed*, else *default*.

    A settings file is somebody else's input, and the default is always the
    safe direction: never a mode that does more work than the listener chose.
    """
    wanted = str(value or "").strip().lower()
    return wanted if wanted in allowed else default


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
    #: How the Inbox decides which shows are in it. **"include"** (the default,
    #: and the behaviour Cast has always had) means only the shows you marked
    #: Route to Inbox. **"exclude"** inverts it: every show is in the Inbox
    #: except the ones you marked -- and the mark then reads as *"keep this one
    #: out"*. One flag, read two ways, rather than a second per-show field that
    #: could disagree with the first.
    #:
    #: Deliberately global, not per show: "which shows" is the question the mode
    #: answers, and a per-show mode would be a question about a question. It is
    #: also why the Inbox caps that shipped in 1.1.0 came first -- an opt-out
    #: Inbox over a 1,300-show library is a very different object, and the caps
    #: are what make it survivable.
    inbox_mode: str = "include"

    #: Chapter inference (see core/podcasts/chapter_cascade.py and
    #: inference_budget.py). Global here, per-show overridable like every other
    #: Cast setting, and **switchable off entirely in one place** -- somebody who
    #: does not want inferred chapters should never hear about them again.
    #:
    #: "when_downloaded" is the default because a downloaded episode is one the
    #: listener committed to, and the work costs them nothing they did not
    #: already accept.
    chapters_auto: str = "when_downloaded"  # "off" | "when_downloaded" | "always"
    #: How long the listener is willing to wait. Everything else about the scan
    #: derives from this one choice rather than from a page of knobs nobody can
    #: reason about -- see inference_budget.py.
    chapters_effort: str = "thorough"  # "quick" | "thorough" | "deep"
    #: Individual tiers, each of which **disables** rather than deprioritises.
    #: A listener who says "never scan the audio" has said something specific
    #: and must be obeyed.
    chapters_use_show_notes: bool = True
    chapters_use_transcript: bool = True
    chapters_scan_audio: bool = True
    #: Naming sections with a model sends **text only**, never audio, and is off
    #: until asked for.
    chapters_name_sections: bool = False
    #: Which installed speech engine transcribes, when transcription is allowed.
    #: "" = whatever dictation already uses, so there is one chooser rather than
    #: a second one that can disagree with it.
    chapters_speech_engine: str = ""
    #: Say so when a scan finishes. Politely, once, and never as an interruption.
    chapters_announce: bool = True
    #: Seconds either side of a mark that **Preview** plays -- see
    #: ``chapter_edits.preview_window`` for why it is symmetrical.
    chapters_preview_seconds: int = 10
    #: How long a listening history is kept, in days. 90 by default; ``0``
    #: keeps it forever, and ``-1`` means **do not keep one at all**, which
    #: short-circuits the write rather than pruning afterwards. A privacy
    #: commitment the app made and could not honour: the 90 days was hardcoded
    #: and there was no way to say either "forever" or "never".
    history_retention_days: int = 90
    #: Download when the connection is metered. True is today's behaviour, so
    #: nobody's downloads stop on upgrade; the guard only ever *holds* an
    #: automatic download, never a one you asked for by name.
    download_on_metered: bool = True
    #: Streaks and Year in Review. Off, matching the app it came from: a
    #: listening streak is a nudge, and a nudge nobody asked for is pressure.
    stats_streaks_enabled: bool = False
    #: iTunes, Podcast Index, or both -- "both" since the app carries its own key.
    directory_source: str = "both"
    #: How the Play Queue is grouped: none, by podcast, or by library folder.
    queue_group_mode: str = "none"
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
    #: Load the next queue item's first seconds before the current episode ends,
    #: so moving on costs an open and a seek rather than a download (see
    #: core/podcasts/prebuffer.py). **Off by default**: these are speculative
    #: bytes, and somebody on a metered connection pays for them by the megabyte.
    prebuffer_next: bool = False
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
    #: How the library's shows are ordered everywhere they are listed -- one
    #: of ``sorting.SHOW_SORT_MODES``. ``"custom"`` means the listener's own
    #: hand-arranged order: ``PodcastLibrary.shows``' list order, maintained
    #: with Move Up / Move Down.
    show_sort_mode: str = "title_az"
    #: Personal names for the pinned library views (Favorites, New Episodes,
    #: ...): view id -> the listener's own label. Only the renamed views have
    #: an entry; everything else keeps its shipped name (see
    #: ``virtual_views.view_label``). Views only -- a show's or episode's name
    #: belongs to its feed and is never renamable.
    view_names: dict[str, str] = field(default_factory=dict)
    #: How often subscribed feeds are checked on their own, in minutes; 0 =
    #: manually only. Shared by every app that reads this library, because a
    #: show subscribed in Quill Radio and a show subscribed in QUILL Cast are
    #: the same show, and two apps disagreeing about when to check it would
    #: mean two requests, two answers and one confused listener. The choices
    #: and the rules live in ``quill.core.podcasts.refresh_policy``.
    #:
    #: Manual by default. An app that starts reaching the network on a
    #: schedule nobody chose is an app spending somebody else's data.
    refresh_minutes: int = 0
    #: Also check once at launch. Separate from the interval on purpose: a
    #: listener who wants an hourly check does not necessarily want to wait on
    #: the network while the app is opening.
    refresh_on_launch: bool = False
    #: Delete a downloaded file once the episode has been *played* -- an
    #: independent switch, not a retention mode, so it composes with "keep the
    #: last N" and with the age and storage rules rather than replacing one of
    #: them. Age answers "this is old" and this answers "I am done with it",
    #: and they are different questions.
    #:
    #: Never touches an in-progress download, and never applies retroactively
    #: to episodes finished before it was switched on.
    delete_after_play: bool = False

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
            "inbox_mode": self.inbox_mode,
            "chapters_auto": self.chapters_auto,
            "chapters_effort": self.chapters_effort,
            "chapters_use_show_notes": self.chapters_use_show_notes,
            "chapters_use_transcript": self.chapters_use_transcript,
            "chapters_scan_audio": self.chapters_scan_audio,
            "chapters_name_sections": self.chapters_name_sections,
            "chapters_speech_engine": self.chapters_speech_engine,
            "chapters_announce": self.chapters_announce,
            "chapters_preview_seconds": self.chapters_preview_seconds,
            "history_retention_days": self.history_retention_days,
            "download_on_metered": self.download_on_metered,
            "stats_streaks_enabled": self.stats_streaks_enabled,
            "directory_source": self.directory_source,
            "queue_group_mode": self.queue_group_mode,
            "queue_age_limit_days": self.queue_age_limit_days,
            "inbox_max_episodes": self.inbox_max_episodes,
            "inbox_age_limit_hours": self.inbox_age_limit_hours,
            "download_retention_days": self.download_retention_days,
            "storage_cap_mb": self.storage_cap_mb,
            "playback_cache": self.playback_cache,
            "playback_cache_cap_mb": self.playback_cache_cap_mb,
            "continue_after_queue": self.continue_after_queue,
            "prebuffer_next": self.prebuffer_next,
            "continue_after_group": self.continue_after_group,
            "announce_show_name_first": self.announce_show_name_first,
            "default_launch_view": self.default_launch_view,
            "show_sort_mode": self.show_sort_mode,
            "view_names": dict(self.view_names),
            "refresh_minutes": self.refresh_minutes,
            "refresh_on_launch": self.refresh_on_launch,
            "delete_after_play": self.delete_after_play,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastSettings:
        delete_policy = str(data.get("delete_files_on_remove", "ask"))
        view_mode = str(data.get("episode_list_view_mode", "grouped"))
        sort_mode = str(data.get("episode_sort_mode", "date_newest"))
        raw_view_names = data.get("view_names")
        view_names = (
            {
                str(key): str(value).strip()
                for key, value in raw_view_names.items()
                if str(key).strip() and str(value).strip()
            }
            if isinstance(raw_view_names, dict)
            else {}
        )
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
            # A settings file is somebody else's input: an unknown mode reads
            # as the old behaviour, which can only ever show *fewer* shows in
            # the Inbox than the listener expected -- never more.
            inbox_mode=(
                str(data.get("inbox_mode", "include")).strip().lower()
                if str(data.get("inbox_mode", "include")).strip().lower() in {"include", "exclude"}
                else "include"
            ),
            # A stored value out of range reads as the default rather than
            # reaching the scan: an unknown effort must not silently turn a
            # feature up (minutes of transcription nobody asked for) or off.
            chapters_auto=_one_of(
                data.get("chapters_auto"),
                {"off", "when_downloaded", "always"},
                "when_downloaded",
            ),
            history_retention_days=_coerce_int(data.get("history_retention_days"), 90),
            download_on_metered=bool(data.get("download_on_metered", True)),
            stats_streaks_enabled=bool(data.get("stats_streaks_enabled", False)),
            directory_source=_one_of(
                data.get("directory_source"), {"itunes", "podcast_index", "both"}, "both"
            ),
            queue_group_mode=_one_of(
                data.get("queue_group_mode"), {"none", "show", "folder"}, "none"
            ),
            chapters_effort=_one_of(
                data.get("chapters_effort"), {"quick", "thorough", "deep"}, "thorough"
            ),
            chapters_use_show_notes=bool(data.get("chapters_use_show_notes", True)),
            chapters_use_transcript=bool(data.get("chapters_use_transcript", True)),
            chapters_scan_audio=bool(data.get("chapters_scan_audio", True)),
            chapters_name_sections=bool(data.get("chapters_name_sections", False)),
            chapters_speech_engine=str(data.get("chapters_speech_engine", "") or ""),
            chapters_announce=bool(data.get("chapters_announce", True)),
            # Clamped, not validated: neither value is a reason to refuse to open.
            chapters_preview_seconds=max(
                3, min(60, _coerce_int(data.get("chapters_preview_seconds"), 10))
            ),
            queue_age_limit_days=max(0, _coerce_int(data.get("queue_age_limit_days"), 0)),
            inbox_max_episodes=max(0, _coerce_int(data.get("inbox_max_episodes"), 0)),
            inbox_age_limit_hours=max(0, _coerce_int(data.get("inbox_age_limit_hours"), 0)),
            download_retention_days=max(0, _coerce_int(data.get("download_retention_days"), 0)),
            storage_cap_mb=max(0, _coerce_int(data.get("storage_cap_mb"), 0)),
            playback_cache=bool(data.get("playback_cache", True)),
            playback_cache_cap_mb=max(0, _coerce_int(data.get("playback_cache_cap_mb"), 1024)),
            continue_after_queue=bool(data.get("continue_after_queue", True)),
            prebuffer_next=bool(data.get("prebuffer_next", False)),
            continue_after_group=bool(data.get("continue_after_group", False)),
            announce_show_name_first=bool(data.get("announce_show_name_first", False)),
            default_launch_view=str(data.get("default_launch_view", "")),
            show_sort_mode=_one_of(
                data.get("show_sort_mode"),
                {"title_az", "title_za", "unheard_first", "recently_updated", "custom"},
                "title_az",
            ),
            view_names=view_names,
            refresh_minutes=_coerce_int(data.get("refresh_minutes"), 0),
            refresh_on_launch=bool(data.get("refresh_on_launch", False)),
            # A file written before the switch existed carries the old
            # retention *mode*, which meant exactly this; read it as True so
            # nobody's downloads start piling up after an upgrade.
            delete_after_play=bool(data.get("delete_after_play", False))
            or str(data.get("retention", "")) == "delete_after_play",
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
