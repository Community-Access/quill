"""Radio Paradise: seven hand-curated channels, each at every quality it offers.

Radio Paradise is listener-supported, DJ-curated, ad-free internet radio, and it
is one of the few stations that publishes a **lossless** stream. Quill Radio has
carried it since 2.1 only as an entry in :mod:`quill.core.radio.networks` -- a
Radio Browser *name query*, which returns whatever a stranger happened to
register there, at whatever bitrate they registered, with no way to ask for
anything else. This module replaces the guess with the station's own answer.

Two public facts make it cheap:

* ``api.radioparadise.com/api/list_chan?list_type=json`` lists every channel --
  its slug, its title, and ``current_listeners`` -- keyless, in one 8 KB GET.
* The stream addresses are a fixed, stable naming pattern on
  ``stream.radioparadise.com``. The list API does **not** return them (its
  ``stream`` object is for the now-playing widget and its ``stream_url`` is
  always empty), so the pattern below was verified station by station against
  the live server rather than copied from anyone: every URL this module can
  build was requested, answered 200, and named itself in its own ``icy-name``
  header.

So each channel becomes **six rows, one per quality**, from 32 kbps AAC+ for a
metered connection to lossless FLAC -- which nothing else in the browse tree
offers. That is the whole point of doing this properly: the bitrate is the
listener's choice to make, and it is a choice that a name-search integration
can never offer.

One HTTPS GET to a single reviewed egress site (:func:`_fetch` -- see
``quill/tools/network_egress_audit.py``), HTTPS-only over a verified TLS context
with a bounded timeout and size cap, reached only by an explicit browse, search
or refresh, and refused in Safe Mode via :func:`refuse_in_safe_mode`. The
channel list is cached (:mod:`quill.core.radio.directory_cache`) because seven
channels change about once a decade; the listener counts inside it are the one
thing that goes stale, which is why the cache is hours rather than days.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

_LIST_URL = "https://api.radioparadise.com/api/list_chan?list_type=json"
_STREAM_BASE = "https://stream.radioparadise.com/"
_TIMEOUT_SECONDS = 15.0
#: The list is ~8 KB. A megabyte is absurdly generous and still catches a
#: redirect to something that is not the API at all.
_MAX_BYTES = 1_000_000
_USER_AGENT: str | None = None

CATEGORY_LABEL = "Radio Paradise"
#: Spoken/shown attribution. It names the quality expansion because a listener
#: seeing 42 rows for 7 channels should know why.
CATALOG_CREDIT = "Radio Paradise's own channel list, every channel at every quality"

#: Cached for six hours. The channel list itself is effectively permanent; the
#: listener counts travel with it and are the reason not to cache it for a day.
_CACHE_KEY = "radioparadise:channels"
_CACHE_MAX_AGE_SECONDS = 6 * 60 * 60

#: One offered quality: the label a listener reads, the URL suffix, the codec,
#: and the bitrate (0 for FLAC, which is variable -- ``details_text`` then says
#: "Format: FLAC" rather than inventing a number).
#:
#: **Order matters and is deliberate.** These render top to bottom under each
#: channel, so the first row is what Enter lands on: 320k AAC, the best lossy
#: stream, which is the right default on an ordinary connection. The cheap rows
#: and the lossless row are each one arrow key away -- FLAC last because it is
#: the specialist choice and by far the heaviest, not because it is the worst.
QUALITIES: tuple[tuple[str, str, str, int], ...] = (
    ("320k AAC", "320", "AAC", 320),
    ("192k MP3", "192", "MP3", 192),
    ("128k AAC", "128", "AAC", 128),
    ("64k AAC+", "64", "AAC", 64),
    ("32k AAC+", "32", "AAC", 32),
    ("FLAC (lossless)", "flac", "FLAC", 0),
)

#: The Main Mix (``chan`` 0) does not use its slug in stream names; it uses the
#: codec directly. Verified against the live server.
_MAIN_PATHS: dict[str, str] = {
    "320": "aac-320",
    "192": "mp3-192",
    "128": "aac-128",
    "64": "aac-64",
    "32": "aac-32",
    "flac": "flacm",
}

#: Serenity offers only two of the six, under names that break the pattern in
#: both directions: the bare slug is its 64k stream, and its lossless one is
#: ``-flac`` rather than ``-flacm``.
_SERENITY_PATHS: dict[str, str] = {"64": "serenity", "flac": "serenity-flac"}

#: Radio 2050 is a real channel that ``list_chan`` omits. Adding it here is a
#: judgement call recorded rather than hidden: it answers on every quality
#: suffix, so leaving it out would mean the directory's own gap silently became
#: Quill Radio's. It carries no listener count because the API never mentions
#: it.
_EXTRA_CHANNELS: tuple[tuple[str, str], ...] = (("radio2050", "Radio 2050"),)


class RadioParadiseError(CodedError):
    """A Radio Paradise request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-RADIOPARADISE-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`RadioParadiseError` when Safe Mode is active."""
    if safe_mode:
        raise RadioParadiseError(
            "Radio Paradise is disabled in Safe Mode. Restart QUILL normally to browse it."
        )


# --- pure helpers -----------------------------------------------------------


def stream_path(slug: str, quality_key: str, *, is_main: bool = False) -> str:
    """The stream-name segment for one channel at one quality (pure), or ``""``.

    ``""`` means "this channel does not offer this quality", which is only ever
    Serenity -- and returning it rather than a plausible-looking URL is the
    whole point: a row that 404s at play time is worse than a row that is not
    offered.
    """
    if is_main:
        return _MAIN_PATHS.get(quality_key, "")
    if slug == "serenity":
        return _SERENITY_PATHS.get(quality_key, "")
    if quality_key == "flac":
        return f"{slug}-flacm"
    return f"{slug}-{quality_key}"


def qualities_in_order(preferred: str = "") -> tuple[tuple[str, str, str, int], ...]:
    """:data:`QUALITIES` with *preferred* moved to the front (pure).

    The order decides which row Enter lands on, and which quality that should
    be is a property of the listener's connection rather than of the station --
    so it is a declared option (``source_options.RADIO_PARADISE_QUALITY``) and
    this is where it is spent. Every other quality is still listed, one arrow
    key away; nothing is hidden by choosing.
    """
    wanted = str(preferred or "").strip()
    if not wanted:
        return QUALITIES
    first = [entry for entry in QUALITIES if entry[1] == wanted]
    return (*first, *(entry for entry in QUALITIES if entry[1] != wanted)) if first else QUALITIES


def channel_stations(
    slug: str,
    title: str,
    *,
    listeners: int = 0,
    is_main: bool = False,
    preferred_quality: str = "",
) -> list[RadioStation]:
    """One channel as a row per quality it actually offers (pure)."""
    rows: list[RadioStation] = []
    for label, key, codec, bitrate in qualities_in_order(preferred_quality):
        path = stream_path(slug, key, is_main=is_main)
        if not path:
            continue
        rows.append(
            RadioStation(
                name=f"{title} ({label})",
                stream_url=f"{_STREAM_BASE}{path}",
                # Radio Paradise is not in Radio Browser's namespace, and
                # station_uuid is: radio_browser.register_click() posts whatever
                # is in this field to Radio Browser's click endpoint.
                station_uuid="",
                homepage="https://radioparadise.com/",
                tags=(CATEGORY_LABEL,),
                codec=codec,
                bitrate_kbps=bitrate,
                listeners=listeners,
                source=CATEGORY_LABEL,
            )
        )
    return rows


def _as_int(value: Any) -> int:
    """``current_listeners`` arrives as a *string* (``"6623"``). Be tolerant."""
    try:
        return max(0, int(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def parse_channels(payload: str, *, preferred_quality: str = "") -> list[RadioStation]:
    """Every channel × every quality, from a ``list_chan`` response (pure).

    Tolerant by design: a channel missing a slug is skipped, a payload that is
    not a JSON list yields ``[]``, and the extra channels are appended whatever
    happened -- a directory shape change should cost the rows it broke, not the
    ones it did not.
    """
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        data = []
    rows: list[RadioStation] = []
    seen: set[str] = set()
    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            slug = str(entry.get("slug") or entry.get("stream_name") or "").strip()
            if not slug or slug in seen:
                continue
            seen.add(slug)
            title = str(entry.get("title") or slug).strip()
            rows.extend(
                channel_stations(
                    slug,
                    title,
                    listeners=_as_int(entry.get("current_listeners")),
                    is_main=str(entry.get("chan", "")).strip() == "0",
                    preferred_quality=preferred_quality,
                )
            )
    for slug, title in _EXTRA_CHANNELS:
        if slug not in seen:
            rows.extend(channel_stations(slug, title, preferred_quality=preferred_quality))
    return rows


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(url: str) -> str:
    """One HTTPS GET of Radio Paradise's public channel list -- the reviewed
    egress site.

    Reads one byte past the cap so an over-long reply is **detected** rather
    than handed to :func:`json.loads` as a truncated document, which would fail
    with a parse error naming a column number instead of the real cause.
    """
    if not url.startswith("https://"):
        raise RadioParadiseError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise RadioParadiseError(f"Could not reach Radio Paradise: {error}") from error
    if len(payload) > _MAX_BYTES:
        raise RadioParadiseError(
            f"The Radio Paradise channel list is larger than {_MAX_BYTES} bytes, "
            "so it was not read."
        )
    return payload.decode("utf-8", errors="replace")


def fetch_stations(*, safe_mode: bool = False, refresh: bool = False) -> list[RadioStation]:
    """Every Radio Paradise channel, at every quality, most recently cached.

    A fetch that fails falls back to the cached list rather than blanking the
    branch (:func:`directory_cache.resolve`); the listener counts in a stale
    entry are simply old, which is a smaller lie than an empty station list.
    """
    stations, _age = fetch_stations_with_age(safe_mode=safe_mode, refresh=refresh)
    return stations


def fetch_stations_with_age(
    *, safe_mode: bool = False, refresh: bool = False
) -> tuple[list[RadioStation], float | None]:
    """:func:`fetch_stations`, plus how old the answer is in seconds.

    ``None`` means it was fetched live. The age matters more here than for most
    catalogs because the rows carry live listener counts: saying "as of two
    hours ago" is the difference between a cache and a quiet lie.
    """
    refuse_in_safe_mode(safe_mode)
    payload, age = directory_cache.resolve(
        _CACHE_KEY,
        lambda: _fetch(_LIST_URL),
        max_age_seconds=_CACHE_MAX_AGE_SECONDS,
        refresh=refresh,
        empty="",
    )
    from quill.core.radio import source_options

    return parse_channels(
        str(payload or ""),
        preferred_quality=source_options.chosen(source_options.RADIO_PARADISE_QUALITY.key),
    ), age


def search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Channels whose name matches *query* (case-insensitive substring).

    An empty query returns everything, which is what the browse branch wants;
    Find Stations passes a real query and gets the handful that match. Never
    raises into a search fan-out: a directory that is down contributes nothing.
    """
    try:
        rows = fetch_stations(safe_mode=safe_mode)
    except RadioParadiseError:
        return []
    wanted = str(query or "").strip().casefold()
    if not wanted:
        return rows
    if wanted in CATEGORY_LABEL.casefold():
        return rows
    return [row for row in rows if wanted in row.name.casefold()]
