"""Westwood One Sports: the network's ten live event channels, in Browse.

Every stream Westwood One publishes is one of ten StreamTheWorld mounts,
WWODEN1 to WWODEN10 (found 2026-09-28 from the site's own Triton player). They
are listed by StreamTheWorld's redirect address, which always reaches the
server carrying the mount today, so a channel never goes stale.
"""

from __future__ import annotations

from quill.core.radio import browse_sources, recovery, westwood_one


def test_ten_channels_in_order_by_stable_address() -> None:
    stations = westwood_one.westwood_one_stations()
    assert len(stations) == westwood_one.CHANNELS == 10
    assert [s.name for s in stations][:2] == [
        "Westwood One Sports, channel 1",
        "Westwood One Sports, channel 2",
    ]
    for n, station in enumerate(stations, start=1):
        assert station.stream_url == (
            f"https://playerservices.streamtheworld.com/api/livestream-redirect/WWODEN{n}.mp3"
        )
        assert station.source == "Westwood One Sports"
        assert station.notes


def test_a_channel_that_fails_can_be_re_resolved_by_its_mount() -> None:
    """The recovery ladder's StreamTheWorld step reads the mount from the URL."""
    url = westwood_one.westwood_one_stations()[0].stream_url
    assert recovery.streamtheworld_mount(url) == "WWODEN1"


def test_the_branch_is_in_browse_and_needs_no_network_to_list() -> None:
    assert ("westwood", "Westwood One Sports") in browse_sources.ROOT_SOURCES
    assert "westwood" in browse_sources.LOCAL_SOURCES
    nodes = browse_sources.browse("westwood", safe_mode=True)
    assert len(nodes) == 10 and not nodes[0].is_folder
