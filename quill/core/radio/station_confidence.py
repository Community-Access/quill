"""How much a station row can promise, in the row itself.

WHY THIS EXISTS
---------------
A results list said what a station was called, where it was from, and which
directory listed it. It said nothing about whether the thing would actually
play, so every row made the same silent promise and a listener found out which
ones were lying by pressing Enter on each in turn. That is the same shape as
the audio-track menu described in the release notes -- a puzzle offered in
place of an answer.

WHERE THE ANSWER COMES FROM, AND WHY IT IS NOT INVENTED
-------------------------------------------------------
Radio Browser runs its own checker against every stream it lists and publishes
the verdict as ``lastcheckok``. Quill Radio was downloading that field on every
search and throwing it away. So this is not a measurement this app makes, a
guess, or a heuristic over bitrate and votes -- it is the directory's own
answer to the only question that matters, finally read.

That provenance is the whole design constraint. Nothing here scores, ranks, or
estimates: a station is reported as unplayable only when the directory that
lists it says it could not play it, and every other case either says what it
knows or says nothing.

WHY MOST ROWS STAY SILENT
-------------------------
Only Radio Browser publishes a check. Marking the rest "unknown" would put a
badge on almost every row in the app to convey precisely no information, and a
list where every row carries the same word is a list that has been made longer
without being made more useful. The rule is the one the missing-media notice
already follows: **a healthy row says nothing at all.**

So a badge appears in exactly two cases:

* the directory's own check **failed** -- the one fact worth interrupting a
  listener for, because it turns a wasted Enter into an informed choice;
* the row **cannot be played directly** and needs a lookup first (TuneIn,
  YouTube), which is not a fault but does explain why Enter takes a moment.

The details panel has room for sentences, so it says more -- including the
good news and the "nobody has checked" case, which are worth having somewhere
even though they are not worth a badge.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The directory checked this stream and it played.
WORKING = "working"
#: The directory checked this stream and it did not play.
FAILED = "failed"
#: Playable, but the address has to be worked out first (TuneIn, YouTube).
NEEDS_LOOKUP = "needs_lookup"
#: Nobody has published a check for this row. The common case outside Radio
#: Browser, and deliberately not treated as bad news.
UNKNOWN = "unknown"

#: Sources whose rows carry a page address rather than a stream, so the real
#: address is resolved at the moment you press Enter. Kept as a set of source
#: labels because that is what a row actually carries; ``RadioStation.source``
#: is the same string the Source facet filters on.
_LOOKUP_SOURCES = frozenset({"TuneIn", "YouTube"})

#: What a badge adds to the row label. Short, because it rides a line a screen
#: reader already reads in full, and worded as a statement about the *check*
#: rather than about the station -- the directory's verdict can be out of date,
#: and "may not be playable" claims exactly as much as the evidence supports.
_BADGES: dict[str, str] = {
    FAILED: "may not be playable",
    NEEDS_LOOKUP: "resolved when you play it",
}

#: The details-panel sentence for each verdict, including the two that stay out
#: of the row.
_EXPLANATIONS: dict[str, str] = {
    WORKING: "Radio Browser's own check played this stream successfully.",
    FAILED: (
        "Radio Browser's own check could not play this stream last time it "
        "tried. It may be off the air, or it may have moved."
    ),
    NEEDS_LOOKUP: (
        "This row holds a page address rather than a stream, so the stream is "
        "worked out when you press Enter. That is why it takes a moment."
    ),
    UNKNOWN: "No directory has published a check for this station.",
}


@dataclass(frozen=True, slots=True)
class StationConfidence:
    """One row's verdict, plus the words for it."""

    verdict: str

    @property
    def badge(self) -> str:
        """The row suffix, or ``""`` when this row should stay silent."""
        return _BADGES.get(self.verdict, "")

    @property
    def explanation(self) -> str:
        """The details-panel sentence, or ``""`` when there is nothing to say."""
        return _EXPLANATIONS.get(self.verdict, "")


def assess(station: object) -> StationConfidence:
    """The verdict for *station*, read from what its directory published.

    Takes a duck-typed object rather than importing ``RadioStation`` so that a
    favorite, a search result and a test's stand-in are all assessable without
    this module caring which is which.

    Order matters. A failed check outranks needing a lookup, because "this will
    probably not play" is more use than "this takes a moment to start" and a
    row has room for one badge.
    """
    ok = getattr(station, "last_check_ok", None)
    if ok is False:
        return StationConfidence(FAILED)
    source = str(getattr(station, "source", "") or "")
    if source in _LOOKUP_SOURCES:
        return StationConfidence(NEEDS_LOOKUP)
    if ok is True:
        return StationConfidence(WORKING)
    return StationConfidence(UNKNOWN)


def label_with_confidence(label: str, station: object) -> str:
    """*label* with a badge appended when the row has one to carry.

    The badge goes last, after the name and country, because a screen reader
    reads the row start to finish and the station's own name is what somebody
    is listening for -- a row that opened with "may not be playable" would make
    every list harder to scan in exchange for a caveat about one row in it.
    """
    badge = assess(station).badge
    return f"{label} -- {badge}" if badge else label
