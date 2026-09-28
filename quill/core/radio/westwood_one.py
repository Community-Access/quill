"""Westwood One Sports: the network's own live event channels, in Browse.

Westwood One (Cumulus Media's network division) carries national sports --
the NFL, the NCAA tournaments, the Masters, US Soccer -- to its affiliate
stations. On the internet it streams its events itself, through a Triton Digital
player on westwoodonesports.com; during a big event such as the NCAA
tournament that is several games at once, each on its own channel.

Those channels are StreamTheWorld mounts ``WWODEN1`` to ``WWODEN10``, found
2026-09-28 from the site's own player (``player.listenlive.co/65791``, whose
callsign is ``WWODEN1``) and then by asking Triton's public provisioning service
for each number: one to ten answer, eleven and beyond do not, and no other
Westwood One mount name does. That is every stream Westwood One publishes; its
syndicated shows reach listeners through affiliate stations, which the Networks
branch already finds.

**Stable addresses, not servers.** Each channel is StreamTheWorld's
``livestream-redirect`` URL, which always sends the player to whichever server
is carrying the mount today -- so a channel never goes stale the way a copied
``https://12345.live.streamtheworld.com/...`` address does. The MP3 mount is
used because every channel has one and every engine plays it.

**What is on.** A channel carries a game while one is on and is usually silent
or looping otherwise; the site's schedule says which game is on which channel.
Rights can keep a game off the internet, in which case the channel says so.

Bundled and static like ACB Media and NFB Radio: seeing the list needs no
network. wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.radio.models import RadioStation

__all__ = ["CATEGORY_LABEL", "CHANNELS", "westwood_one_stations"]

CATEGORY_LABEL = "Westwood One Sports"

#: How many event channels Westwood One publishes (``WWODEN1`` .. ``WWODEN10``).
CHANNELS = 10

_HOMEPAGE = "https://www.westwoodonesports.com/"
_REDIRECT = "https://playerservices.streamtheworld.com/api/livestream-redirect/{mount}.mp3"
_NOTES = (
    "Westwood One's own live event channel {n} of {total}. During big events -- "
    "the NCAA tournaments, the NFL, the Masters -- each channel carries a "
    "different game; the schedule at westwoodonesports.com says which. Between "
    "events it may be silent."
)


def westwood_one_stations() -> list[RadioStation]:
    """The ten event channels, in order."""
    return [
        RadioStation(
            name=f"Westwood One Sports, channel {n}",
            stream_url=_REDIRECT.format(mount=f"WWODEN{n}"),
            homepage=_HOMEPAGE,
            country="United States",
            language="English",
            tags=(CATEGORY_LABEL, "Sports", "Play-by-play"),
            codec="MP3",
            source=CATEGORY_LABEL,
            notes=_NOTES.format(n=n, total=CHANNELS),
        )
        for n in range(1, CHANNELS + 1)
    ]
