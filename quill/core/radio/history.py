"""Recently played internet-radio stations, persisted as atomic JSON.

Backs the Station menu's Recently Played submenu, the Play Last Station
command, and the standalone app's optional resume-on-launch behavior.
Most recent first, capped, de-duplicated by the same key favorites use.
wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.radio.models import RadioStation
from quill.core.radio.onboarding import RadioOnboardingState
from quill.core.radio.search_history import SearchQuery
from quill.core.radio.search_sources import DEFAULT_ENABLED as DEFAULT_SEARCH_SOURCES

_FILE_NAME = "radio_history.json"
_MAX_ENTRIES = 15


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
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


@dataclass(slots=True)
class RadioHistory:
    """Recently played stations plus the resume-on-launch preference."""

    stations: list[RadioStation] = field(default_factory=list)
    resume_on_launch: bool = False
    #: Whether the listener has accepted the one-time YouTube consent + rights
    #: notice (#1268). Playing or recording a YouTube link installs yt-dlp on
    #: demand and reaches YouTube, so the notice is shown once -- when a YouTube
    #: link is first added as a station -- and remembered here. Without it, a
    #: scheduled recording that fires while nobody is watching would be the
    #: first time QUILL ever touched YouTube, which is exactly the surprise the
    #: consent exists to prevent.
    youtube_consented: bool = False
    #: What the listener has already been shown of the first-run flow and the
    #: one-shot tips. A nested record rather than three flat fields, because it
    #: is one feature and reading it as one is how the caller uses it.
    onboarding: RadioOnboardingState = field(default_factory=RadioOnboardingState)
    #: Which media-tool shortfall has already been mentioned at launch --
    #: ``"ffmpeg=1,mpv=0"`` and friends, from ``MediaHealth.signature()``.
    #: A signature rather than a "seen" flag so that a machine which later
    #: loses a *second* tool is told again, while a machine told once about
    #: the same state is not told on every launch until the end of time.
    #: Cleared when everything is healthy again, so a later loss is news.
    media_notice_signature: str = ""
    #: Speak "Now playing: ..." when the stream's track title changes.
    #: Off by default -- in QUILL it would interrupt writing; turning it on
    #: is one check item on the radio menus.
    announce_track_titles: bool = False
    #: Show the read-only Station Details pane in Browse/Search Stations. On by
    #: default; View > Show Station Details toggles it, honored by every surface.
    show_station_details: bool = True
    #: Ask before the Delete key removes a browse row. Off means the listener
    #: ticked "Don't ask me again" in that question -- a preference they set
    #: from inside the thing it governs, which is the only place anybody would
    #: look for it.
    confirm_browse_delete: bool = True
    #: Explain, in a dialog, when Delete lands on a row that has nothing to
    #: remove. Same checkbox, same reasoning: useful once, noise forever.
    explain_browse_delete: bool = True
    #: Winamp classic-skin playback keys in the Recordings player (#1344):
    #: Z X C V B along the bottom row, arrows to seek, T for elapsed/remaining,
    #: J to jump. On by default -- every key it claims was otherwise unused in
    #: that dialog -- and one checkbox in Preferences turns them off for anyone
    #: who wants the letters back for list typeahead.
    winamp_playback_keys: bool = True
    #: The recordings play queue (item 12), remembered between sessions
    #: because both are standing preferences rather than per-session choices.
    #: Stop-after-current is deliberately NOT here: it is a one-shot the
    #: listener asks for in the moment, and one that survived a restart would
    #: stop playback for a reason nobody could remember asking for.
    recordings_shuffle: bool = False
    recordings_repeat: str = "off"
    #: Which directories Find Stations searches. A source that is off is never
    #: contacted, so this is a speed/privacy control as well as a tidiness one.
    #: See quill.core.radio.search_sources for the registry.
    search_sources_enabled: tuple[str, ...] = DEFAULT_SEARCH_SOURCES
    #: The last Source-facet choice in Find Stations, re-applied on open -- a
    #: filter you must re-pick every search is not a filter.
    search_source_facet: str = ""
    #: The searches already run, newest first, so running one again is not
    #: retyping it. Whole queries rather than bare words: *jazz in France* and
    #: *jazz in Brazil* are different searches, and a list that kept only "jazz"
    #: would hand back the wrong one. See quill.core.radio.search_history --
    #: it rides this file deliberately, so clearing the recently-played history
    #: clears this too rather than leaving a second history nobody knew about.
    recent_searches: tuple[SearchQuery, ...] = ()
    #: Which branches Browse Stations shows. ``None`` means "never set", which
    #: matters: it lets a branch added in a later release appear for people who
    #: never touched the setting, instead of being frozen out by a stored list
    #: that predates it. A branch that is off is not in the tree at all and is
    #: never contacted -- see quill.core.radio.browse_visibility.
    browse_sources_enabled: tuple[str, ...] | None = None
    #: Which generation of the browse-source list this choice was made against.
    #: A branch added later cannot be named in a list saved earlier, so the
    #: loader shows the newcomers once and stamps this forward. 0 = a profile
    #: that predates the stamp entirely.
    browse_sources_epoch: int = 0
    #: Show the arrow-navigable status bar along the bottom of the main window.
    #: On by default; View > Show Status Bar toggles it. F6 moves focus into it.
    show_status_bar: bool = True
    #: Font scale for the main window (favorites tree, buttons, now-playing line,
    #: status bar). 1.0 = normal; View > Text Size offers Large (1.25) and
    #: Larger (1.5) for low-vision users. Clamped to a sane range on load.
    ui_font_scale: float = 1.0
    #: Keep the computer awake while a station is playing or a recording is
    #: running, so audio does not stop when the system would otherwise sleep.
    #: On by default (Windows only); a Preferences checkbox turns it off.
    prevent_sleep: bool = True
    #: Hold standby off as a scheduled recording approaches, not only while one
    #: is running. A scheduled recording cannot fire on a sleeping machine, and
    #: nothing used to keep it awake while merely *waiting* -- so a computer
    #: that dozed at 10:58 started an 11:00 recording whenever it next woke.
    #: See quill/core/radio/schedule_wake.py.
    keep_awake_before_recording: bool = True
    #: Ask Windows to *wake* the computer for a scheduled recording (a per-user
    #: Task Scheduler entry with WakeToRun). Separate from the setting above on
    #: purpose: inhibiting standby is local and needs no permissions, while
    #: registering a wake changes the machine, and somebody may reasonably want
    #: one and not the other.
    wake_for_scheduled_recording: bool = True
    #: The local station catalog: browse answers from this computer, refreshed
    #: from live data. Off restores 3.0.0 behavior exactly -- live browsing,
    #: session caches, no catalog reads, no refresh of any layer.
    catalog_enabled: bool = True
    #: Check for station updates shortly after launch (skipped when the
    #: catalog is younger than a floor, so a restart loop never hammers
    #: anyone's directory).
    catalog_refresh_on_startup: bool = True
    #: Background refresh cadence in hours. 0 turns the timer off entirely.
    #: Default 24 (Jeff, 2026-08-15).
    catalog_refresh_hours: int = 24
    #: Silently check GitHub releases for a newer Quill Radio on launch (the
    #: same check Help > Check for Updates runs, just quiet unless a genuine
    #: update is found); on by default, one checkbox in Preferences (Ctrl+,)
    #: turns it off.
    check_updates_on_startup: bool = True
    #: ISO timestamp of the last update check (manual or automatic), so the
    #: startup check only hits the network once a day, not on every launch.
    last_update_check: str = ""
    #: Sound Enhancements (Playback menu): three adjustable EQ bands (dB,
    #: see audio_enhance.EQ_BAND_MIN_DB/MAX_DB) and whether the compressor
    #: is on. All default to off -- normal playback never touches the
    #: ffmpeg relay unless the user opts in.
    eq_bass_db: float = 0.0
    eq_mid_db: float = 0.0
    eq_treble_db: float = 0.0
    compressor_enabled: bool = False
    #: What closing the window (titlebar X, Alt+F4, Station > Exit) does:
    #: "ask" shows a one-time-per-session-until-answered Exit/Minimize to
    #: Tray dialog (its "Don't ask me again" checkbox writes this field);
    #: "exit"/"minimize" skip straight to that action. Preferences (Ctrl+,)
    #: can always set it back to "ask".
    close_action: str = "ask"
    #: Speak "Entered/Exited X dialog" around every modal dialog. Off by
    #: default, matching QUILL's own Settings.announce_dialog_transitions --
    #: the standalone apps previously never wired this policy at all, so
    #: dialog_contract.show_modal_dialog's "no policy set" fallback always
    #: spoke it, unlike full QUILL where it is opt-in.
    announce_dialog_transitions: bool = False
    #: How much scaffolding an exported transcript keeps: speakers, timestamps,
    #: both, or just the words. Per install, and named the same in both apps
    #: (the same shape announce_dialog_transitions has) so a transcript saved
    #: from Quill Radio and one saved from QUILL Cast come out alike.
    #: See quill.core.podcasts.transcript_export.
    transcript_detail: str = "speakers"
    #: How "What's Playing" (Ctrl+T) reads a track, as a token template over
    #: quill.core.radio.now_playing (#1068). The default cleans up the raw
    #: broadcast metadata some stations send ("YOUR SONG by Elton John"
    #: instead of a wall of key="value" noise); a listener can retune it with
    #: {title}/{artist}/{raw} tokens and [optional] segments in Preferences.
    now_playing_template: str = "{title}[ by {artist}]"
    #: When a station's stream fails, scan the station's own website for a
    #: working one (quill.core.radio.recovery Strategy C, #1065). The always-on
    #: strategies -- re-resolving a moved StreamTheWorld mount and refreshing
    #: from the directory -- run regardless; this gates only the extra
    #: website-scan step (a network fetch of the station's homepage on failure),
    #: so it is a single opt-out in Preferences. On by default; off in Safe Mode.
    recover_from_website: bool = True
    #: The mpv audio-device name radio playback routes to (#1076), e.g.
    #: "wasapi/{guid}". "" = system default. Set from the Preferences
    #: "Radio output device" dropdown; needs the mpv engine (ignored, with
    #: a spoken fallback, when libmpv is not installed).
    output_device: str = ""
    #: Which playback engine radio uses: "auto" (mpv when installed --
    #: device routing, pause/rewind live, volume boost, wider codec/HLS
    #: support -- else wx.media), "wx" (classic Windows Media, the escape
    #: hatch), or "mpv" (insist; falls back with an announcement if absent).
    playback_engine: str = "auto"
    #: How often Quill Radio checks its subscribed feeds on its own, in
    #: minutes; 0 (the shipped answer) is "only when you ask". Radio's own
    #: rather than the shared podcast settings, and deliberately: Radio and
    #: QUILL Cast read one library, so a single shared switch would mean
    #: turning the check on in one app turned it on in the other, with no way
    #: to say "let Cast do it". Each app decides whether *it* is the one that
    #: checks. The duplicate-work that could follow is handled where it
    #: belongs -- the shared ``PodcastLibrary.last_auto_check`` stamp, see
    #: refresh_policy.is_due.
    podcast_refresh_minutes: int = 0
    #: Run one check at launch as well. Off by default: a launch that spends
    #: four seconds on feeds is a launch a screen-reader user spends waiting.
    podcast_refresh_on_launch: bool = False
    #: The lead time a new reminder starts on (list.md 7.8). Chosen per
    #: reminder either way; this only decides what the control opens at, so
    #: the common case is one keystroke shorter. 15 minutes because that is
    #: the shortest warning that is still a warning -- long enough to finish
    #: what you are doing, short enough that you have not forgotten by then.
    reminder_default_lead_seconds: int = 900
    #: Play the reminder earcon (7.4). On by default, and separate from the
    #: global per-event sound list on purpose: somebody who has turned most
    #: earcons off has probably not meant to turn off the one sound they
    #: asked to be interrupted by.
    reminder_sound: bool = True
    #: Skip Silence for bounded playback (11.7): long pauses in a recording,
    #: a YouTube row or a podcast episode are shortened as it plays. The
    #: engine has always been able to do this (audio_enhance's Smart Speed
    #: clause); Quill Radio simply never passed the flag. No effect on live
    #: radio, which plays at broadcast speed.
    skip_silence: bool = False
    #: Playback speed remembered per *kind* of bounded row (11.7). A podcast
    #: is remembered per show (radio_listens) because shows have voices you
    #: have an opinion about; a recording is not -- "1.5x for recordings"
    #: means every recording. 1.0 = normal, and nothing is applied.
    recording_speed: float = 1.0
    youtube_speed: float = 1.0
    #: Volume Boost (mpv engine): amplify up to 50% past 100 for quiet
    #: streams. No effect on the wx.media engine, which caps at 100.
    volume_boost: bool = False
    #: Last volume level (0-100) the listener set, remembered across sessions so
    #: stations don't all come back at full blast on the next launch (#1263).
    #: -1 means "never set" -- the controller keeps its own default.
    volume_percent: int = -1
    #: Sound options (listener-level, so global rather than per-station):
    #: channel mode -- "stereo" (default), "mono" (both channels blended into
    #: one, for single-sided hearing or a single earbud where hard-panned
    #: content otherwise disappears), or "left"/"right" (send just that source
    #: channel to both ears, so the radio can play in one ear while a screen
    #: reader uses the other). Replaces the earlier ``mono_enabled`` bool.
    channel_mode: str = "stereo"
    #: Night mode -- real-time loudness normalization (lifts quiet program
    #: material), the complement to the compressor's "tame the loud parts".
    night_mode_enabled: bool = False
    #: OptiLab broadcast-polish (listener-level, global like night mode; adapted
    #: from OptiLab Core by dgl1984, Apache-2.0). ``optilab_enabled`` is the
    #: bypass so the chosen mode is remembered while turned off; ``optilab_mode``
    #: is "off"/"podcast"/"stream"/"limiter"; ``optilab_input_db`` is the input
    #: trim (0 by default) and ``optilab_auto_adapt`` the 0-100% adapt amount.
    optilab_enabled: bool = False
    optilab_mode: str = "off"
    optilab_input_db: float = 0.0
    optilab_auto_adapt: int = 0
    #: "Use exact OptiLab processing when saving" -- recordings and converted
    #: files go through the real OptiLab Core engine instead of the ffmpeg
    #: adaptation of it. Off by default, and deliberately scoped to *saved
    #: files*: live listening cannot run it (nothing on that path ever holds a
    #: PCM sample) and a setting that silently applied to only some of what it
    #: named would be the exact failure rule A-9 forbids.
    optilab_exact: bool = False
    #: The same, extended to *listening*: the stream is relayed through the real
    #: engine as it plays. Separate from ``optilab_exact`` because it costs
    #: something the saved-file case does not -- a slower start and a reconnect
    #: on every change -- so it must be chosen, never inherited.
    optilab_exact_live: bool = False
    #: Favorites sort order for the tree/menus: "az" (A-Z, the default so a
    #: fresh list is alphabetized), "za" (Z-A), or "manual" (the hand-arranged
    #: Move Up/Down order). Applies to folders and to stations; a folder may
    #: override it for its own contents via ``folder_sort_orders``. This is a
    #: display-only order -- the stored manual order is never destroyed, so
    #: switching back to "manual" restores it.
    favorites_sort: str = "az"
    #: Per-folder sort overrides (folder path -> "az"|"za"|"manual"). A folder
    #: absent here follows ``favorites_sort``.
    folder_sort_orders: dict[str, str] = field(default_factory=dict)
    #: Alt+F4 sends the app to the system tray (still playing) instead of
    #: closing the window. Off by default -- Alt+F4 keeps its Windows-wide
    #: meaning unless the listener opts in. Separate from close_action,
    #: which governs the titlebar X and Exit: with this on, the reflexive
    #: keyboard close tucks the radio away while the deliberate exits still
    #: exit (or ask, per close_action).
    alt_f4_to_tray: bool = False
    #: Open Browse Stations over the main window at launch. Off by default,
    #: and deliberately not a general "which window opens" picker: a setting
    #: that changes where you land is expensive for somebody driving by
    #: keyboard, and one predictable place every launch beats a choice made
    #: months ago and half-remembered. Browse is already Ctrl+B away, so this
    #: is a convenience rather than a fix.
    open_browse_at_startup: bool = False
    #: Which single window opens at launch ("" = none). Replaces the
    #: open_browse_at_startup checkbox, which could only ever answer for one of
    #: the six windows there now; the flag is still read once, to migrate.
    startup_window: str = ""
    #: Verbose radio logging (quill-radio #5). When on, the radio logger
    #: subtrees drop to DEBUG (via radio_logging.set_radio_debug) and recording
    #: runs ffmpeg at -loglevel verbose, so a hard-to-reproduce playback or
    #: recording problem leaves a full trail in quill.log. Off by default (it is
    #: chatty); one checkbox in Preferences (Ctrl+,) turns it on. Applied when
    #: history loads and whenever the checkbox changes.
    debug_mode: bool = False
    #: ISO timestamp of when the app was last running (written on close), so a
    #: startup "missed recording" report can name scheduled recordings whose
    #: time passed while it was closed (quill-radio #4). Empty = never recorded
    #: (a first run reports nothing).
    last_seen: str = ""
    #: Where the standalone writes ``quill.log`` (quill-radio #5). "" = the
    #: default ``<data_dir>/logs``. Set from the Preferences "Log folder" field;
    #: applied at startup and relocated live when changed.
    log_dir: str = ""
    #: One volume for every station. Off by default, which is the historical
    #: behaviour: a favorite's own remembered level wins outright, so with twenty
    #: favorites each carrying a level there was no way to turn them all down --
    #: you had to play each station and adjust it.
    #:
    #: On, ``volume_percent`` becomes the single level every station plays at,
    #: and Volume Up/Down set *it*, so turning the volume down turns everything
    #: down. Per-station levels are deliberately kept, not erased: turning this
    #: back off restores every station's own level exactly as it was.
    use_global_volume: bool = False
    #: Keep a per-station log of the songs each station plays, recorded from the
    #: track-title poll that already runs (see quill.core.radio.song_history).
    #: On by default -- it is what makes "what was that song earlier?"
    #: answerable -- but a record of everything you have listened to deserves an
    #: off switch, and turning it off stops new entries immediately. Existing
    #: entries stay until cleared from the Song History window.
    song_history_enabled: bool = True
    #: Whether to resume an in-progress recording found at launch (R3).
    #: ``"ask"`` shows the Resume/Skip/Always-resume dialog; ``"always"``
    #: auto-resumes without prompting; ``"never"`` silently skips. Persisted so
    #: the user's "Always resume" / "Never resume" choice sticks across launches.
    recording_resume_choice: str = "ask"
    #: How many of a subscribed show's newest episodes the Subscriptions branch
    #: lists per show (Browse Stations > Podcasts > Subscriptions). 0 = every
    #: episode the feed carries. Deliberately Radio's one podcast knob: the
    #: rich per-show retention/inbox machinery lives in Quill Cast, and Radio
    #: stays a player.
    subscription_episode_limit: int = 25

    def record(self, station: RadioStation) -> None:
        """Note that *station* just played; it moves to the front."""
        key = station.station_uuid or station.stream_url
        self.stations = [s for s in self.stations if (s.station_uuid or s.stream_url) != key]
        self.stations.insert(0, station)
        del self.stations[_MAX_ENTRIES:]

    @property
    def last_station(self) -> RadioStation | None:
        return self.stations[0] if self.stations else None


# Reading and writing the file lives in history_store, split out under
# GATE-11, and is re-exported here so every caller keeps the one import it
# already had. At the bottom because history_store imports this record: the
# record is the shape, the store is what happens to it.
from quill.core.radio.history_store import _store_path as _store_path  # noqa: E402
from quill.core.radio.history_store import load_history as load_history  # noqa: E402
from quill.core.radio.history_store import save_history as save_history  # noqa: E402
