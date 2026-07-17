"""Parse and format the "What's Playing" track announcement.

A stream's ICY ``StreamTitle`` (see :mod:`quill.core.radio.icy`) is supposed to
be a short "Artist - Title" string, and for most stations it is. But broadcast
automation systems (RCS/GSelector, iHeart, and other US commercial stations)
stuff a pile of key/value pairs in there instead, so a listener who asks
"what's playing?" hears the raw mess reported in issue #1068::

    title="YOUR SONG",artist="Elton John",url="song_spot="F" MediaBaseId="0"
    itunesTrackId="0" amgTrackId="-1" amgArtistId="0" TAID="0" TPID="638642"

This module turns that back into what a person actually wanted to hear -- the
title and the artist -- and lets them decide exactly how it is spoken with a
small, friendly token template.

Two pure steps:

* :func:`parse_now_playing` recognises the ``key="value"`` broadcast form
  (pulling ``title``/``artist`` out of the noise) and the plain
  "Artist - Title" convention, and degrades to "the whole string is the title"
  for anything else. It never raises.
* :func:`format_now_playing` renders a :class:`NowPlaying` through a template
  of ``{title}`` / ``{artist}`` / ``{raw}`` tokens, with ``[...]`` marking an
  *optional segment* that vanishes when a token inside it is empty -- so the
  default ``{title}[ by {artist}]`` reads "YOUR SONG by Elton John" when both
  are known and simply "YOUR SONG" when the stream only gives a title, with no
  dangling "by". :func:`render_now_playing` does both in one call.

wx-free, strict-typed. The announcement's "Now playing: " spoken prefix stays
with the announcing UI; this module owns only the track description itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Default announcement template: title, and " by <artist>" only when known.
DEFAULT_TEMPLATE = "{title}[ by {artist}]"

#: The tokens a template may use, with a one-line description for help text.
TEMPLATE_TOKENS: tuple[tuple[str, str], ...] = (
    ("{title}", "the song or programme title"),
    ("{artist}", "the artist or performer"),
    ("{raw}", "the stream's exact original text, unparsed"),
)

#: ``key="value"`` pairs, the shape broadcast automation packs into StreamTitle.
_KEY_VALUE_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
#: Alternative key spellings various encoders use for the same two fields.
_TITLE_KEYS = ("title", "song", "cut", "streamtitle")
_ARTIST_KEYS = ("artist", "artists", "performer", "author")
#: Optional ``[...]`` template segment, dropped whole when a token inside is
#: empty. Non-greedy so several segments in one template stay independent.
_OPTIONAL_SEGMENT_RE = re.compile(r"\[([^\[\]]*)\]")
_TOKEN_RE = re.compile(r"\{(\w+)\}")


@dataclass(slots=True)
class NowPlaying:
    """The pieces of a track announcement parsed from a stream title."""

    #: The song/programme title (best-effort; may equal the whole raw string).
    title: str = ""
    #: The artist/performer, when the stream provides one separately.
    artist: str = ""
    #: The exact original ``StreamTitle`` text, always preserved for ``{raw}``.
    raw: str = ""
    #: Every other ``key="value"`` field found in a structured title, kept so a
    #: future template could expose album/etc. without another parse.
    extras: dict[str, str] = field(default_factory=dict)


def parse_now_playing(stream_title: str) -> NowPlaying:
    """Parse a raw ICY ``StreamTitle`` into title/artist fields (pure).

    Recognises, in order: the ``key="value"`` broadcast-automation form (issue
    #1068), the plain ``Artist - Title`` convention, and -- failing both -- a
    bare string taken as the title. Never raises; an empty input yields an
    empty :class:`NowPlaying`.
    """
    raw = stream_title.strip()
    if not raw:
        return NowPlaying()

    pairs = _KEY_VALUE_RE.findall(raw)
    if pairs and any(key.lower() in (*_TITLE_KEYS, *_ARTIST_KEYS) for key, _ in pairs):
        fields = {key.lower(): value.strip() for key, value in pairs}
        title = _first_present(fields, _TITLE_KEYS)
        artist = _first_present(fields, _ARTIST_KEYS)
        consumed = {*_TITLE_KEYS, *_ARTIST_KEYS}
        extras = {k: v for k, v in fields.items() if k not in consumed and v}
        # A structured title with neither a title nor artist value is useless
        # noise; fall through to treating the whole string as the title.
        if title or artist:
            return NowPlaying(title=title, artist=artist, raw=raw, extras=extras)

    # Plain "Artist - Title" convention (the ICY norm). Split on the first
    # spaced hyphen only, so a title like "9 to 5 - Live" keeps its own hyphen.
    if " - " in raw:
        artist_part, title_part = raw.split(" - ", 1)
        artist_part = artist_part.strip()
        title_part = title_part.strip()
        if artist_part and title_part:
            return NowPlaying(title=title_part, artist=artist_part, raw=raw)

    return NowPlaying(title=raw, raw=raw)


def format_now_playing(now_playing: NowPlaying, template: str = DEFAULT_TEMPLATE) -> str:
    """Render *now_playing* through *template* (pure).

    ``{title}``/``{artist}``/``{raw}`` are substituted; a ``[...]`` segment is
    kept only when every token inside it resolves to a non-empty value, so
    ``{title}[ by {artist}]`` never leaves a dangling "by". An unknown token is
    left as-is (so a typo is visible, not silently eaten). Falls back to the
    title (or the raw string) if the template renders empty -- the listener
    always hears *something* when a title exists.
    """
    values = {
        "title": now_playing.title,
        "artist": now_playing.artist,
        "raw": now_playing.raw,
        **now_playing.extras,
    }

    def _render_segment(segment: str) -> str:
        # Drop this optional segment if any token in it is empty/unknown.
        for token in _TOKEN_RE.findall(segment):
            if not values.get(token, ""):
                return ""
        return _substitute(segment, values)

    rendered = _OPTIONAL_SEGMENT_RE.sub(lambda m: _render_segment(m.group(1)), template)
    rendered = _substitute(rendered, values)
    rendered = _collapse_whitespace(rendered)
    if rendered:
        return rendered
    return now_playing.title or now_playing.raw


def render_now_playing(stream_title: str, template: str = DEFAULT_TEMPLATE) -> str:
    """Parse *stream_title* and format it in one call (pure convenience)."""
    return format_now_playing(parse_now_playing(stream_title), template)


def _first_present(fields: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = fields.get(key, "")
        if value:
            return value
    return ""


def _substitute(text: str, values: dict[str, str]) -> str:
    return _TOKEN_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
