"""What the Podcasting 2.0 tags mean to a listener, in rows and sentences.

:mod:`quill.core.podcasts.namespace_tags` reads the tags. This decides what they
are *for*: which of them are worth showing, what each one says out loud, and what
pressing Enter on it should do.

Kept apart from the window that displays it for the usual reason -- the words a
screen reader speaks are the feature, so they belong somewhere they can be tested
without a display -- and for one specific to this feature: the same rows are
spoken as a one-line summary when somebody just wants to know whether there is
anything here, and rendered as lists when they want to look.

**Every row is a whole sentence.** "Jane Smith, guest" rather than a Name column
and a Role column, because a list that reads as "Jane Smith" then makes you move
right to learn she is the guest has spent two keystrokes on one fact.

**Every row says whether it does anything.** A person with no link is still worth
listing -- knowing who is on the episode is the point -- but the row records that
there is nothing to open, so the button can say so rather than being pressed and
silently declining.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.namespace_tags import NamespaceTags

#: What pressing the action button on a row does.
ACTION_NONE = ""
ACTION_OPEN = "open"  # a web address, in the browser
ACTION_PLAY = "play"  # audio, through the ordinary player
ACTION_SUBSCRIBE = "subscribe"  # a feed, added to the library

#: The button's label for each action. Set from the highlighted row, so the
#: control always names what it is about to do rather than staying generic.
ACTION_LABELS: dict[str, str] = {
    ACTION_NONE: "Nothing to Open",
    ACTION_OPEN: "&Open in Browser",
    ACTION_PLAY: "&Play",
    ACTION_SUBSCRIBE: "&Subscribe to This Podcast",
}


@dataclass(frozen=True, slots=True)
class Row:
    """One line in one section: what it says, and what it does."""

    label: str
    action: str = ACTION_NONE
    target: str = ""

    @property
    def is_actionable(self) -> bool:
        return bool(self.action and self.target)

    @property
    def button_label(self) -> str:
        return ACTION_LABELS.get(self.action if self.is_actionable else ACTION_NONE, "")


@dataclass(frozen=True, slots=True)
class Section:
    """A tab: a heading, the rows under it, and what it says when asked."""

    key: str
    title: str
    rows: tuple[Row, ...] = ()
    #: Read before the list, so the first thing heard is what this tab is for.
    heading: str = ""
    #: How this section is counted out loud: ("person", "people"). A tab title
    #: is a label and a count is a sentence, and "1 recommended" is neither.
    noun: tuple[str, str] = ("item", "items")

    def counted(self) -> str:
        count = len(self.rows)
        return f"{count} {self.noun[0] if count == 1 else self.noun[1]}"


@dataclass(slots=True)
class Extras:
    """Every section that has something in it. Empty ones are never built."""

    sections: list[Section] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.sections

    def section(self, key: str) -> Section | None:
        for section in self.sections:
            if section.key == key:
                return section
        return None


def _people_rows(tags: NamespaceTags, *, group_label: str) -> list[Row]:
    return [
        Row(
            label=f"{person.display} ({group_label})" if group_label else person.display,
            action=ACTION_OPEN if person.link_url else ACTION_NONE,
            target=person.link_url,
        )
        for person in tags.people
        if person.name
    ]


def spoken_position(start_ms: int) -> str:
    """A position as words, never a timecode.

    "12 minutes in" is heard once. "00:12:34" is heard as a string of digits and
    then worked out, which is the whole reason nothing in QUILL speaks timecodes.
    """
    total_seconds = max(0, start_ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        parts = [f"{hours} hour{'' if hours == 1 else 's'}"]
        if minutes:
            parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
        return f"{' '.join(parts)} in"
    if minutes:
        return f"{minutes} minute{'' if minutes == 1 else 's'} in"
    return f"{seconds} second{'' if seconds == 1 else 's'} in"


def spoken_length(duration_ms: int) -> str:
    """How long a marked moment lasts, in words."""
    seconds = max(0, duration_ms // 1000)
    if seconds < 60:
        return f"{seconds} second{'' if seconds == 1 else 's'} long"
    minutes = seconds // 60
    return f"{minutes} minute{'' if minutes == 1 else 's'} long"


def build(
    *,
    show_tags: NamespaceTags | None = None,
    episode_tags: NamespaceTags | None = None,
    show_title: str = "",
) -> Extras:
    """Everything worth showing for one episode of one show.

    Show-level and episode-level tags are merged deliberately, and labelled:
    a host belongs to the podcast and a guest belongs to the episode, and a
    People list that flattens the two loses the distinction somebody opened it
    for. Everything else simply combines, episode first.
    """
    show_tags = show_tags or NamespaceTags()
    episode_tags = episode_tags or NamespaceTags()
    sections: list[Section] = []

    people = _people_rows(episode_tags, group_label="this episode") + _people_rows(
        show_tags, group_label="this podcast"
    )
    if people:
        sections.append(
            Section(
                key="people",
                title="People",
                noun=("person", "people"),
                rows=tuple(people),
                heading="Who is on this episode, and who makes the podcast.",
            )
        )

    if episode_tags.soundbites:
        sections.append(
            Section(
                key="highlights",
                title="Highlights",
                noun=("marked moment", "marked moments"),
                rows=tuple(
                    Row(
                        label=(
                            f"{bite.title or 'Highlight'} -- "
                            f"{spoken_position(bite.start_ms)}, {spoken_length(bite.duration_ms)}"
                        ),
                        # No action here: these are chapter marks, and jumping to
                        # one belongs in the chapter list where every other jump
                        # already lives. Two places to do the same thing is how a
                        # keyboard user ends up learning neither.
                    )
                    for bite in episode_tags.soundbites
                ),
                heading=(
                    "Moments this podcast marked as worth hearing. "
                    "They also appear in the chapter list, where Enter plays from one."
                ),
            )
        )

    live = list(show_tags.live_items) + list(episode_tags.live_items)
    if live:
        sections.append(
            Section(
                key="live",
                title="Live",
                noun=("live stream", "live streams"),
                rows=tuple(
                    Row(
                        label=(
                            f"{item.title} -- {'on the air now' if item.is_live else 'not on air'}"
                        ),
                        action=ACTION_PLAY if item.is_live and item.stream_url else ACTION_NONE,
                        target=item.stream_url if item.is_live else "",
                    )
                    for item in live
                ),
                heading="Live streams this podcast is carrying in its feed.",
            )
        )

    if episode_tags.alternates:
        sections.append(
            Section(
                key="audio",
                title="Other Audio",
                noun=("other version", "other versions"),
                rows=tuple(
                    Row(label=alt.display, action=ACTION_PLAY, target=alt.url)
                    for alt in episode_tags.alternates
                ),
                heading=(
                    "Other versions of this episode's audio -- usually a smaller "
                    "one for a slow or metered connection."
                ),
            )
        )

    podroll = list(dict.fromkeys(list(show_tags.podroll) + list(episode_tags.podroll)))
    if podroll:
        sections.append(
            Section(
                key="recommended",
                title="Recommended",
                noun=("recommended podcast", "recommended podcasts"),
                rows=tuple(Row(label=url, action=ACTION_SUBSCRIBE, target=url) for url in podroll),
                heading=(
                    f"Podcasts {show_title or 'this podcast'} recommends. "
                    "Subscribing fetches the feed and reads its real name."
                ),
            )
        )

    funding = list(show_tags.funding) + list(episode_tags.funding)
    if funding:
        sections.append(
            Section(
                key="support",
                title="Support",
                noun=("support link", "support links"),
                rows=tuple(
                    Row(label=link.display, action=ACTION_OPEN, target=link.url) for link in funding
                ),
                heading=(
                    "Where this podcast asked to be supported. QUILL opens the "
                    "page in your browser and has nothing to do with what happens there."
                ),
            )
        )

    location = episode_tags.location or show_tags.location
    if location:
        sections.append(
            Section(
                key="location",
                title="Place",
                noun=("place", "places"),
                rows=(Row(label=location),),
                heading="Where this episode is about.",
            )
        )

    return Extras(sections=sections)


def summary(extras: Extras) -> str:
    """One sentence: is there anything here, and what?

    Spoken when the command runs, before the window appears, so somebody who
    only wanted to know can leave immediately.
    """
    if extras.is_empty:
        return "This podcast published no extra details for this episode."
    counted = ", ".join(section.counted() for section in extras.sections)
    return f"Extra details for this episode: {counted}."


def has_extras(
    show_tags: NamespaceTags | None = None, episode_tags: NamespaceTags | None = None
) -> bool:
    """Whether the command is worth offering at all. Cheap enough to call in a
    menu-building loop: it asks whether any tag exists, and parses nothing."""
    return (
        not (show_tags or NamespaceTags()).is_empty
        or not (episode_tags or NamespaceTags()).is_empty
    )
