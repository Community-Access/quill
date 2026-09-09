"""What an episode row actually says, and who decides.

The single highest-value accessibility setting QUILL Cast did not have.

A screen reader reads **every** row of **every** list out loud, in full, in
order. That is not a detail of how one person uses the app; it is the app. An
episode list of two hundred rows reads every field you did not want two hundred
times, and there is no equivalent of glancing past it. Cast's answer until now
was a single boolean -- put the podcast name before the episode title in
cross-show lists -- which is one control over a question with at least seven
answers.

Earshot ships six switches for this (podcast name, published date, duration,
download status, and the episode and podcast descriptions at off / brief /
full) and it is the best idea in that app. This is Cast's version of it, plus
the two Cast can answer and Earshot cannot: **the row's order** as a named
choice rather than a boolean, and **what else this episode has** -- chapters, a
transcript -- which Cast knows about and never said.

Three rules the composer follows, all of them the reason it is a pure function
in core rather than a format string in a list control:

* **Order is a choice, not a flag.** *Title first*, *Podcast first*, *Date
  first*. Whichever comes first is what you can skim by first letter, and which
  one that should be depends entirely on how you look for things -- by show, by
  subject, or by when it landed.
* **Nothing is said twice.** In a single-podcast list the podcast's name is the
  window you are standing in, so it is dropped whatever the switch says. A
  setting that made every row of *The Allusionist* begin with "The Allusionist"
  would be a setting nobody keeps on.
* **Every part is droppable and the row still parses.** The separators are
  chosen so a row with one field and a row with six read as sentences, not as
  a list of dashes with gaps in it.

Per podcast as well as globally, because the answer genuinely differs: a daily
show with the date in every title should not have the date read again, and an
interview show with numbered titles wants the guest's name and nothing else.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.settings_types import (
    CATEGORY_ANNOUNCEMENTS,
    KIND_CHOICE,
    SettingDef,
    choices,
    define,
)

# -- the vocabulary ----------------------------------------------------------

ORDER_TITLE_FIRST = "title_first"
ORDER_PODCAST_FIRST = "podcast_first"
ORDER_DATE_FIRST = "date_first"
ROW_ORDERS: tuple[str, ...] = (ORDER_TITLE_FIRST, ORDER_PODCAST_FIRST, ORDER_DATE_FIRST)

DURATION_OFF = "off"
DURATION_LENGTH = "length"
DURATION_REMAINING = "remaining"

DESCRIPTION_OFF = "off"
DESCRIPTION_BRIEF = "brief"
DESCRIPTION_FULL = "full"

#: How much of a description "brief" is, in characters. One sentence's worth:
#: enough to tell two episodes apart, short enough that arrowing through forty
#: rows is still arrowing rather than reading.
BRIEF_LIMIT = 140

#: The separator between a row's parts. An em dash surrounded by spaces, which
#: every reader pauses on -- a comma does not, and a row of six comma-separated
#: parts reads as one long clause.
SEPARATOR = " -- "


# -- the settings ------------------------------------------------------------

SETTINGS: tuple[SettingDef, ...] = (
    define(
        "row_order",
        "&Read each row starting with:",
        "Which part of an episode row is read first. Whichever comes first is "
        "what you can skim by first letter. It changes how rows read, never "
        "what order the list is in -- Sort Episodes is the setting for that.",
        kind=KIND_CHOICE,
        category=CATEGORY_ANNOUNCEMENTS,
        default=ORDER_TITLE_FIRST,
        choices=choices(
            (ORDER_TITLE_FIRST, "The episode title"),
            (ORDER_PODCAST_FIRST, "The podcast's name"),
            (ORDER_DATE_FIRST, "The date it was published"),
        ),
        aliases=("row order", "podcast name first", "announce show name first", "skim"),
    ),
    define(
        "row_say_podcast",
        "Say the &podcast's name",
        "Include the podcast's name in each row of a list that mixes shows. It "
        "is never added in a single podcast's own episode list, where the name "
        "is the window you are already standing in.",
        category=CATEGORY_ANNOUNCEMENTS,
        default=True,
        aliases=("show name", "podcast name"),
    ),
    define(
        "row_say_date",
        "Say when it was p&ublished",
        "Include the publication date in each row. Turn it off for a show that "
        "already puts the date in every title -- it does not change sorting, "
        "which still knows the date either way.",
        category=CATEGORY_ANNOUNCEMENTS,
        default=True,
        aliases=("date", "published"),
    ),
    define(
        "row_duration",
        "Say how &long it is:",
        "Include the episode's length in each row, either the whole length or "
        "how much of it is left. An episode whose feed does not say how long it "
        "is says nothing here rather than saying zero.",
        kind=KIND_CHOICE,
        category=CATEGORY_ANNOUNCEMENTS,
        default=DURATION_LENGTH,
        choices=choices(
            (DURATION_OFF, "Don't say"),
            (DURATION_LENGTH, "The whole length"),
            (DURATION_REMAINING, "How much is left"),
        ),
        aliases=("duration", "length", "time remaining"),
    ),
    define(
        "row_say_download",
        "Say whether it is &downloaded",
        "Include downloaded, downloading or streaming in each row. It reports "
        "what is on disk; it never starts or stops a download.",
        category=CATEGORY_ANNOUNCEMENTS,
        default=True,
        aliases=("download status", "downloaded", "streaming"),
    ),
    define(
        "row_say_extras",
        "Say when it has &chapters or a transcript",
        "Include chapters and transcript in each row when this episode has "
        "them. It says what exists; it fetches nothing and nothing is "
        "downloaded to find out.",
        category=CATEGORY_ANNOUNCEMENTS,
        default=False,
        aliases=("chapters", "transcript", "extras"),
    ),
    define(
        "row_description",
        "Read the episode's descri&ption:",
        "Include the show notes in each row -- a sentence of them, or all of "
        "them. Off by default, because a description in every row is the one "
        "setting that can make a forty-row list unreadable. It does not fetch "
        "anything: an episode whose feed carried no notes says nothing here.",
        kind=KIND_CHOICE,
        category=CATEGORY_ANNOUNCEMENTS,
        default=DESCRIPTION_OFF,
        choices=choices(
            (DESCRIPTION_OFF, "Don't read it"),
            (DESCRIPTION_BRIEF, "A sentence of it"),
            (DESCRIPTION_FULL, "All of it"),
        ),
        aliases=("description", "show notes", "summary"),
    ),
    define(
        "row_episode_numbers",
        "Say the season and episode n&umber",
        "Include the publisher's own numbering in each row, where they "
        "published one. An episode the feed did not number says nothing rather "
        "than saying zero, and this changes what a row says, never the order.",
        category=CATEGORY_ANNOUNCEMENTS,
        default=False,
        aliases=("season", "episode number", "numbering"),
    ),
)

#: Every setting id this module owns, in the order the editors offer them.
SETTING_IDS: tuple[str, ...] = tuple(item.id for item in SETTINGS)


# -- the resolved shape ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RowSpeech:
    """One podcast's answers, resolved -- what its rows say."""

    order: str = ORDER_TITLE_FIRST
    say_podcast: bool = True
    say_date: bool = True
    duration: str = DURATION_LENGTH
    say_download: bool = True
    say_extras: bool = False
    description: str = DESCRIPTION_OFF
    episode_numbers: bool = False

    @classmethod
    def from_values(cls, values: dict[str, object]) -> RowSpeech:
        """Build from resolved setting values, tolerating anything missing."""
        return cls(
            order=str(values.get("row_order", ORDER_TITLE_FIRST)),
            say_podcast=bool(values.get("row_say_podcast", True)),
            say_date=bool(values.get("row_say_date", True)),
            duration=str(values.get("row_duration", DURATION_LENGTH)),
            say_download=bool(values.get("row_say_download", True)),
            say_extras=bool(values.get("row_say_extras", False)),
            description=str(values.get("row_description", DESCRIPTION_OFF)),
            episode_numbers=bool(values.get("row_episode_numbers", False)),
        )


# -- formatting the parts ----------------------------------------------------


def format_length(seconds: int) -> str:
    """A length as a person says it: ``"1 hour 5 minutes"``, ``"18 minutes"``.

    Never ``"0 minutes"`` -- a feed that publishes no duration has said
    nothing, and saying zero would be Cast inventing a fact.
    """
    if seconds <= 0:
        return ""
    minutes = max(1, round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} hour{'' if hours == 1 else 's'} {minutes} minutes"
    if hours:
        return f"{hours} hour{'' if hours == 1 else 's'}"
    return f"{minutes} minute{'' if minutes == 1 else 's'}"


def format_remaining(episode: PodcastEpisode) -> str:
    """How much of this episode is left, or its whole length when unstarted.

    "12 minutes left" is a different fact from "45 minutes", and for somebody
    deciding what to play next in the time they have it is the more useful of
    the two -- which is the entire reason this is a choice rather than a
    boolean.
    """
    total = episode.duration_seconds
    if total <= 0:
        return ""
    played = max(0, episode.position_ms // 1000)
    if played <= 0:
        return format_length(total)
    remaining = total - played
    if remaining <= 60:
        return "under a minute left"
    return f"{format_length(remaining)} left"


def format_published(published: str, *, now: datetime | None = None) -> str:
    """A publication date, relative where that is what somebody means.

    "Today", "Yesterday", "3 days ago" up to a week, then the date itself.
    Relative because within a week that *is* the fact -- somebody asking when
    an episode landed does not want to do arithmetic on a date -- and absolute
    afterwards, because "83 days ago" is arithmetic of a different kind.
    """
    stamp = _parse(published)
    if stamp is None:
        return ""
    moment = now or datetime.now(UTC)
    days = (moment.date() - stamp.date()).days
    if days < 0:
        return stamp.strftime("%d %B %Y")
    if days == 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    if stamp.year == moment.year:
        return stamp.strftime("%d %B")
    return stamp.strftime("%d %B %Y")


def _parse(published: str) -> datetime | None:
    text = (published or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        from email.utils import parsedate_to_datetime

        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if parsed is None:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def format_state(episode: PodcastEpisode, *, downloading: bool = False) -> str:
    """Downloaded, downloading, or streaming -- what is on disk right now."""
    if downloading:
        return "downloading"
    return "downloaded" if episode.downloaded_path else "streaming"


def format_extras(episode: PodcastEpisode) -> str:
    """ "chapters", "transcript", or both -- what else this episode carries."""
    parts: list[str] = []
    if episode.chapters_url or episode.tags.soundbites:
        parts.append("chapters")
    if episode.transcript_url:
        parts.append("transcript")
    return " and ".join(parts)


def format_description(description: str, mode: str) -> str:
    """The show notes, at the length that was asked for.

    Whitespace collapsed and cut on a word, because a description that ends
    mid-word reads as a fault in the app rather than as a summary.
    """
    text = " ".join((description or "").split())
    if not text or mode == DESCRIPTION_OFF:
        return ""
    if mode == DESCRIPTION_FULL or len(text) <= BRIEF_LIMIT:
        return text
    cut = text[:BRIEF_LIMIT].rsplit(" ", 1)[0]
    return f"{cut}..."


# -- the composer ------------------------------------------------------------


def compose_row(
    episode: PodcastEpisode,
    speech: RowSpeech,
    *,
    show_title: str = "",
    cross_show: bool = False,
    downloading: bool = False,
    now: datetime | None = None,
) -> str:
    """One episode row, as it should read.

    *cross_show* is what stops the row saying the obvious: in a single
    podcast's own episode list the show's name is the window you are standing
    in, so it is dropped whatever the switch says. Every other part is
    droppable and the row still parses, which is why the order is assembled
    from a list rather than from a format string with holes in it.
    """
    title = episode.title.strip() or "Untitled episode"
    if speech.episode_numbers:
        number = episode.number_label()
        if number:
            title = f"{number}: {title}"

    podcast = show_title.strip() if (cross_show and speech.say_podcast and show_title) else ""
    date = format_published(episode.published, now=now) if speech.say_date else ""

    lead: list[str] = []
    if speech.order == ORDER_PODCAST_FIRST and podcast:
        lead = [podcast, title]
    elif speech.order == ORDER_DATE_FIRST and date:
        lead = [date, title] + ([podcast] if podcast else [])
        date = ""
    else:
        lead = [title] + ([podcast] if podcast else [])

    parts: list[str] = [part for part in lead if part]
    if date:
        parts.append(date)
    if speech.duration == DURATION_REMAINING:
        length = format_remaining(episode)
    elif speech.duration == DURATION_LENGTH:
        length = format_length(episode.duration_seconds)
    else:
        length = ""
    if length:
        parts.append(length)
    if speech.say_download:
        parts.append(format_state(episode, downloading=downloading))
    if speech.say_extras:
        extras = format_extras(episode)
        if extras:
            parts.append(extras)
    described = format_description(episode.description, speech.description)
    if described:
        parts.append(described)
    return SEPARATOR.join(parts)


def describe_row_speech(speech: RowSpeech) -> str:
    """The whole shape in one sentence, for a status line or F1."""
    named = {
        ORDER_TITLE_FIRST: "the episode title",
        ORDER_PODCAST_FIRST: "the podcast's name",
        ORDER_DATE_FIRST: "the date",
    }.get(speech.order, "the episode title")
    extras = [
        name
        for name, on in (
            ("the podcast", speech.say_podcast),
            ("the date", speech.say_date),
            ("the length", speech.duration != DURATION_OFF),
            ("whether it is downloaded", speech.say_download),
            ("chapters and transcripts", speech.say_extras),
            ("the numbering", speech.episode_numbers),
            ("the description", speech.description != DESCRIPTION_OFF),
        )
        if on
    ]
    if not extras:
        return f"Rows read {named} and nothing else."
    if len(extras) == 1:
        return f"Rows read {named}, then {extras[0]}."
    return f"Rows read {named}, then " + ", ".join(extras[:-1]) + f" and {extras[-1]}."


__all__ = [
    "BRIEF_LIMIT",
    "DESCRIPTION_BRIEF",
    "DESCRIPTION_FULL",
    "DESCRIPTION_OFF",
    "DURATION_LENGTH",
    "DURATION_OFF",
    "DURATION_REMAINING",
    "ORDER_DATE_FIRST",
    "ORDER_PODCAST_FIRST",
    "ORDER_TITLE_FIRST",
    "ROW_ORDERS",
    "SEPARATOR",
    "SETTINGS",
    "SETTING_IDS",
    "RowSpeech",
    "compose_row",
    "describe_row_speech",
    "format_description",
    "format_extras",
    "format_length",
    "format_published",
    "format_remaining",
    "format_state",
]
