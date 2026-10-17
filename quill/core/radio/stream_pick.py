"""Which of a web page's streams is *the* station: one answer, or an honest "several".

A Find-Streams scan answers with candidates. Two callers then have to decide
whether one of them is unambiguously the station -- stream recovery (#1065),
which plays it unasked, and Add Custom Station (#36), which saves it. Both used
to count candidates, and a Triton station always offers two: an MP3 mount and an
HE-AAC one (``KKSEFM`` and ``KKSEFMAAC``), each on whichever server answered.
Two *mounts* of one *station* are one answer, not a choice -- so counting them
made every Triton player "ambiguous", which is the case the resolver exists for.

So candidates are grouped by station before they are counted: a StreamTheWorld
mount by its callsign with the codec suffix removed, anything else by its own
URL. Within a station the MP3 mount wins, because every engine plays it.

:func:`durable_url` is the other half of saving one: a
``https://18233.live.streamtheworld.com/KKSEFM`` address names one server, and
servers rotate; StreamTheWorld's ``livestream-redirect/KKSEFM.mp3`` always sends
the player to whichever server carries the mount today (the form Westwood One's
channels already use, ``westwood_one.py``).

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "StreamPick",
    "durable_url",
    "is_resolved_player_mount",
    "pick_stream",
    "station_key",
]

#: A SecureNet *mount* lives on an ``ice<N>`` host. The player front-ends
#: (``radio.``, ``streamdb<N>web.``) sit on the same domain but serve pages, and
#: a player page links to itself -- so matching the domain would promote the
#: page's own links right along with the stream.
_SECURENET_MOUNT_RE = re.compile(r"^https?://ice\d+\.securenetsystems\.net/", re.IGNORECASE)

#: A StreamTheWorld server URL: ``https://<sid>.live.streamtheworld.com/<MOUNT>``.
_STW_SERVER_RE = re.compile(
    r"^https?://\d+\.live\.streamtheworld\.com(?::\d+)?/([A-Za-z0-9_]+?)(?:\.mp3)?/?$",
    re.IGNORECASE,
)
_STW_REDIRECT = "https://playerservices.streamtheworld.com/api/livestream-redirect/{mount}.mp3"

#: Codec suffixes Triton appends to a station's mount for its other encodings.
_CODEC_SUFFIX_RE = re.compile(r"(?:_?AAC|_SC)$", re.IGNORECASE)


class _Candidate(Protocol):
    @property
    def url(self) -> str: ...


@dataclass(frozen=True, slots=True)
class StreamPick:
    """The verdict on a page's candidates.

    ``url`` is set when one station was found; ``stations`` names each distinct
    station when there were several; both are empty when there was nothing.
    """

    url: str = ""
    stations: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return bool(self.url)


def _is_stw_host(url: str) -> bool:
    """True when *url*'s host is streamtheworld.com or one of its subdomains --
    matched on the parsed host at a dot boundary, so a look-alike such as
    ``evilstreamtheworld.com`` or ``example.com/?streamtheworld.com`` is not."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host == "streamtheworld.com" or host.endswith(".streamtheworld.com")


def is_resolved_player_mount(url: str) -> bool:
    """True when *url* **is** a page's own resolved stream rather than a guess
    taken off it: a Triton/StreamTheWorld mount, or a SecureNet ice mount."""
    return _is_stw_host(url) or bool(_SECURENET_MOUNT_RE.match(url))


def _stw_mount(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if not _is_stw_host(url):
        return ""
    last = parsed.path.strip("/").rsplit("/", 1)[-1]
    stem, dot, ext = last.rpartition(".")
    return stem if dot and ext.lower() in ("mp3", "aac", "m3u8", "pls") else last


def station_key(url: str) -> str:
    """What makes two candidate URLs the same station (pure).

    ``KKSEFM`` and ``KKSEFMAAC`` on any two servers are one station; anything
    that is not a StreamTheWorld mount is only itself.
    """
    mount = _stw_mount(url)
    if mount:
        return "stw:" + _CODEC_SUFFIX_RE.sub("", mount.upper())
    return url


def _label(key: str) -> str:
    return key[4:] if key.startswith("stw:") else key


def _is_aac_mount(url: str) -> bool:
    mount = _stw_mount(url)
    return bool(mount) and mount.upper().endswith("AAC")


def pick_stream(candidates: Sequence[_Candidate]) -> StreamPick:
    """One station's stream from *candidates*, or the stations to choose from.

    Resolved player mounts outrank everything else on the page -- they are the
    stream the page itself advertises, not one of its links that merely looks
    like audio. When there are none, one candidate is an answer and two are a
    choice. Within the chosen station the MP3 mount wins.
    """
    resolved = [c for c in candidates if is_resolved_player_mount(c.url)]
    pool = resolved or list(candidates)
    groups: dict[str, list[_Candidate]] = {}
    for candidate in pool:
        groups.setdefault(station_key(candidate.url), []).append(candidate)
    if len(groups) != 1:
        return StreamPick(stations=tuple(_label(key) for key in groups))
    members = next(iter(groups.values()))
    preferred = [c for c in members if not _is_aac_mount(c.url)] or members
    return StreamPick(url=preferred[0].url)


def durable_url(url: str) -> str:
    """The lasting address for a StreamTheWorld server URL; anything else as-is.

    Only the MP3 mount is rewritten: the redirect names its format, and MP3 is
    the one every station has and every engine plays.
    """
    match = _STW_SERVER_RE.match(url.strip())
    if not match or match.group(1).upper().endswith("AAC"):
        return url
    return _STW_REDIRECT.format(mount=match.group(1))
