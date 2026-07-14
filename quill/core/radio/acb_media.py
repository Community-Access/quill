"""ACB Media: the American Council of the Blind's ten Live365 radio streams.

A small, bundled, always-available category in the station browser -- no
network call needed to see it, which matters on a slow connection or the
first run before any search has happened. QUILL's own mission overlaps
directly with ACB's here, so these are offered as a first-class, permanent
category next to RadioBrowser search results and the user's own favorites,
not just another search result.

Sourced from the American Council of the Blind's own published stream list
(cross-checked against ``link.acb.org``'s ``streams.xml`` and per-station
``.pls`` files -- all agree on these ten names, station ids, and Live365 URLs).
Static rather than fetched live: the lineup changes rarely, a bundled list
needs no egress-audit entry and never breaks if ``link.acb.org`` is briefly
down, and it sidesteps a real bug found while researching this feature (a
sibling open-source ACB player has two contradictory in-code station lists,
one of which doesn't match its own UI code's expectations). If ACB's lineup
changes, refresh this list by hand -- a live-refresh fetcher can be added
later following the same pattern as ``core/radio/radio_browser.py`` if that
becomes worth the added surface. wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.radio.models import RadioStation

#: (name, Live365 station id, homepage) -- homepage paths for 1-7 are ACB's
#: own named shows (acbradio.org); 8-10 link to the general acbmedia.org site.
_ACB_STATIONS: tuple[tuple[str, str, str], ...] = (
    ("ACB Media 1", "a11911", "https://acbradio.org/mainstream"),
    ("ACB Media 2", "a27778", "https://acbradio.org/mainstream"),
    ("ACB Media 3", "a17972", "https://acbradio.org/trove"),
    ("ACB Media 4", "a89697", "https://acbradio.org/cafe"),
    ("ACB Media 5", "a46090", "https://acbradio.org/community"),
    ("ACB Media 6", "a36240", "https://acbradio.org/live"),
    ("ACB Media 7", "a95398", "https://acbradio.org/special"),
    ("ACB Media 8", "a18975", "https://acbmedia.org"),
    ("ACB Media 9", "a44175", "https://acbmedia.org"),
    ("ACB Media 10", "a85327", "https://acbmedia.org"),
)

CATEGORY_LABEL = "ACB Media"


def acb_media_stations() -> list[RadioStation]:
    """The ten ACB Media stations, in their published numeric order."""
    return [
        RadioStation(
            name=name,
            stream_url=f"https://streaming.live365.com/{station_id}",
            station_uuid="",
            homepage=homepage,
            country="United States",
            language="English",
            tags=(CATEGORY_LABEL,),
            codec="MP3",
        )
        for name, station_id, homepage in _ACB_STATIONS
    ]
