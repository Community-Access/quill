"""Which transcript to take when a feed offers several (list.md 2.6).

A Podcasting 2.0 feed may carry more than one ``<podcast:transcript>`` for the
same episode -- the same words in JSON, WebVTT, SRT and HTML. QUILL took the
**first tag it matched**, whatever its type, which means the choice belonged to
whoever wrote the feed's element order.

That is not a cosmetic difference. Only the structured formats carry **cue
times**:

* the timed transcript reader follows along with playback, and cannot without
  them;
* the chapter cascade's transcript tier infers chapters from timings;
* Markdown export writes timestamps beside speakers.

So a publisher who happened to list HTML first silently cost their listeners
all three, on every episode, with no error anywhere. Earshot hit exactly this
and named Buzzsprout as the provider that surfaced it.

**The order is by what the format can do, not by preference.** JSON carries
speakers and timings and is unambiguous to parse; WebVTT carries timings and
usually speakers; SRT carries timings; HTML carries the words. Anything
unrecognised sorts last but is still kept -- a feed that grows a format nobody
anticipated should degrade to "the words", never to nothing.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

#: Best first. The rank is the format's *capability*, so a reader that needs
#: timings gets them whenever the feed has them at all.
_RANK: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("json", ("application/json", "json")),
    ("vtt", ("text/vtt", "vtt", "webvtt")),
    ("srt", ("application/x-subrip", "srt", "subrip")),
    ("html", ("text/html", "html", "xhtml")),
    ("text", ("text/plain", "plain", "txt")),
)

#: What an unrecognised type scores. Below everything named, above nothing:
#: an unknown format is still a transcript, and refusing it would lose the
#: words to protect the timings.
_UNKNOWN = len(_RANK)


def rank(transcript_type: object, url: object = "") -> int:
    """How good this representation is, lower being better (pure).

    The declared ``type`` decides it. When a feed gives none -- which is legal
    and common -- the URL's extension is the fallback, because a publisher who
    omitted the attribute still named the file.
    """
    declared = str(transcript_type or "").strip().lower()
    for index, (_name, tokens) in enumerate(_RANK):
        if any(token in declared for token in tokens):
            return index
    tail = str(url or "").strip().lower().split("?", 1)[0].rsplit(".", 1)
    suffix = tail[-1] if len(tail) == 2 else ""
    for index, (name, _tokens) in enumerate(_RANK):
        if suffix == name or (name == "vtt" and suffix == "webvtt"):
            return index
    return _UNKNOWN


def best(candidates: list[tuple[str, str]]) -> tuple[str, str]:
    """The best ``(url, type)`` of those offered, or two empty strings.

    Ties keep feed order, which is the publisher's own preference among
    equals -- the sort is stable and that is deliberate. A candidate with no
    URL is dropped: a type with nothing to fetch is not a representation.
    """
    real = [(url, kind) for url, kind in candidates if str(url or "").strip()]
    if not real:
        return ("", "")
    return min(real, key=lambda pair: rank(pair[1], pair[0]))


def carries_timings(transcript_type: object, url: object = "") -> bool:
    """Whether this representation has cue times in it (pure).

    The question every caller that follows along with playback is really
    asking. HTML sometimes does carry them -- a ``<time>`` element, a cue-shaped
    timestamp -- but not dependably, and a "maybe" is not something the reader
    can be built on.
    """
    return rank(transcript_type, url) <= 2


__all__ = ["best", "carries_timings", "rank"]
