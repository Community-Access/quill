"""Every feature QUILL Cast has, each with a switch (qc.md section 17).

Jeff: "all features should be configurable to turn them on or off."

Customize Features used to list eight areas. This is the complete inventory:
every capability, grouped, each a checkbox, each on by default -- only an
explicit *off* is stored (the rule :mod:`quill.core.app_features` follows), so
an area added later is on for everybody until they say otherwise. A
switched-off area is **absent**: its place is not in the Places list, its rows
are not in the menus, its cell is not in the status bar, its keys do nothing
(a key is a menu accelerator, and an absent row has none), and its window is
not in Go To. The palette still lists its command with "(off in Customize
Features)" so a listener who remembers the name learns where it went.

Two things make the list exhaustive rather than aspirational. Every command
id Cast registers or binds maps to exactly one area through
:func:`area_for_command`, and ``tests/unit/core/podcasts/test_cast_features.py``
walks the Cast modules for every id and fails on one this file does not
place -- so a new command cannot arrive without a switch. And the profiles
are written as what they take *away*, so a profile never hides a feature it
was written before.

The eight original ids (``downloads``, ``inbox``, ``queue``, ``transcripts``,
``statistics``, ``personal_audio``, ``sleep_timer``, ``backups``) are kept, so
nobody's saved choices change meaning.
"""

from __future__ import annotations

from quill.core.app_features import AppArea, AppProfile

__all__ = [
    "AREAS",
    "COMMAND_AREAS",
    "GROUPS",
    "PROFILES",
    "area_for_command",
    "area_ids",
    "areas_in_group",
    "group_of",
]

#: (group id, group label), in the order Customize Features shows them.
GROUPS: tuple[tuple[str, str], ...] = (
    ("places", "Places"),
    ("playing", "Playing"),
    ("library", "Library"),
    ("getting", "Getting podcasts"),
    ("keeping", "Keeping things"),
    ("telling", "Telling you"),
    ("data", "Listening data"),
    ("around", "Around the app"),
)


def _area(group: str, area_id: str, label: str, why: str) -> tuple[str, AppArea]:
    return group, AppArea(area_id, label, why)


_GROUPED: tuple[tuple[str, AppArea], ...] = (
    # -- Places ---------------------------------------------------------------
    _area(
        "places",
        "inbox",
        "Inbox",
        "The Inbox place, its folders and its caps: new episodes waiting to be "
        "triaged. Off, new episodes simply appear in their podcasts.",
    ),
    _area(
        "places",
        "queue",
        "Play Queue",
        "The Play Queue place and the queue run: a listening order built ahead of time.",
    ),
    _area(
        "places",
        "downloads",
        "Downloads",
        "The Downloads place and menu: keeping episodes on this computer rather "
        "than streaming them.",
    ),
    _area(
        "places",
        "personal_audio",
        "Personal Audio",
        "Your own recordings and audiobooks as a place: Add Personal Audio and watched folders.",
    ),
    _area(
        "places",
        "playlists",
        "Playlists",
        "Smart and hand-made playlists, as a place between Favorites and "
        "Personal Audio when any exist.",
    ),
    _area(
        "places",
        "notifications",
        "Notifications",
        "The Notifications place, its status-bar count and its window: what Cast "
        "told you while you were elsewhere.",
    ),
    # -- Playing --------------------------------------------------------------
    _area(
        "playing",
        "now_playing",
        "Now Playing window",
        "The console for the playing episode: the slider, chapters, your note, the "
        "show notes. Off, the status bar and the Episode menu still play everything.",
    ),
    _area(
        "playing",
        "transcripts",
        "Transcripts and chapters",
        "Reading along, jumping by chapter, and the chapter inference that "
        "produces chapters for podcasts whose publishers did not.",
    ),
    _area(
        "playing",
        "notes",
        "Show notes and your notes",
        "The show-notes pane under the library, the Show Notes window, Links in "
        "These Notes, and the note you write on an episode.",
    ),
    _area(
        "playing",
        "sleep_timer",
        "Sleep timer",
        "Stopping after a set time or at the end of the episode.",
    ),
    _area(
        "playing",
        "speed",
        "Speed controls",
        "Speed Up, Speed Down, Reset Speed and the speed readout. Off, every "
        "episode plays at normal speed.",
    ),
    _area(
        "playing",
        "sound",
        "Sound Enhancements",
        "The equaliser, loudness, mono and boost, and the audio output device.",
    ),
    _area(
        "playing",
        "skipping",
        "Skipping",
        "Skip forward and back, intro and outro skipping, and Skip Silence.",
    ),
    _area(
        "playing",
        "winamp_keys",
        "Winamp playback keys",
        "The letter keys for the transport in the lists. Off, the letters go back "
        "to list typeahead.",
    ),
    _area(
        "playing",
        "global_hotkeys",
        "Global hotkeys",
        "Play, Pause and Stop from any program, and the hotkey that raises Now Playing.",
    ),
    # -- Library ---------------------------------------------------------------
    _area(
        "library",
        "folders",
        "Folders and custom order",
        "Folders in the Podcasts tree, and moving podcasts and folders into your own order.",
    ),
    _area(
        "library",
        "find",
        "Find",
        "The Find box above the places: typing flattens the library into matches.",
    ),
    _area(
        "library",
        "feed_check",
        "Feed Check",
        "The report of which feeds need something, with Retry and schedules.",
    ),
    _area(
        "library",
        "filters",
        "Episode filters and smart playlists",
        "Rules that keep episodes out, and rules that gather them into a playlist.",
    ),
    _area(
        "library",
        "customizing",
        "Quick Actions and Choose Columns",
        "Reordering the context menus, and choosing which columns each list reads.",
    ),
    _area(
        "library",
        "caught_up",
        "Hide caught-up podcasts",
        "The View switch that hides podcasts with nothing unheard.",
    ),
    _area(
        "library",
        "watched_folders",
        "Watched folders",
        "Folders of your own audio that Cast watches for new files.",
    ),
    # -- Getting podcasts --------------------------------------------------------
    _area(
        "getting",
        "directory",
        "Directory search and Add by address",
        "Add Podcast: finding a podcast by name in a directory, or by its feed address.",
    ),
    _area(
        "getting",
        "acb_media",
        "Follow ACB Media",
        "The one-key row that follows every ACB Media podcast.",
    ),
    _area(
        "getting",
        "backups",
        "Backups and OPML",
        "Backing up the library, restoring it, and importing or exporting a "
        "subscription list. Advanced mode shows these; this switches them off "
        "entirely.",
    ),
    _area(
        "getting",
        "credentials",
        "Private feeds and directory credentials",
        "A username and password for a private feed, and a Podcast Index key.",
    ),
    _area(
        "getting",
        "spotify",
        "Spotify podcasts",
        "Connecting to Spotify and browsing its podcasts (experimental).",
    ),
    # -- Keeping things ------------------------------------------------------------
    _area(
        "keeping",
        "auto_download",
        "Automatic downloads",
        "Downloading new episodes without being asked, by the count you set.",
    ),
    _area(
        "keeping",
        "retention",
        "Retention and housekeeping",
        "Deleting played downloads, the storage cap, Free Up Space and Run "
        "Housekeeping Now. Off, nothing is ever deleted for you.",
    ),
    _area(
        "keeping",
        "keep_episode",
        "Keep This Episode and Refresh Episode Audio",
        "Pinning one episode out of retention's reach, and re-fetching its audio.",
    ),
    _area(
        "keeping",
        "export_data",
        "Export my data and Delete all data",
        "Taking everything out, and the one row that empties the library.",
    ),
    # -- Telling you ---------------------------------------------------------------
    _area(
        "telling",
        "toasts",
        "Toasts",
        "The desktop notification for a new episode or a finished download. The "
        "Notifications list still keeps the record.",
    ),
    _area(
        "telling",
        "earcons",
        "Sounds",
        "The short sounds for a new episode, a finished download and a check that ran.",
    ),
    _area(
        "telling",
        "digest",
        "New-episode digest",
        "One sentence on launch about what arrived while Cast was closed.",
    ),
    _area(
        "telling",
        "feed_notices",
        "Feed failure and gone-quiet notices",
        "Being told once when a feed keeps failing, or when a podcast has gone quiet.",
    ),
    _area(
        "telling",
        "feed_timer",
        "Automatic feed check",
        "Looking for new episodes on a schedule. Off, feeds are checked only when "
        "you press Refresh.",
    ),
    _area(
        "telling",
        "transitions",
        "Dialog transition announcements",
        "Saying a window's name as it opens and closes.",
    ),
    # -- Listening data --------------------------------------------------------------
    _area(
        "data",
        "statistics",
        "Statistics",
        "Listening statistics, streaks and Year in Review. Nothing here leaves "
        "this computer; switch it off if you would rather not be counted at all.",
    ),
    _area(
        "data",
        "recently_played",
        "Recently played and Continue Listening",
        "The record of what you played and where you stopped.",
    ),
    _area(
        "data",
        "sync",
        "Listening Places sync",
        "Carrying your place between machines through a synced folder.",
    ),
    # -- Around the app ------------------------------------------------------------------
    _area(
        "around",
        "status_bar",
        "Status bar",
        "The nine cells along the bottom, F6 away.",
    ),
    _area(
        "around",
        "tray",
        "Tray",
        "Sending Cast to the tray on close, and the tray icon's menu.",
    ),
    _area(
        "around",
        "tutorials",
        "Tutorials",
        "The guided lessons under Help.",
    ),
    _area(
        "around",
        "palette",
        "Command Palette and Go To",
        "The searchable list of every command, and the one key for every place.",
    ),
    _area(
        "around",
        "share",
        "Share and export audio",
        "Sharing a moment or a link, and saving an episode's audio as a file.",
    ),
    _area(
        "around",
        "quillins",
        "Quillins",
        "Extensions, and their menu.",
    ),
    _area(
        "around",
        "ai_features",
        "AI features",
        "Help > AI Features: the family's AI on the show notes. Each AI feature is "
        "also behind the AI help switch in Preferences and the privacy agreement.",
    ),
)

AREAS: tuple[AppArea, ...] = tuple(area for _group, area in _GROUPED)
_GROUP_OF: dict[str, str] = {area.id: group for group, area in _GROUPED}


def area_ids() -> frozenset[str]:
    return frozenset(_GROUP_OF)


def group_of(area_id: str) -> str:
    return _GROUP_OF.get(area_id, "")


def areas_in_group(group_id: str) -> list[AppArea]:
    return [area for group, area in _GROUPED if group == group_id]


# -- commands to areas ---------------------------------------------------------- #

#: Every command id Cast registers or binds, and the area that owns it. "" is
#: an id that belongs to the app itself and has no switch (Exit, Preferences,
#: the transport). The gate test walks the Cast modules for ids this table
#: does not know.
COMMAND_AREAS: dict[str, str] = {
    # the app itself: always present
    "app.announcement_self_test": "",
    "app.repeat_last_announcement": "",
    "app.repeat_last_result": "",
    "app.activity": "",
    "app.undo_last": "",
    "app.recent_problems": "",
    "app.quiet_hours": "",
    "app.quiet_hours_toggle": "",
    "app.export_setup": "",
    "app.import_setup": "",
    "app.media_tools": "",
    "app.shortcut_sheet": "",
    "view.toggle_window_to_tray": "tray",
    "app.go_to": "palette",
    "app.notifications": "notifications",
    "app.bookmarks": "notes",
    "app.bookmark_moment": "notes",
    "app.backup": "backups",
    "app.restore": "backups",
    # playing
    "podcasts.play_pause": "",
    "podcasts.stop": "",
    "podcasts.mute": "",
    "podcasts.go_to_position": "",
    "podcasts.now_playing": "now_playing",
    "podcasts.say_now_playing": "",
    "podcasts.speed_up": "speed",
    "podcasts.speed_down": "speed",
    "podcasts.speed_reset": "speed",
    "podcasts.skip_forward": "skipping",
    "podcasts.skip_back": "skipping",
    "podcasts.skip_settings": "skipping",
    "podcasts.skip_silence": "skipping",
    "podcasts.sound_enhancements": "sound",
    "podcasts.next_chapter": "transcripts",
    "podcasts.previous_chapter": "transcripts",
    "podcasts.find_chapters": "transcripts",
    "podcasts.analyze_chapters": "transcripts",
    "podcasts.episode_extras": "notes",
    "podcasts.episode_notes": "notes",
    "podcasts.add_note": "notes",
    "podcasts.stop_after_episode": "",
    "media.continue_listening": "recently_played",
    "media.sync_places": "sync",
    # queue
    "podcasts.open_queue": "queue",
    "podcasts.next_in_queue": "queue",
    "podcasts.previous_in_queue": "queue",
    "podcasts.mark_played_and_next": "queue",
    "podcasts.clear_queue": "queue",
    "podcasts.shuffle_queue": "queue",
    "podcasts.play_unheard": "",
    "podcasts.play_unheard_oldest": "",
    # inbox
    "podcasts.inbox": "inbox",
    "podcasts.inbox_folder": "inbox",
    "podcasts.mark_all_played": "",
    # downloads and keeping
    "podcasts.downloads": "downloads",
    "podcasts.pause_all_downloads": "downloads",
    "podcasts.resume_all_downloads": "downloads",
    "podcasts.free_space": "retention",
    "podcasts.run_maintenance": "retention",
    "podcasts.keep_episode": "keep_episode",
    "podcasts.export_data": "export_data",
    "podcasts.delete_all_data": "export_data",
    # getting podcasts
    "podcasts.add": "directory",
    "podcasts.add_local": "personal_audio",
    "podcasts.personal_audio": "personal_audio",
    "podcasts.scan_watched": "watched_folders",
    "podcasts.watched_folders": "watched_folders",
    "podcasts.acb_media": "acb_media",
    "podcasts.import_opml": "backups",
    "podcasts.export_opml": "backups",
    "spotify.connect": "spotify",
    "spotify.browse": "spotify",
    # library
    "podcasts.feed_check": "feed_check",
    "podcasts.quick_actions": "customizing",
    "podcasts.settings": "",
    "podcasts.open_manager": "",
    # listening data
    "podcasts.statistics": "statistics",
    # around the app
    "podcasts.tutorials": "tutorials",
}

_PREFIX_AREAS: tuple[tuple[str, str], ...] = (("tools.hosted_ai_", "ai_features"),)


def area_for_command(command_id: str) -> str | None:
    """The area that owns *command_id*; "" for the app's own; None if unknown."""
    if command_id in COMMAND_AREAS:
        return COMMAND_AREAS[command_id]
    for prefix, area in _PREFIX_AREAS:
        if command_id.startswith(prefix):
            return area
    return None


# -- profiles ---------------------------------------------------------------------- #

_JUST_LISTEN_OFF = frozenset(
    area.id
    for _group, area in _GROUPED
    if area.id
    not in {
        "inbox",
        "queue",
        "downloads",
        "now_playing",
        "sleep_timer",
        "speed",
        "skipping",
        "notes",
        "recently_played",
        "status_bar",
        "directory",
        "find",
        "folders",
    }
)

_EARSHOT_LIKE_OFF = frozenset({
    "playlists",
    "notifications",
    "winamp_keys",
    "global_hotkeys",
    "feed_check",
    "customizing",
    "watched_folders",
    "acb_media",
    "credentials",
    "spotify",
    "export_data",
    "earcons",
    "digest",
    "feed_notices",
    "transitions",
    "statistics",
    "sync",
    "tray",
    "tutorials",
    "quillins",
    "ai_features",
    "share",
})

PROFILES: tuple[AppProfile, ...] = (
    AppProfile(
        "everything",
        "Everything",
        f"All {len(AREAS)} areas on, which is what a new install is. Choose it to "
        "get back to the shipped answer after experimenting.",
        frozenset(),
    ),
    AppProfile(
        "just_listen",
        "Just Listen",
        "The places, Now Playing, the sleep timer, speed and skipping, the show "
        "notes, Continue Listening, Find, folders and Add Podcast -- and nothing "
        "else. No automatic checks, no toasts, no statistics, no extensions. "
        "Choose it for a quiet app that plays podcasts.",
        _JUST_LISTEN_OFF,
    ),
    AppProfile(
        "earshot_like",
        "Earshot-like",
        "What the Earshot phone app has: the places, playback, downloads, the "
        "Inbox, filters, settings and sync-free listening data. Off are the "
        "desktop-only extras: notifications, Winamp keys, global hotkeys, Feed "
        "Check, watched folders, Spotify, toasts and sounds, statistics, "
        "tutorials, extensions and AI.",
        _EARSHOT_LIKE_OFF,
    ),
)
