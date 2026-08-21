"""Where a now-playing title came from, and whether it is verbatim.

WHY THIS EXISTS
---------------
"What's Playing" answers with a song and an artist, and a listener has no way
to tell how much to trust it. Quill Radio reaches for a title in three quite
different places, and only tells you the answer:

* the **ICY side connection** -- a second, short connection to the stream that
  reads the ``StreamTitle`` block the station interleaves with its audio;
* the **player** -- mpv's own ``media-title`` / ``metadata`` map, which is what
  HLS stations and a few ICY hosts populate instead;
* the **station's status page** -- the Icecast/SHOUTcast status endpoint, asked
  only when the first two came back with nothing.

Those are not equally direct, and they can disagree. A status page is a
snapshot the station publishes for its own listing and can lag the audio by a
song; the ICY block is carried with the audio itself. Presenting all three as
one confident sentence is exactly the kind of unlabelled claim this app refuses
to make elsewhere -- the Popular/Trending rows say "as of 2 hours ago", an
inferred chapter list says it was worked out rather than published, and a
machine transcript says it is automatic.

THE SECOND HALF: VERBATIM VERSUS RENDERED
-----------------------------------------
What the station sends is frequently not what you are shown. Stations put a
good deal into ``StreamTitle`` -- ``text="..."``, ``song_spot="M"``, advert
markers, their own call sign -- and ``now_playing.render_now_playing`` digs the
song and artist out of it. That rendering is usually right and is not always
right, and when the shown text differs from what arrived, the listener is
entitled to see both. Hence :attr:`NowPlayingFacts.raw`, and hence the fact
that this module compares the two rather than trusting a flag somebody
remembered to set.

None of this changes what is spoken. The live announcement is unchanged; this
is what the details window can say when somebody asks.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The ICY metadata block carried alongside the audio (SHOUTcast/Icecast).
SOURCE_ICY = "icy"
#: mpv's own ``media-title`` / parsed ``metadata`` map -- what HLS provides.
SOURCE_ENGINE = "engine"
#: The station's Icecast/SHOUTcast status page, asked only as a last resort.
SOURCE_STATUS_PAGE = "status_page"
#: No title has been read yet, or the stream sends none.
SOURCE_NONE = ""

#: How each route describes itself, in the second person and without jargon.
#: "ICY" is deliberately spelled out: it is the correct name and it is also
#: three letters no listener is obliged to have met before.
_SOURCE_PHRASES: dict[str, str] = {
    SOURCE_ICY: "the station's own track metadata, carried with the audio",
    SOURCE_ENGINE: "the audio stream itself, read by the player",
    SOURCE_STATUS_PAGE: "the station's status page, which can run a song behind",
}


@dataclass(frozen=True, slots=True)
class NowPlayingFacts:
    """Everything known about the current title, including how it was learned."""

    #: What the listener is shown -- rendered, cleaned, template applied.
    shown: str = ""
    #: Exactly what arrived, before any rendering. Kept because the two differ
    #: often enough to matter and the difference is never otherwise visible.
    raw: str = ""
    #: One of the ``SOURCE_*`` constants above.
    source: str = SOURCE_NONE

    @property
    def is_verbatim(self) -> bool:
        """True when the shown text is what the station actually sent.

        Compared rather than flagged: rendering is a pure function of the raw
        text, so asking whether it changed anything is a more reliable answer
        than a boolean somebody has to remember to set at each of the three
        call sites. Whitespace-only differences do not count as a change --
        that is tidying, not interpretation.
        """
        return self.shown.strip() == self.raw.strip()

    def provenance_lines(self) -> list[str]:
        """The provenance block for the details window, or ``[]`` when silent.

        Empty when there is no title at all: a window explaining where a title
        it does not have came from is worse than one that simply does not
        mention it.
        """
        if not self.shown.strip() and not self.raw.strip():
            return []
        phrase = _SOURCE_PHRASES.get(self.source)
        lines: list[str] = []
        if phrase:
            lines.append(f"Track information from: {phrase}.")
        if not self.is_verbatim and self.raw.strip():
            # Show the original, and say plainly that the line above it is a
            # reading of this rather than a quotation of it.
            lines.append(f"The station sent: {self.raw.strip()}")
            lines.append(
                "The track shown above was read out of that, which is usually "
                "right and is not always right."
            )
        return lines


def describe_source(source: str) -> str:
    """A one-line answer to "where did this come from?", or "" for no source."""
    return _SOURCE_PHRASES.get(source, "")
