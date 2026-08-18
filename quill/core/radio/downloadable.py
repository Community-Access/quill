"""May this be saved to a file? The rights question, answered in one place.

Quill Radio plays a lot of different things, and only some of them are yours to
keep. A LibriVox chapter is public domain and downloading it is the point. A live
station is a broadcast in progress -- there is no file to save, and "download"
means nothing. A Spotify episode is copy-protected and always will be. Between
those sit the interesting cases, and getting one of them wrong means QUILL
writing somebody a file it had no right to write.

So the decision is made **here**, once, from a table anybody can read, rather
than in a menu handler where it would be a condition nobody can find.

Three rules the table follows:

* **Live is never downloadable**, and not because of rights -- a broadcast has no
  end, so there is no file. That is what *Record Station* is for, and the refusal
  says so rather than leaving somebody to wonder which command they wanted.
* **A source must be affirmatively allowed.** An unknown source is refused. The
  Internet Archive's own guidance puts it best and it is the rule here generally:
  never assume a downloadable-looking file may be redistributed.
* **A refusal always says why**, in words, because "Download" simply missing
  from a menu is indistinguishable from a bug -- and the four reasons a thing
  cannot be saved are genuinely different facts.

wx-free, strict-typed, pure. Nothing here touches the network or a disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: Sources whose bounded media QUILL may save. Each is here for a stated reason,
#: and adding one is a rights decision rather than a convenience.
ALLOWED_SOURCES: dict[str, str] = {
    # Public domain by construction; the whole project exists to be copied.
    "LibriVox": "public domain",
    "Project Gutenberg": "public domain",
    # The browse tree only ever surfaces rights-safe collections, and the book
    # side additionally requires an explicit open licence per item.
    "Internet Archive": "public domain or openly licensed",
    # Creative Commons, and the licence travels with the file (see `licence_note`).
    "ccMixter": "Creative Commons, licence shown on the row",
    # A podcast enclosure is the publisher's own file, offered for download by
    # every podcast client there has ever been. This is the normal case. The
    # same episode reaches the menu under different source names depending on
    # where it was found -- search results, the browse tree's Podcasts branch,
    # and Subscriptions each stamp their own -- and every one of them must be
    # here, or Download silently vanishes from that surface (reported
    # 2026-08-18: no Download on a subscription episode row).
    "Podcasts (Apple)": "the publisher's own episode file",
    "Podcast": "the publisher's own episode file",
    "Apple Podcasts": "the publisher's own episode file",
    "Subscribed Podcasts": "the publisher's own episode file",
}

#: Sources that are refused with a specific sentence rather than the generic one.
#: Each of these looks downloadable and is not, which is exactly when a person
#: deserves the real reason.
REFUSED_SOURCES: dict[str, str] = {
    "Spotify": (
        "Spotify audio is copy-protected and cannot be saved by any app, including this one."
    ),
    "Mixcloud": (
        "Quill Radio never takes a stream from Mixcloud -- the row is the show's "
        "page. Open it in your browser to see what Mixcloud itself offers."
    ),
    "YouTube": (
        "Quill Radio deliberately does not download from YouTube. It plays and "
        "records audio; saving the file is not something this app does."
    ),
    "Audius": (
        "Audius tracks are offered here for listening. Whether a track may be "
        "downloaded is the artist's choice and is not something Quill Radio can "
        "tell from the listing, so it does not guess."
    ),
}

#: What to say when a live station is asked to be downloaded. Names the command
#: that *is* the answer, because wanting to keep a broadcast is a reasonable
#: thing to want and Record Station is how it is done.
LIVE_REASON = (
    "A live station is playing now and has no end, so there is no file to save. "
    "Use Record Station to capture it as it goes out."
)

#: And when the source is simply not on the list.
UNKNOWN_REASON = (
    "Quill Radio does not know that this may be saved, so it does not save it. "
    "Only sources whose terms clearly allow it are offered for download."
)

_UNSAFE_NAME = re.compile(r"[^\w\-. ]+")


@dataclass(frozen=True, slots=True)
class Decision:
    """Whether a row may be saved, and the sentence to say when it may not."""

    allowed: bool
    reason: str = ""
    #: Why it *is* allowed, for the confirmation ("public domain").
    basis: str = ""

    def __bool__(self) -> bool:
        return self.allowed


def _source_of(station: Any) -> str:
    return str(getattr(station, "source", "") or "").strip()


def can_download(station: Any) -> Decision:
    """Whether *station* may be saved to a file, with the reason either way."""
    url = str(getattr(station, "stream_url", "") or "").strip()
    if not url:
        return Decision(False, UNKNOWN_REASON)

    source = _source_of(station)
    refusal = REFUSED_SOURCES.get(source)
    if refusal:
        return Decision(False, refusal)

    # Checked after the named refusals so Spotify and YouTube give their own
    # answer rather than the live one, which would be true but unhelpful.
    if not bool(getattr(station, "is_recording", False)):
        return Decision(False, LIVE_REASON)

    basis = ALLOWED_SOURCES.get(source)
    if not basis:
        return Decision(False, UNKNOWN_REASON)
    if not url.lower().startswith(("https://", "http://")):
        return Decision(False, UNKNOWN_REASON)
    return Decision(True, basis=basis)


def licence_note(station: Any) -> str:
    """The licence to record beside a saved file, when the row carries one.

    ccMixter rows carry their Creative Commons terms, and saving the audio while
    dropping the terms would strip exactly the information the licence exists to
    travel with.
    """
    tags = tuple(getattr(station, "tags", ()) or ())
    return str(tags[0]) if tags else ""


def suggested_filename(station: Any, *, url: str = "") -> str:
    """A safe file name for *station*, keeping the source's own extension.

    The station's name rather than the URL's last segment: a LibriVox chapter's
    address is a string of digits, and a folder of those is a folder nobody can
    read.
    """
    name = _UNSAFE_NAME.sub("", str(getattr(station, "name", "") or "").strip())
    name = " ".join(name.split())[:120] or "download"
    address = (url or str(getattr(station, "stream_url", "") or "")).split("?", 1)[0]
    suffix = ""
    if "." in address.rsplit("/", 1)[-1]:
        candidate = "." + address.rsplit(".", 1)[-1].lower()
        if 2 <= len(candidate) <= 6 and candidate[1:].isalnum():
            suffix = candidate
    return f"{name}{suffix or '.mp3'}"


def describe(decision: Decision, station: Any) -> str:
    """What to say when somebody asks to download *station*."""
    if not decision.allowed:
        return decision.reason
    name = str(getattr(station, "name", "") or "this")
    basis = f" ({decision.basis})" if decision.basis else ""
    return f"Downloading {name}{basis}."
