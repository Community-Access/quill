"""NFB-NEWSLINE Radio Network (NFBRN): the National Federation of the Blind's
public speech/talk stream, offered as a small bundled, always-available Browse
Stations category -- the sibling of ``core/radio/acb_media.py``.

Like ACB Media, this is a static, bundled entry (no network call to see it),
because QUILL's mission overlaps directly with the NFB's here and the stream is
a single long-lived mount. Sourced from the NFB's published NFBRN stream
(``cast.az-streamingserver.com:8590/live``; ``/stream`` is a known alternate
mount used by other directories, kept here only as a comment for reference --
the player's own stream-recovery covers a mount going briefly down). If the
stream address ever changes, refresh this by hand. wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.radio.models import RadioStation

CATEGORY_LABEL = "NFB Radio"

#: NFBRN's primary MP3 mount. ``.../8590/stream`` is a documented alternate.
_NFBRN_STREAM_URL = "http://cast.az-streamingserver.com:8590/live"
_NFBRN_HOMEPAGE = "https://nfb.org/resources/publications-and-media/nfbrn"


def nfb_media_stations() -> list[RadioStation]:
    """The NFB Radio Network station (a one-entry list, mirroring ACB Media)."""
    return [
        RadioStation(
            name="NFBRN -- National Federation of the Blind Radio Network",
            stream_url=_NFBRN_STREAM_URL,
            station_uuid="",
            homepage=_NFBRN_HOMEPAGE,
            country="United States",
            language="English",
            tags=(CATEGORY_LABEL, "Speech", "Talk"),
            codec="MP3",
            source=CATEGORY_LABEL,
        )
    ]
