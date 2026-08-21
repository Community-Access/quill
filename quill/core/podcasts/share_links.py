"""Share the moment, not just the file.

Cast could copy an episode's audio URL and save its audio to a file. Neither of
those is what somebody means when they say "listen to this bit". What they mean
is a place *inside* an episode -- 41 minutes and 12 seconds into this show --
and there was no way to hand that to anybody.

**Two things go on the clipboard, always, together.** A link that reopens at the
right second, and a plain English sentence that says the same thing. The
sentence is not a fallback afterthought: a link nobody can open is worse than a
sentence anybody can paste, and the person receiving it very often does not have
QUILL Cast. The sentence works in an email, in a text message, read aloud over
the phone.

**Nothing here fetches anything.** ``parse_link`` reads somebody else's input off
a command line, so it is written as a parser that refuses rather than one that
guesses, and the caller is required to check the feed against the library before
playing a note of it -- see :func:`parse_link`'s own warning.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

__all__ = ["SCHEME", "ShareTarget", "build_link", "build_text", "parse_link", "spoken_position"]

#: The URI scheme the installer registers. Named for the app rather than
#: something generic, so two QUILL apps can never fight over one scheme.
SCHEME = "quill-cast"

_PREFIX = f"{SCHEME}://episode"


@dataclass(frozen=True, slots=True)
class ShareTarget:
    """What a shared link points at."""

    feed_url: str
    guid: str
    position_ms: int = 0


def spoken_position(position_ms: int) -> str:
    """A position as words: "41 minutes 12 seconds".

    Words rather than ``41:12``, for the reason every duration in this codebase
    is spelled out: a screen reader reads a colon-separated number as a time of
    day, and this is a length.
    """
    total = max(0, int(position_ms)) // 1000
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)


def build_link(feed_url: str, guid: str, position_ms: int = 0) -> str:
    """``quill-cast://episode?feed=...&guid=...&t=<seconds>``, or "".

    Seconds rather than milliseconds in the link, because a shared moment is a
    human-scale thing and a link somebody may retype should not carry three
    digits nobody can hear the difference in.
    """
    feed = (feed_url or "").strip()
    identifier = (guid or "").strip()
    if not feed or not identifier:
        return ""
    params = urllib.parse.urlencode({
        "feed": feed,
        "guid": identifier,
        "t": max(0, int(position_ms)) // 1000,
    })
    return f"{_PREFIX}?{params}"


def build_text(show_title: str, episode_title: str, position_ms: int = 0) -> str:
    """The human line: "Show Title, Episode Title, at 41 minutes 12 seconds"."""
    show = (show_title or "").strip()
    episode = (episode_title or "").strip() or "an episode"
    where = f"at {spoken_position(position_ms)}" if position_ms > 0 else "from the start"
    return f"{show}, {episode}, {where}" if show else f"{episode}, {where}"


def build_share(
    show_title: str, episode_title: str, feed_url: str, guid: str, position_ms: int = 0
) -> str:
    """Both halves, as one clipboard payload: the sentence, then the link."""
    text = build_text(show_title, episode_title, position_ms)
    link = build_link(feed_url, guid, position_ms)
    return f"{text}\n{link}" if link else text


def parse_link(text: str) -> ShareTarget | None:
    """A shared link as a target, or ``None`` for anything else.

    .. warning::
       This parses somebody else's input, handed in on a command line by
       whatever opened the link. It resolves to a **feed address and a GUID and
       nothing else** -- no audio URL, no file path, no player instruction --
       and the caller must find that feed in the library the listener already
       subscribes to before playing anything. QUILL Cast must never fetch an
       arbitrary URL because a link asked it to.
    """
    # Quotes stripped because a link pasted from a chat window or handed
    # in by a shell very often arrives wrapped in them.
    raw = (text or "").strip().strip('"').strip("'")
    if not raw.lower().startswith(f"{_PREFIX}?"):
        return None
    query = urllib.parse.parse_qs(raw.split("?", 1)[1])
    feed = (query.get("feed") or [""])[0].strip()
    guid = (query.get("guid") or [""])[0].strip()
    if not feed or not guid:
        return None
    if not feed.lower().startswith(("http://", "https://")):
        # A feed address is a web address. Anything else in that slot is
        # somebody trying something.
        return None
    try:
        seconds = max(0, int((query.get("t") or ["0"])[0]))
    except ValueError:
        seconds = 0
    return ShareTarget(feed_url=feed, guid=guid, position_ms=seconds * 1000)
