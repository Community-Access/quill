"""What one podcast's settings actually decide, asked in one place.

Twenty-five per-podcast settings arrived at once, and each of them has to be
*read* somewhere -- by the background check, the download queue, the episode
list, the announcer, the player. Without this module each of those call sites
would grow its own two-line resolve-and-coerce dance, and the twenty-sixth
setting would grow a twenty-sixth copy.

So: one function per question the app actually asks, every one of them taking a
library and a podcast and returning something a caller can act on directly --
minutes, a list of episodes, a boolean, a sentence. The resolution chain
(shared default, folder, podcast) is
:mod:`quill.core.podcasts.settings_resolver`'s job; the *meaning* is this one's.

Three habits run through it:

* **Answer with the thing, not the setting.** ``download_allowed_now`` returns
  whether a download may start, having already folded in the metered guard, the
  window and the clock. A caller that has to assemble three settings itself is
  a caller that will assemble them differently from the next one.
* **The permissive answer on doubt.** An unreadable value, an unknown choice, a
  clock that cannot be read: every one of them lands on "carry on as before".
  These settings restrict, and a restriction nobody chose is the worst kind.
* **Nothing here mutates.** Every function is a question. The verbs live with
  the surfaces that own them.

wx-free, strict-typed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.podcasts import settings_catalog
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.settings_defs_show import (
    BACKFILL_ALL,
    BACKFILL_MONTHS,
    BACKFILL_NEWEST,
    PRIORITY_INTERRUPT,
    PRIORITY_NORMAL,
    PRIORITY_QUIET,
    QUEUE_ORDER_OLDEST,
    TRANSCRIPTS_NEVER,
    VARIANT_BEST,
    VARIANT_SMALLEST,
)
from quill.core.podcasts.settings_resolver import value_of
from quill.core.podcasts.subscriptions import PodcastLibrary


def setting(library: PodcastLibrary, show: PodcastShow | None, setting_id: str) -> object:
    """One resolved value, or the catalogue default when the id is unknown.

    The single door every function below goes through, so an id that gets
    renamed fails in one place rather than in twenty.
    """
    definition = settings_catalog.definition(setting_id)
    if definition is None:
        return None
    return value_of(library, definition, show=show)


# -- 7.1: how often this podcast is checked ----------------------------------


def cadence_minutes(library: PodcastLibrary, show: PodcastShow) -> int:
    """How often this podcast is checked on its own, in minutes; 0 = manually.

    One cadence for a three-hundred-podcast library is either wasteful or late:
    a daily news show wants hourly, a weekly three-hour interview wants daily,
    a dormant archive wants never. Normalised through the shared refresh
    policy, so Cast and Quill Radio still accept the same values and mean the
    same thing by them.
    """
    from quill.core.podcasts.refresh_policy import normalize_interval

    return normalize_interval(setting(library, show, "refresh_minutes"))


def refreshes_at_launch(library: PodcastLibrary, show: PodcastShow) -> bool:
    return bool(setting(library, show, "refresh_on_launch"))


# -- 7.2: what arrives on subscribe ------------------------------------------


def backfill_episodes(
    library: PodcastLibrary, show: PodcastShow, episodes: list[PodcastEpisode]
) -> list[PodcastEpisode]:
    """Which of a newly subscribed podcast's episodes to collect once.

    Separate from the automatic download count, which only ever looks forward.
    This is the one-off, and it is per podcast because subscribing to a daily
    briefing and to a four-hundred-episode series are opposite acts.
    """
    mode = str(setting(library, show, "backfill_mode") or "")
    count = int(setting(library, show, "backfill_count") or 0)  # type: ignore[arg-type]
    if mode == BACKFILL_ALL:
        return list(episodes)
    ordered = sorted(episodes, key=lambda e: (e.published, e.title), reverse=True)
    if mode == BACKFILL_NEWEST:
        return ordered[: max(0, count)]
    if mode == BACKFILL_MONTHS:
        cutoff = _months_ago(count)
        if cutoff is None:
            return []
        return [episode for episode in ordered if _moment(episode.published) >= cutoff]
    return []


def _months_ago(months: int) -> datetime | None:
    if months <= 0:
        return None
    now = datetime.now(UTC)
    year, month = divmod(now.month - 1 - months, 12)
    return now.replace(year=now.year + year, month=month + 1, day=1)


def _moment(published: str) -> datetime:
    from quill.core.podcasts.row_speech import _parse  # noqa: PLC2701 - one parser, not two

    parsed = _parse(published)
    return parsed or datetime.min.replace(tzinfo=UTC)


# -- 7.3 / 7.4: how this podcast reads ---------------------------------------


def title_rules(library: PodcastLibrary, show: PodcastShow):
    """This podcast's title-tidying rules, made safe."""
    from quill.core.podcasts.title_cleanup import rules_from_stored

    return rules_from_stored(setting(library, show, "title_cleanup"))


def display_title(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> str:
    """This episode's title as it should be shown and spoken.

    The feed's own title is never modified; this is the reading of it. A
    podcast with no rules gets its title back unchanged and pays one dictionary
    lookup for the privilege.
    """
    from quill.core.podcasts.title_cleanup import apply_rules

    rules = title_rules(library, show)
    return apply_rules(episode.title, rules) if rules else episode.title


def spoken_show_name(library: PodcastLibrary, show: PodcastShow) -> str:
    """What to *say* when naming this podcast, which may not be its name.

    Feed titles are full of initialisms, punctuation and words from other
    languages that a speech engine mangles, and hearing it mangled forty times
    a day is a cost no shared setting can address. Written text is untouched --
    the podcast keeps its own name everywhere it is read rather than spoken.
    """
    spoken = str(setting(library, show, "speech_name") or "").strip()
    return spoken or show.title


# -- 7.5 / 7.19: attention ---------------------------------------------------


def notify_priority(library: PodcastLibrary, show: PodcastShow) -> str:
    """How loudly this podcast's new episodes are reported.

    Three positions rather than the boolean Cast had, because "tell me by
    name", "count it in the summary" and "say nothing at all" are three
    different instructions and the boolean could only express two of them.
    A podcast that predates this and had its announcement switched on reads as
    urgent, which is what the switch meant.
    """
    value = str(setting(library, show, "notify_priority") or PRIORITY_NORMAL)
    if value == PRIORITY_NORMAL and show.notify_new_episodes:
        return PRIORITY_INTERRUPT
    return value


def is_quiet(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether this podcast's new episodes are never spoken about."""
    return notify_priority(library, show) == PRIORITY_QUIET


def may_speak_in_quiet_hours(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether this one podcast may be announced during quiet hours.

    Only ever *widens* quiet hours for a single podcast somebody named, and
    only for the new-episode announcement -- every other kind of background
    news is still held back.
    """
    return bool(setting(library, show, "notify_past_quiet_hours"))


def announce_budget(library: PodcastLibrary) -> int:
    """How many spoken new-episode announcements an hour; 0 = no ceiling.

    A library of three hundred podcasts with twenty set to announce is a
    library that talks over you. Over the ceiling, announcements are folded
    into the shared summary rather than dropped -- nothing is lost, it is said
    once instead of twenty times.
    """
    return int(setting(library, None, "announce_max_per_hour") or 0)  # type: ignore[arg-type]


def quiet_feed_weeks(library: PodcastLibrary, show: PodcastShow) -> int:
    """Say something if this podcast publishes nothing for this many weeks."""
    return int(setting(library, show, "quiet_feed_weeks") or 0)  # type: ignore[arg-type]


def failed_check_notice(library: PodcastLibrary, show: PodcastShow) -> int:
    """Say something after this many consecutive failed checks; 0 = never."""
    return int(setting(library, show, "failed_check_notice") or 0)  # type: ignore[arg-type]


def earcon(library: PodcastLibrary, show: PodcastShow) -> str:
    """This podcast's own new-episode sound, or ``""`` for the shared one."""
    if is_quiet(library, show):
        return ""
    return str(setting(library, show, "earcon") or "").strip()


# -- 7.6: when automatic downloads may run -----------------------------------


def download_window(library: PodcastLibrary, show: PodcastShow) -> tuple[int, int]:
    """``(start hour, end hour)``; equal hours mean there is no window."""
    start = int(setting(library, show, "download_window_start") or 0)  # type: ignore[arg-type]
    end = int(setting(library, show, "download_window_end") or 0)  # type: ignore[arg-type]
    return start, end


def in_download_window(
    library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None
) -> bool:
    """Whether the clock currently allows this podcast's automatic downloads.

    Wraps midnight, because "01:00 to 06:00" and "22:00 to 02:00" are both
    things people mean. Equal hours are no window at all, which is the default
    and the only value that means "whenever".
    """
    start, end = download_window(library, show)
    if start == end:
        return True
    hour = (now or datetime.now()).hour
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def download_allowed_now(
    library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None
) -> bool:
    """Whether an **automatic** download may start for this podcast right now.

    The metered guard and the off-peak window folded into one answer, because
    every caller wants the answer and none of them wants the two questions.
    A download somebody asked for by name never comes through here.
    """
    from quill.core.net_metered import may_download

    settings = library.effective_settings(show)
    if not may_download(settings, automatic=True):
        return False
    return in_download_window(library, show, now=now)


# -- 7.7: transcripts --------------------------------------------------------


def transcript_policy(library: PodcastLibrary, show: PodcastShow) -> str:
    """When this podcast's transcripts are collected."""
    return str(setting(library, show, "transcript_policy") or TRANSCRIPTS_NEVER)


def wants_transcript(library: PodcastLibrary, show: PodcastShow, *, trigger: str) -> bool:
    """Whether *trigger* ("arrival" or "download") should fetch a transcript."""
    policy = transcript_policy(library, show)
    if policy == TRANSCRIPTS_NEVER:
        return False
    if policy == "transcribe":
        return True
    return policy == trigger


# -- 7.10: which end of the catalogue Auto-Queue works from ------------------


def queue_candidates(
    library: PodcastLibrary, show: PodcastShow, arrived: list[PodcastEpisode]
) -> list[PodcastEpisode]:
    """The episodes Auto-Queue should take, in the order it should take them.

    Newest-first is the news-show assumption Cast shipped with. Oldest-unplayed
    is how somebody starts a series at the beginning, and it looks at the whole
    catalogue rather than at what just arrived -- because for a finished series
    nothing ever arrives, and the feature would otherwise do nothing at all.
    """
    order = str(setting(library, show, "auto_queue_order") or "")
    if order != QUEUE_ORDER_OLDEST:
        return arrived
    unplayed = [episode for episode in show.episodes if not episode.played]
    unplayed.sort(key=lambda e: (e.published, e.title))
    return unplayed[:1]


# -- 7.11 / 7.12 / 7.22: storage and what is fetched -------------------------


def is_pinned(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether this podcast's downloads are exempt from the automatic sweeps."""
    return bool(setting(library, show, "storage_pinned"))


def storage_budget_mb(library: PodcastLibrary, show: PodcastShow) -> int:
    """How much disk this podcast's downloads may take; 0 = no budget."""
    return int(setting(library, show, "storage_budget_mb") or 0)  # type: ignore[arg-type]


def preferred_variant(library: PodcastLibrary, show: PodcastShow) -> str:
    return str(setting(library, show, "preferred_variant") or "default")


def audio_url(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> str:
    """The URL to fetch for this episode, honouring the variant preference.

    Podcasting 2.0's ``alternateEnclosure`` is already parsed into the
    episode's tags and was never used for anything. **Falls back to the
    publisher's own enclosure whenever the preference cannot be met**, so a
    preference can never leave an episode unplayable.
    """
    wanted = preferred_variant(library, show)
    alternates = list(getattr(episode.tags, "alternates", ()) or ())
    if wanted not in (VARIANT_SMALLEST, VARIANT_BEST) or not alternates:
        return episode.audio_url
    sized = [entry for entry in alternates if _size_of(entry) > 0 and _url_of(entry)]
    if not sized:
        return episode.audio_url
    chosen = min(sized, key=_size_of) if wanted == VARIANT_SMALLEST else max(sized, key=_size_of)
    return _url_of(chosen) or episode.audio_url


def _size_of(entry: object) -> int:
    for name in ("length", "size", "bytes"):
        value = getattr(entry, name, None)
        if isinstance(value, int) and value > 0:
            return value
    return 0


def _url_of(entry: object) -> str:
    for name in ("url", "uri", "href"):
        value = getattr(entry, name, None)
        if isinstance(value, str) and value:
            return value
    return ""


def catalog_view_limit(library: PodcastLibrary, show: PodcastShow) -> int:
    """How many episodes this podcast's list shows at once; 0 = all of them.

    A **view**, deliberately, and not a trim. A four-thousand-episode archive
    feed makes every list operation slower for everybody, and the obvious fix
    -- deleting the old episode records -- would be the one thing in this
    feature set that destroys something. Raising the limit brings them all
    back, because they never went anywhere.
    """
    return int(setting(library, show, "catalog_view_limit") or 0)  # type: ignore[arg-type]


def visible_episodes(
    library: PodcastLibrary, show: PodcastShow, episodes: list[PodcastEpisode]
) -> list[PodcastEpisode]:
    """*episodes*, cut to the catalogue view limit, newest first."""
    limit = catalog_view_limit(library, show)
    if limit <= 0 or len(episodes) <= limit:
        return list(episodes)
    ordered = sorted(episodes, key=lambda e: (e.published, e.title), reverse=True)
    return ordered[:limit]


# -- 7.13 / 7.18 / 7.24: playback --------------------------------------------


def chapter_skip_patterns(library: PodcastLibrary, show: PodcastShow) -> tuple[str, ...]:
    """Chapter titles to jump over as this podcast plays."""
    stored = setting(library, show, "chapter_skip_patterns")
    if not isinstance(stored, (list, tuple)):
        return ()
    return tuple(str(entry) for entry in stored if str(entry).strip())


def skips_chapter(library: PodcastLibrary, show: PodcastShow, title: str) -> bool:
    """Whether a chapter with this title should be skipped.

    Wildcards, matched case-insensitively against the whole chapter title --
    the same vocabulary as Episode Filters, because a person who has learned
    one pattern language in this app should not have to learn a second.
    """
    import re

    from quill.core.podcasts.models_filters import wildcard_to_regex

    for pattern in chapter_skip_patterns(library, show):
        try:
            if re.fullmatch(wildcard_to_regex(pattern), title, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def smart_speed_level(library: PodcastLibrary, show: PodcastShow) -> str:
    return str(setting(library, show, "smart_speed_level") or "medium")


def sleep_timer_minutes(library: PodcastLibrary, show: PodcastShow) -> int:
    """What the sleep timer offers while this podcast plays; 0 = the shared one."""
    return int(setting(library, show, "sleep_timer_minutes") or 0)  # type: ignore[arg-type]


# -- 7.16 / 7.17: curation ---------------------------------------------------


def default_playlist(library: PodcastLibrary, show: PodcastShow) -> str:
    """A playlist this podcast's new episodes join, by name; ``""`` for none."""
    return str(setting(library, show, "default_playlist") or "").strip()


def labels(library: PodcastLibrary, show: PodcastShow) -> list[str]:
    """This podcast's labels.

    Stored on the library rather than as a setting, because a label is not a
    value with a default -- there is no "shared default label" a podcast could
    inherit, and pretending otherwise would put an empty control in the folder
    editor that could never do anything.
    """
    return library.labels_for(show.id)


# -- 7.20 / 7.21: feed policy ------------------------------------------------


def follows_redirects(library: PodcastLibrary, show: PodcastShow) -> bool:
    return bool(setting(library, show, "follow_redirects"))


def republished_as_new(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether a re-issued episode comes back to the Inbox.

    On is what Cast has always done. Off is for a feed that re-stamps its whole
    back catalogue on every rebuild, which turns that kindness into a flood --
    and either way nothing is hidden and nothing is deleted.
    """
    return bool(setting(library, show, "republished_as_new"))


def describe_show_policy(library: PodcastLibrary, show: PodcastShow) -> str:
    """This podcast's settings in one sentence, for a status line or F1.

    Only what differs from the shared defaults, because a sentence listing
    ninety-three settings is not a sentence.
    """
    changed = settings_catalog.changed(library, show=show)
    if not changed:
        return f"{show.title} follows the shared defaults for everything."
    count = len(changed)
    first = changed[0].definition.label_text()
    return (
        f"{show.title} has {count} setting{'' if count == 1 else 's'} of its own, "
        f"starting with {first}."
    )


__all__ = [
    "announce_budget",
    "audio_url",
    "backfill_episodes",
    "cadence_minutes",
    "catalog_view_limit",
    "chapter_skip_patterns",
    "default_playlist",
    "describe_show_policy",
    "display_title",
    "download_allowed_now",
    "download_window",
    "earcon",
    "failed_check_notice",
    "in_download_window",
    "is_pinned",
    "is_quiet",
    "labels",
    "may_speak_in_quiet_hours",
    "notify_priority",
    "preferred_variant",
    "queue_candidates",
    "quiet_feed_weeks",
    "refreshes_at_launch",
    "republished_as_new",
    "setting",
    "skips_chapter",
    "sleep_timer_minutes",
    "smart_speed_level",
    "spoken_show_name",
    "storage_budget_mb",
    "title_rules",
    "transcript_policy",
    "visible_episodes",
    "wants_transcript",
]
