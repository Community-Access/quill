"""The per-podcast settings proposal, defined.

Twenty-five settings, every one of which had to survive the same test: **a
single shared value would be wrong for somebody, not merely imperfect.** "One
badly-mastered show among forty" is the shape -- a global control cannot fix
it, because turning it up fixes one show and ruins thirty-nine.

Two further tests every entry here passed:

* **Is it worse by ear than by eye?** A screen reader reads every row of every
  list out loud, in full. A numeric prefix on two hundred episode titles
  destroys first-letter navigation and no sighted user ever notices, which is
  why *title cleanup* is here and why *artwork* very nearly is not.
* **Can it be wrong safely?** Anything that hides, skips or deletes needs a way
  back before it needs a checkbox. Nothing in this file deletes; the two that
  hide (the catalogue view limit, the filter's own scopes) both have a named
  way back.

Several of these needed no new storage at all -- the cadence, the chapter
policy, the session behaviour and the metered guard were *already* per-show
overridable in the data model and reachable only globally. Describing them here
is what surfaces them, and it is the cheapest third of the proposal.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from quill.core.podcasts.settings_types import (
    CATEGORY_ANNOUNCEMENTS,
    CATEGORY_ARRIVAL,
    CATEGORY_CURATION,
    CATEGORY_PLAYBACK,
    CATEGORY_STORAGE,
    KIND_CHOICE,
    KIND_INT,
    KIND_OPAQUE,
    KIND_TEXT,
    LEVEL_GLOBAL,
    LEVEL_SHOW,
    SettingDef,
    choices,
    define,
)

# -- vocabularies the rest of the app matches on -----------------------------

BACKFILL_NONE = "none"
BACKFILL_NEWEST = "newest"
BACKFILL_MONTHS = "months"
BACKFILL_ALL = "all"

QUEUE_ORDER_NEWEST = "newest"
QUEUE_ORDER_OLDEST = "oldest"

TRANSCRIPTS_NEVER = "never"
TRANSCRIPTS_ON_ARRIVAL = "arrival"
TRANSCRIPTS_ON_DOWNLOAD = "download"
TRANSCRIPTS_TRANSCRIBE = "transcribe"

PRIORITY_INTERRUPT = "interrupt"
PRIORITY_NORMAL = "normal"
PRIORITY_QUIET = "quiet"

VARIANT_DEFAULT = "default"
VARIANT_SMALLEST = "smallest"
VARIANT_BEST = "best"

TRIM_LIGHT = "light"
TRIM_MEDIUM = "medium"
TRIM_STRONG = "strong"

#: Every hour of the day is a valid download-window bound; the two being equal
#: means "no window", which is the default and the only value that means
#: "whenever".
WINDOW_ANY = 0


SETTINGS: tuple[SettingDef, ...] = (
    # -- 7.1 / 7.2 / 7.6: when episodes arrive and how many ------------------
    define(
        "backfill_mode",
        "When I subscribe, also &fetch:",
        "How much of a podcast's back catalogue to collect once, at the moment "
        "you subscribe. It is a one-off and it is separate from the automatic "
        "download count, which only ever looks forward -- subscribing to a "
        "daily news feed and to a 400-episode series are opposite acts.",
        kind=KIND_CHOICE,
        category=CATEGORY_ARRIVAL,
        default=BACKFILL_NONE,
        choices=choices(
            (BACKFILL_NONE, "Nothing -- just new episodes from now on"),
            (BACKFILL_NEWEST, "The newest few"),
            (BACKFILL_MONTHS, "The last few months"),
            (BACKFILL_ALL, "Everything the feed still offers"),
        ),
        aliases=("backfill", "back catalogue", "history", "subscribe"),
    ),
    define(
        "backfill_count",
        "How many, or how many months:",
        "The number behind the choice above -- episodes when you asked for the "
        "newest few, months when you asked for the last few months. It is read "
        "only when that choice needs it, and it never applies twice.",
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=5,
        minimum=1,
        maximum=999,
        aliases=("backfill", "how many"),
    ),
    define(
        "download_window_start",
        "Only download automatically &after (hour):",
        "The earliest hour of the day an automatic download may start, on a "
        "24-hour clock. It never delays a download you asked for by name, and "
        "leaving both hours the same means there is no window at all.",
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=WINDOW_ANY,
        minimum=0,
        maximum=23,
        aliases=("off peak", "overnight", "window", "schedule", "bandwidth"),
    ),
    define(
        "download_window_end",
        "...and &before (hour):",
        "The hour an automatic download window closes. A download already "
        "running is never cut off when the window ends -- the window decides "
        "when work may start, not when it must stop.",
        kind=KIND_INT,
        category=CATEGORY_ARRIVAL,
        default=WINDOW_ANY,
        minimum=0,
        maximum=23,
        aliases=("off peak", "overnight", "window", "schedule"),
    ),
    define(
        "auto_queue_order",
        "Auto-Queue takes the:",
        "Which end of the catalogue Auto-Queue works from. Oldest first is how "
        "you start a series at the beginning; it queues one episode at a time "
        "either way and never re-queues something you have played.",
        kind=KIND_CHOICE,
        category=CATEGORY_ARRIVAL,
        levels=(LEVEL_GLOBAL, LEVEL_SHOW),
        default=QUEUE_ORDER_NEWEST,
        choices=choices(
            (QUEUE_ORDER_NEWEST, "Newest episode"),
            (QUEUE_ORDER_OLDEST, "Oldest unplayed episode"),
        ),
        aliases=("queue", "beginning", "serial", "order"),
    ),
    # -- 7.7: transcripts ----------------------------------------------------
    define(
        "transcript_policy",
        "Fetch &transcripts:",
        "When to collect a podcast's transcripts. A cached transcript is what "
        "lets Search Everywhere find a sentence rather than a title. Fetching "
        "never plays or downloads audio; transcribing here is the one choice "
        "that does read the audio, which is why it is per podcast.",
        kind=KIND_CHOICE,
        category=CATEGORY_ARRIVAL,
        default=TRANSCRIPTS_NEVER,
        choices=choices(
            (TRANSCRIPTS_NEVER, "Never -- only when I ask"),
            (TRANSCRIPTS_ON_ARRIVAL, "When an episode arrives"),
            (TRANSCRIPTS_ON_DOWNLOAD, "When I download an episode"),
            (TRANSCRIPTS_TRANSCRIBE, "And transcribe it myself when the feed has none"),
        ),
        aliases=("transcript", "subtitles", "search", "whisper"),
    ),
    # -- 7.5 / 7.19: attention ----------------------------------------------
    define(
        "notify_priority",
        "New episodes of this podcast are:",
        "How loudly this podcast's new episodes are reported. Urgent may "
        "interrupt what is being read; quiet is never spoken at all. It changes "
        "what is said, never what arrives -- a quiet podcast still downloads, "
        "queues and files exactly as it would.",
        kind=KIND_CHOICE,
        category=CATEGORY_ANNOUNCEMENTS,
        default=PRIORITY_NORMAL,
        choices=choices(
            (PRIORITY_INTERRUPT, "Urgent -- say so straight away"),
            (PRIORITY_NORMAL, "Normal -- count them in the summary"),
            (PRIORITY_QUIET, "Quiet -- say nothing"),
        ),
        aliases=("notify", "announce", "interrupt", "priority", "quiet"),
    ),
    define(
        "notify_past_quiet_hours",
        "May speak during &quiet hours",
        "Lets this one podcast's new-episode announcement through quiet hours. "
        "For a live or news feed you asked to be told about; it does not affect "
        "any other kind of announcement, and quiet hours still hold everything "
        "else back.",
        category=CATEGORY_ANNOUNCEMENTS,
        levels=(LEVEL_SHOW,),
        default=False,
        aliases=("quiet hours", "night", "interrupt"),
    ),
    define(
        "announce_max_per_hour",
        "At most this many spoken announcements an hour (0 = no limit):",
        "A ceiling on how often Cast speaks about new episodes. Anything over "
        "the ceiling is folded into the shared summary rather than dropped -- "
        "nothing is lost, it is only said once instead of twenty times.",
        kind=KIND_INT,
        category=CATEGORY_ANNOUNCEMENTS,
        levels=(LEVEL_GLOBAL,),
        default=0,
        minimum=0,
        maximum=999,
        aliases=("notify", "budget", "chatty", "limit"),
    ),
    define(
        "quiet_feed_weeks",
        "Tell me if this podcast goes quiet for (weeks, 0 = never):",
        "Says something when a podcast you follow stops publishing for this "
        "long. It never unsubscribes you and never stops checking the feed -- a "
        "show that ends does so silently, and this is the only notice you get.",
        kind=KIND_INT,
        category=CATEGORY_ANNOUNCEMENTS,
        default=0,
        minimum=0,
        maximum=520,
        aliases=("dead feed", "gone quiet", "abandoned", "stopped"),
    ),
    define(
        "failed_check_notice",
        "Tell me after this many failed checks (0 = never):",
        "Says something when a feed has failed this many times in a row. It "
        "keeps trying either way -- this decides when you are told, not when "
        "Cast gives up, and Cast does not give up.",
        kind=KIND_INT,
        category=CATEGORY_ANNOUNCEMENTS,
        default=0,
        minimum=0,
        maximum=99,
        aliases=("dead feed", "error", "broken", "404"),
    ),
    # -- 7.3 / 7.4: how this podcast reads ----------------------------------
    define(
        "title_cleanup",
        "Tidy episode titles...",
        "Patterns removed from this podcast's episode titles when they are "
        "shown and spoken. The feed's own title is never changed and nothing is "
        "renamed -- it is the reading that is tidied, so first-letter "
        "navigation works on the part of the title that differs.",
        kind=KIND_OPAQUE,
        category=CATEGORY_ANNOUNCEMENTS,
        levels=(LEVEL_SHOW,),
        default=(),
        editor="title_cleanup",
        aliases=("prefix", "rename", "titles", "tidy", "strip"),
    ),
    define(
        "speech_name",
        "Say this podcast's &name as:",
        "A spelling used only when this podcast's name is spoken, for a title "
        "your speech engine mangles. It changes nothing you can read -- the "
        "podcast keeps its own name everywhere it is written.",
        kind=KIND_TEXT,
        category=CATEGORY_ANNOUNCEMENTS,
        levels=(LEVEL_SHOW,),
        default="",
        aliases=("pronounce", "pronunciation", "phonetic", "speech", "tts"),
    ),
    define(
        "earcon",
        "Play this sound when it publishes:",
        "A sound of its own for this podcast's new episodes, from your active "
        "sound pack. It is played instead of the shared new-episode sound, not "
        "as well, and a quiet podcast stays silent whatever is chosen here.",
        kind=KIND_TEXT,
        category=CATEGORY_ANNOUNCEMENTS,
        levels=(LEVEL_SHOW,),
        default="",
        aliases=("sound", "earcon", "chime", "alert"),
    ),
    # -- 7.11 / 7.12 / 7.22 / 7.23: storage and what is fetched -------------
    define(
        "storage_budget_mb",
        "This podcast may use (MB, 0 = no budget):",
        "How much disk this one podcast's downloads may take. It is a budget "
        "inside the total cap, not an addition to it, and reaching it stops new "
        "automatic downloads rather than deleting anything you already have.",
        kind=KIND_INT,
        category=CATEGORY_STORAGE,
        levels=(LEVEL_GLOBAL, LEVEL_SHOW),
        default=0,
        minimum=0,
        maximum=10_000_000,
        aliases=("disk", "quota", "space", "budget"),
    ),
    define(
        "storage_pinned",
        "Ne&ver delete this podcast's downloads",
        "Exempts this podcast from the storage cap, the age rule and "
        "delete-after-playing. It protects files from the automatic sweeps "
        "only -- Remove Downloaded Copy still works, and it is not a licence to "
        "fill the disk silently, because the sweeps report what they skipped.",
        category=CATEGORY_STORAGE,
        levels=(LEVEL_SHOW,),
        default=False,
        aliases=("keep", "archive", "pin", "protect"),
    ),
    define(
        "preferred_variant",
        "Prefer the audio that is:",
        "Which version of an episode to fetch when the feed offers more than "
        "one. Falls back to the publisher's own default whenever the choice is "
        "not available, so it can never leave an episode unplayable.",
        kind=KIND_CHOICE,
        category=CATEGORY_STORAGE,
        default=VARIANT_DEFAULT,
        choices=choices(
            (VARIANT_DEFAULT, "Whatever the publisher lists first"),
            (VARIANT_SMALLEST, "The smallest file"),
            (VARIANT_BEST, "The best quality"),
        ),
        aliases=("bitrate", "quality", "size", "alternate", "bandwidth"),
    ),
    define(
        "catalog_view_limit",
        "Show at most this many episodes (0 = all of them):",
        "How many of this podcast's episodes the list shows at once, newest "
        "first. It is a view: nothing is deleted, nothing is unsubscribed, and "
        "search and the older episodes are all still there when you raise it.",
        kind=KIND_INT,
        category=CATEGORY_CURATION,
        default=0,
        minimum=0,
        maximum=100_000,
        aliases=("limit", "huge feed", "slow", "archive"),
    ),
    define(
        "artwork_override",
        "Use this artwork instead:",
        "A picture file to use for this podcast in the tray and the window. "
        "Cosmetic only -- nothing is downloaded, and it changes nothing a "
        "screen reader says.",
        kind=KIND_TEXT,
        category=CATEGORY_CURATION,
        levels=(LEVEL_SHOW,),
        default="",
        device_local=True,
        aliases=("artwork", "image", "icon", "cover"),
    ),
    # -- 7.13 / 7.18 / 7.24: playback ---------------------------------------
    define(
        "chapter_skip_patterns",
        "Skip chapters named...",
        "Chapter titles to jump over as an episode plays -- an advert break a "
        "publisher marked, a sponsor read. Exact where a seconds-based skip is "
        "a guess. It skips over them during playback and removes nothing.",
        kind=KIND_OPAQUE,
        category=CATEGORY_PLAYBACK,
        levels=(LEVEL_SHOW,),
        default=(),
        editor="chapter_skip",
        aliases=("advert", "sponsor", "skip", "chapters"),
    ),
    define(
        "smart_speed_level",
        "How much silence to shorten:",
        "How hard the silence trimmer works, when it is switched on above. It "
        "only ever shortens gaps -- it never speeds anybody up and never "
        "changes the audio on disk.",
        kind=KIND_CHOICE,
        category=CATEGORY_PLAYBACK,
        default=TRIM_MEDIUM,
        choices=choices(
            (TRIM_LIGHT, "A little"),
            (TRIM_MEDIUM, "A moderate amount"),
            (TRIM_STRONG, "As much as possible"),
        ),
        aliases=("smart speed", "silence", "trim"),
    ),
    define(
        "sleep_timer_minutes",
        "Sleep timer starts at (minutes, 0 = off):",
        "How long the sleep timer runs when you start it while this podcast is "
        "playing. It does not start a timer by itself -- it only decides what "
        "the timer offers when you do.",
        kind=KIND_INT,
        category=CATEGORY_PLAYBACK,
        default=0,
        minimum=0,
        maximum=600,
        aliases=("sleep", "timer", "bedtime"),
    ),
    # -- 7.16 / 7.17: curation ----------------------------------------------
    define(
        "default_playlist",
        "Also add new episodes to the playlist:",
        "A playlist this podcast's new episodes join as they arrive. It adds "
        "them to that list only -- it does not queue them, download them, or "
        "take them out of the Inbox.",
        kind=KIND_TEXT,
        category=CATEGORY_CURATION,
        levels=(LEVEL_SHOW,),
        default="",
        aliases=("playlist", "commute", "routing"),
    ),
    define(
        "labels",
        "Labels...",
        "Your own words for this podcast, as many as you like. A folder is one "
        "home and a label is not a home at all: labelling a podcast never moves "
        "it, and a smart playlist can ask for a label the way it asks for a "
        "folder.",
        kind=KIND_OPAQUE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_SHOW,),
        default=(),
        editor="labels",
        aliases=("tag", "label", "keyword", "group"),
    ),
    # -- 7.20 / 7.21: feed policy -------------------------------------------
    define(
        "follow_redirects",
        "Follow permanent feed re&directs",
        "Lets a feed that has permanently moved update its own address. It "
        "follows the redirect only when the server calls it permanent, and it "
        "never carries a saved username and password to a new host.",
        category=CATEGORY_ARRIVAL,
        default=False,
        aliases=("redirect", "moved", "301", "url"),
    ),
    define(
        "republished_as_new",
        "Treat re-published episodes as ne&w",
        "Whether a corrected or re-cut episode comes back to your Inbox. On is "
        "what Cast has always done; off suits a feed that re-stamps its whole "
        "back catalogue on every rebuild, and it never hides an episode either "
        "way.",
        category=CATEGORY_ARRIVAL,
        default=True,
        aliases=("republish", "reissue", "corrected", "flood"),
    ),
    define(
        "duplicate_feed_policy",
        "If a podcast is already subscribed:",
        "What to do when a feed you add turns out to be one you already "
        "follow. Warning is the default; allowing it makes a second, "
        "independent subscription rather than merging the two.",
        kind=KIND_CHOICE,
        category=CATEGORY_ARRIVAL,
        levels=(LEVEL_GLOBAL,),
        default="warn",
        choices=choices(
            ("warn", "Tell me, and let me decide"),
            ("skip", "Skip it quietly"),
            ("allow", "Add it anyway"),
        ),
        aliases=("duplicate", "twice", "same feed"),
    ),
)

__all__ = [
    "BACKFILL_ALL",
    "BACKFILL_MONTHS",
    "BACKFILL_NEWEST",
    "BACKFILL_NONE",
    "PRIORITY_INTERRUPT",
    "PRIORITY_NORMAL",
    "PRIORITY_QUIET",
    "QUEUE_ORDER_NEWEST",
    "QUEUE_ORDER_OLDEST",
    "SETTINGS",
    "TRANSCRIPTS_NEVER",
    "TRANSCRIPTS_ON_ARRIVAL",
    "TRANSCRIPTS_ON_DOWNLOAD",
    "TRANSCRIPTS_TRANSCRIBE",
    "TRIM_LIGHT",
    "TRIM_MEDIUM",
    "TRIM_STRONG",
    "VARIANT_BEST",
    "VARIANT_DEFAULT",
    "VARIANT_SMALLEST",
    "WINDOW_ANY",
]
