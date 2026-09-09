"""Catalogue entries for the settings that decide what a *library* does.

The other half of the description of Cast's existing settings (its sibling is
:mod:`quill.core.podcasts.settings_defs_playback`): when episodes arrive, what
is kept on disk, how lists are ordered, and what is said about any of it.

Every entry here names a field of
:class:`~quill.core.podcasts.models_settings.PodcastSettings` that already
shipped. Three things are new about them and all three come from being
described rather than merely stored: they are searchable, they can be reported
as "things you have changed", and the ones marked per-podcast now resolve
through the folder level as well.

**Which levels an entry allows is a real decision, not a formality.** The
download folder is a property of this computer; the directory to search is a
property of this listener; neither is a property of one podcast, and marking
them global-only is what stops a per-show editor offering a control that could
not mean anything.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts import settings_help
from quill.core.podcasts.models_queue import coerce_int
from quill.core.podcasts.settings_types import (
    CATEGORY_ANNOUNCEMENTS,
    CATEGORY_ARRIVAL,
    CATEGORY_CURATION,
    CATEGORY_STORAGE,
    KIND_CHOICE,
    KIND_INT,
    KIND_TEXT,
    LEVEL_GLOBAL,
    SettingDef,
    choices,
    define,
)


def _keep(value: object) -> str:
    from quill.core.podcasts.single_settings import describe_keep

    return describe_keep(coerce_int(value, 0))


def _queue_age(value: object) -> str:
    from quill.core.podcasts.single_settings import describe_queue_age

    return describe_queue_age(coerce_int(value, 0))


def _download_count(value: object) -> str:
    count = coerce_int(value, 0)
    if count < 0:
        return "Downloading every episode the feed still offers."
    if count == 0:
        return "Downloading nothing automatically."
    return f"Downloading the {count} newest episode{'' if count == 1 else 's'} automatically."


def _days(noun: str, never: str) -> Callable[[object], str]:
    def describe(value: object) -> str:
        days = coerce_int(value, 0)
        if days <= 0:
            return never
        return f"{noun} after {days} day{'' if days == 1 else 's'}."

    return describe


SETTINGS: tuple[SettingDef, ...] = (
    # -- arrival -------------------------------------------------------------
    define(
        "auto_download_count",
        "&Automatically download:",
        settings_help.HELP["auto_download"],
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=0,
        minimum=-1,
        maximum=999,
        settings_field="auto_download_count",
        aliases=("auto download", "fetch", "offline", "newest"),
        describe=_download_count,
    ),
    define(
        "always_sync_full_catalog",
        "Always s&ync the full catalog",
        settings_help.HELP["always_sync"],
        category=CATEGORY_ARRIVAL,
        default=False,
        settings_field="always_sync_full_catalog",
        aliases=("backfill", "back catalogue", "everything"),
    ),
    define(
        "auto_download_queued",
        "Also download anything you add to the Play &Queue",
        settings_help.HELP["download_queued"],
        category=CATEGORY_ARRIVAL,
        default=True,
        settings_field="auto_download_queued",
        aliases=("queue", "download"),
    ),
    define(
        "auto_download_inbox",
        "Also download &everything routed to the Inbox",
        settings_help.HELP["download_inbox"],
        category=CATEGORY_ARRIVAL,
        default=False,
        settings_field="auto_download_inbox",
        aliases=("inbox", "download"),
    ),
    define(
        "download_on_metered",
        "Download automatically on a &metered connection",
        settings_help.HELP["metered"],
        category=CATEGORY_ARRIVAL,
        default=True,
        settings_field="download_on_metered",
        aliases=("wifi", "wi-fi only", "mobile data", "tethering", "metered"),
    ),
    define(
        "refresh_minutes",
        "Check subscribed feeds e&very:",
        "How often Cast checks your feeds on its own; zero means only when you "
        "ask. Quill Radio shares the answer -- whichever app checks says so, and "
        "the other stays quiet inside the same interval -- so this is one job "
        "over one set of feeds, never two.",
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=0,
        minimum=0,
        maximum=10080,
        settings_field="refresh_minutes",
        aliases=("refresh", "cadence", "interval", "check", "poll"),
        describe=lambda value: (
            "Feeds are only checked when you ask."
            if coerce_int(value, 0) <= 0
            else f"Checking feeds every {coerce_int(value, 0)} minutes."
        ),
    ),
    define(
        "refresh_on_launch",
        "Also check once at &launch",
        "Checks your feeds when Cast opens, separately from the interval above. "
        "Separate on purpose: wanting an hourly check is not the same as wanting "
        "to wait on the network while the app is opening.",
        category=CATEGORY_ARRIVAL,
        default=False,
        settings_field="refresh_on_launch",
        aliases=("startup", "launch", "refresh"),
    ),
    define(
        "reconnect_enabled",
        "&Reconnect and keep downloading automatically",
        settings_help.HELP["reconnect"],
        category=CATEGORY_ARRIVAL,
        default=True,
        settings_field="reconnect_enabled",
        aliases=("retry", "resume", "dropped"),
    ),
    define(
        "reconnect_max_attempts",
        "Reconnect attempts:",
        settings_help.HELP["reconnect_attempts"],
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        levels=(LEVEL_GLOBAL,),
        default=5,
        minimum=0,
        maximum=99,
        settings_field="reconnect_max_attempts",
        aliases=("retry", "attempts"),
    ),
    define(
        "reconnect_wait_seconds",
        "Seconds between attempts:",
        settings_help.HELP["reconnect_wait"],
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        levels=(LEVEL_GLOBAL,),
        default=10,
        minimum=1,
        maximum=3600,
        settings_field="reconnect_wait_seconds",
        aliases=("retry", "wait", "backoff"),
    ),
    define(
        "inbox_mode",
        "Which shows go to the &Inbox:",
        settings_help.HELP["inbox_mode"],
        kind=KIND_CHOICE,
        category=CATEGORY_ARRIVAL,
        levels=(LEVEL_GLOBAL,),
        default="include",
        choices=choices(
            ("include", "Only the ones I mark"), ("exclude", "Every show except the ones I mark")
        ),
        settings_field="inbox_mode",
        aliases=("inbox", "opt in", "opt out"),
    ),
    define(
        "inbox_max_episodes",
        "&Inbox: keep at most (0 = no limit):",
        settings_help.HELP["inbox_max"],
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=0,
        minimum=0,
        maximum=999,
        settings_field="inbox_max_episodes",
        aliases=("inbox", "cap", "limit"),
    ),
    define(
        "inbox_age_limit_hours",
        "Inbox: drop episodes &older than:",
        settings_help.SHOW_HELP["inbox_age"],
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=0,
        minimum=0,
        maximum=8760,
        settings_field="inbox_age_limit_hours",
        aliases=("inbox", "age", "stale"),
    ),
    define(
        "queue_age_limit_days",
        "&Expire from the queue:",
        settings_help.SHOW_HELP["queue_expiry"],
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=0,
        minimum=0,
        maximum=3650,
        settings_field="queue_age_limit_days",
        aliases=("queue", "expiry", "stale"),
        describe=_queue_age,
    ),
    # -- storage -------------------------------------------------------------
    define(
        "retention",
        "Defa&ult retention:",
        settings_help.HELP["retention"],
        kind=KIND_CHOICE,
        category=CATEGORY_STORAGE,
        default="keep_all",
        choices=choices(
            ("keep_all", "Keep every download"),
            ("keep_last_n", "Keep only the most recent"),
        ),
        settings_field="retention",
        aliases=("keep", "delete", "prune"),
    ),
    define(
        "retention_count",
        "&Keep the most recent:",
        settings_help.HELP["keep_last_n"],
        kind=KIND_INT,
        category=CATEGORY_STORAGE,
        default=5,
        minimum=0,
        maximum=9999,
        settings_field="retention_count",
        aliases=("keep", "episodes to keep", "how many"),
        describe=_keep,
    ),
    define(
        "download_retention_days",
        "Delete downloads after (days, 0 = never):",
        settings_help.HELP["delete_after_days"],
        kind=KIND_INT,
        category=CATEGORY_STORAGE,
        default=0,
        minimum=0,
        maximum=3650,
        settings_field="download_retention_days",
        aliases=("delete", "age", "cleanup"),
        describe=_days("Deleting downloads", "Downloads are never deleted for being old."),
    ),
    define(
        "delete_after_play",
        "Delete its downloaded &file",
        settings_help.HELP["delete_after_playing"],
        category=CATEGORY_STORAGE,
        default=False,
        settings_field="delete_after_play",
        aliases=("delete", "played", "cleanup"),
    ),
    define(
        "storage_cap_mb",
        "Total download storage cap (MB, 0 = none):",
        settings_help.HELP["storage_cap"],
        kind=KIND_INT,
        category=CATEGORY_STORAGE,
        default=0,
        minimum=0,
        maximum=10_000_000,
        settings_field="storage_cap_mb",
        aliases=("disk", "space", "quota", "cap"),
    ),
    define(
        "playback_cache_cap_mb",
        "Space for streamed episodes (MB, 0 = no limit):",
        settings_help.HELP["playback_cache_cap"],
        kind=KIND_INT,
        category=CATEGORY_STORAGE,
        levels=(LEVEL_GLOBAL,),
        default=1024,
        minimum=0,
        maximum=10_000_000,
        settings_field="playback_cache_cap_mb",
        aliases=("cache", "stream", "disk"),
    ),
    define(
        "download_root",
        "&Download location:",
        settings_help.HELP["download_folder"],
        kind=KIND_TEXT,
        category=CATEGORY_STORAGE,
        levels=(LEVEL_GLOBAL,),
        default="",
        settings_field="download_root",
        device_local=True,
        aliases=("folder", "path", "where"),
    ),
    define(
        "delete_files_on_remove",
        "&When I unsubscribe, delete downloaded files:",
        settings_help.HELP["unsubscribe_files"],
        kind=KIND_CHOICE,
        category=CATEGORY_STORAGE,
        levels=(LEVEL_GLOBAL,),
        default="ask",
        choices=choices(("ask", "Ask me"), ("always", "Always"), ("never", "Never")),
        settings_field="delete_files_on_remove",
        aliases=("unsubscribe", "delete", "files"),
    ),
    define(
        "auto_trim_silence",
        "Auto-&trim silence from downloaded episodes",
        settings_help.HELP["auto_trim"],
        category=CATEGORY_STORAGE,
        default=False,
        settings_field="auto_trim_silence",
        aliases=("silence", "trim", "process"),
    ),
    define(
        "normalize_loudness",
        "Normali&ze loudness of downloaded episodes",
        settings_help.HELP["normalize"],
        category=CATEGORY_STORAGE,
        default=False,
        settings_field="normalize_loudness",
        aliases=("loudness", "volume", "process"),
    ),
    # -- announcements -------------------------------------------------------
    define(
        "download_notify",
        "&Notify me when downloads finish",
        settings_help.HELP["download_notify"],
        category=CATEGORY_ANNOUNCEMENTS,
        levels=(LEVEL_GLOBAL,),
        default=False,
        settings_field="download_notify",
        aliases=("notification", "toast", "downloads"),
    ),
    # -- curation ------------------------------------------------------------
    define(
        "episode_sort_mode",
        "Sort episodes b&y:",
        "The order a podcast's episodes are listed in. It changes the order "
        "only -- no episode is hidden by it, and the row text is decided by the "
        "announcement settings instead.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        default="date_newest",
        choices=choices(
            ("date_newest", "Newest first"),
            ("date_oldest", "Oldest first"),
            ("title_az", "Title, A to Z"),
            ("title_za", "Title, Z to A"),
            ("duration_longest", "Longest first"),
            ("duration_shortest", "Shortest first"),
            ("season_episode", "Season and episode number"),
        ),
        settings_field="episode_sort_mode",
        aliases=("sort", "order", "season", "serial"),
    ),
    define(
        "episode_list_view_mode",
        "Show cross-show lists as:",
        "How the Inbox and the other mixed lists are shaped: one stream, "
        "clustered by podcast, or real folders. It groups rows; it never "
        "removes any.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="grouped",
        choices=choices(
            ("flat", "One flat list"),
            ("grouped", "Grouped by podcast"),
            ("folders", "Folders, one per podcast"),
        ),
        settings_field="episode_list_view_mode",
        aliases=("inbox", "grouping", "view"),
    ),
    define(
        "show_sort_mode",
        "Sort podcasts by:",
        "The order your podcasts are listed in everywhere. Custom is your own "
        "hand-arranged order, kept with Move Up and Move Down. It changes the "
        "order only -- no podcast is hidden by any of the choices.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="title_az",
        choices=choices(
            ("title_az", "Title, A to Z"),
            ("title_za", "Title, Z to A"),
            ("unheard_first", "Most unheard first"),
            ("recently_updated", "Recently updated first"),
            ("custom", "My own order"),
        ),
        settings_field="show_sort_mode",
        aliases=("sort", "order", "library"),
    ),
    define(
        "queue_group_mode",
        "Group the Play Queue by:",
        "Whether the Play Queue clusters its rows by podcast or by folder. It "
        "is a grouping, not a re-ordering: what plays next is still what is at "
        "the top of the queue.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="none",
        choices=choices(
            ("none", "Nothing -- one list"),
            ("show", "Podcast"),
            ("folder", "Folder"),
        ),
        settings_field="queue_group_mode",
        aliases=("queue", "grouping"),
    ),
    define(
        "default_launch_view",
        "Start on this &view:",
        settings_help.HELP["launch_view"],
        kind=KIND_TEXT,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="",
        settings_field="default_launch_view",
        aliases=("launch", "startup", "open on"),
    ),
    define(
        "directory_source",
        "Search these directories:",
        "Which podcast directories a search asks. Both is the default because "
        "Cast carries its own key for one of them; choosing one narrows the "
        "search rather than disabling searching.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="both",
        choices=choices(
            ("both", "Both"), ("itunes", "iTunes only"), ("podcast_index", "Podcast Index only")
        ),
        settings_field="directory_source",
        aliases=("search", "directory", "itunes", "podcast index"),
    ),
    define(
        "stats_streaks_enabled",
        "Show listenin&g streaks in Statistics",
        settings_help.HELP["streaks"],
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default=False,
        settings_field="stats_streaks_enabled",
        aliases=("streak", "stats", "gamification"),
    ),
    define(
        "history_retention_days",
        "Keep my listening &history for:",
        settings_help.HELP["history_days"],
        kind=KIND_INT,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default=90,
        minimum=-1,
        maximum=36500,
        settings_field="history_retention_days",
        aliases=("history", "privacy", "forget"),
        describe=lambda value: (
            "No listening history is kept at all."
            if coerce_int(value, 0) < 0
            else (
                "Listening history is kept forever."
                if coerce_int(value, 0) == 0
                else f"Listening history is kept for {coerce_int(value, 0)} days."
            )
        ),
    ),
)

__all__ = ["SETTINGS"]
