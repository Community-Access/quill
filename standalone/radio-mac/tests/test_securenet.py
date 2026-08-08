"""SecureNet Systems (Cirrus) player resolution.

Regression cover for a listener report (2026-08-07): pasting either
``https://streamdb3web.securenetsystems.net/v5/ROM`` (Radio Once More) or
``https://radio.securenetsystems.net/v5/warl`` (Radio Once More 2) into
Add Custom Station produced nothing playable. The mounts these pages advertise
are bare Icecast paths with no file extension and no ``/stream``-style hint, so
the generic shape heuristics in :mod:`quill_radio_mac.core.link_finder` discarded
them -- the ROM page yielded two unrelated links and the WARL page yielded none
at all.

The HTML below is trimmed from the real pages, keeping the shapes that matter:
the mount appears bare in one place and again with a ``playSessionID`` query.
"""

from __future__ import annotations

import pytest
from quill_radio_mac.core import securenet
from quill_radio_mac.core.link_finder import _securenet_candidates

ROM_URL = "https://streamdb3web.securenetsystems.net/v5/ROM"
ROM_HTML = """
<html><head><title>Radio Once More</title></head><body>
<script>
  var stationCallSign = "ROM";
  var streamURL = "https://ice66.securenetsystems.net/ROM";
  var trackingURL = "https://ice66.securenetsystems.net/ROM?playSessionID=8F2C-11EE-0001";
</script>
<a href="https://www.radiooncemore.com/">Station home</a>
<a href="/v5/retry/index.cfm">Having trouble?</a>
</body></html>
"""

WARL_URL = "https://radio.securenetsystems.net/v5/warl"
WARL_HTML = """
<html><head><title>Radio Once More 2</title></head><body>
<script>var streamURL = "https://ice25.securenetsystems.net/WARL";</script>
</body></html>
"""


def test_recognises_player_pages_from_either_front_end() -> None:
    assert securenet.page_is_securenet_player(ROM_URL, ROM_HTML)
    assert securenet.page_is_securenet_player(WARL_URL, WARL_HTML)


def test_recognises_a_player_embedded_on_a_station_own_domain() -> None:
    """A station embedding the Cirrus player still resolves.

    The URL is the broadcaster's own domain, so host matching cannot fire --
    the ice mount in the body is what identifies the platform.
    """
    assert securenet.page_is_securenet_player("https://www.radiooncemore.com/listen", ROM_HTML)


def test_ignores_unrelated_pages() -> None:
    assert not securenet.page_is_securenet_player("https://example.com/", "<html>hi</html>")
    # Names the platform but advertises no mount: nothing to offer.
    assert not securenet.page_is_securenet_player(
        "https://example.com/", "<p>We stream via securenetsystems.net</p>"
    )


@pytest.mark.parametrize(
    ("url", "html", "expected"),
    [
        (ROM_URL, ROM_HTML, "ROM"),
        # Linked in lowercase, but the station is WARL -- the mount's casing
        # wins over whatever the person pasting the link happened to type.
        (WARL_URL, WARL_HTML, "WARL"),
        ("https://www.radiooncemore.com/listen", ROM_HTML, "ROM"),
        # No mount on the page: fall back to the player path.
        ("https://radio.securenetsystems.net/v5/KXYZ", "<html></html>", "KXYZ"),
    ],
)
def test_callsign_from_page(url: str, html: str, expected: str) -> None:
    assert securenet.callsign_from_page(url, html) == expected


def test_extracts_the_mount_and_drops_the_session_id() -> None:
    """One saveable URL, not two, and no per-visit session id pinned into it."""
    assert securenet.stream_urls_from_page(ROM_HTML) == ["https://ice66.securenetsystems.net/ROM"]


def test_server_number_is_read_not_computed() -> None:
    """ROM is on ice66 and WARL on ice25 -- the number cannot be derived."""
    assert securenet.stream_urls_from_page(WARL_HTML) == ["https://ice25.securenetsystems.net/WARL"]


def test_skips_the_shared_interstitial_mount() -> None:
    html = """
    var adURL = "https://ice7.securenetsystems.net/media";
    var streamURL = "https://ice7.securenetsystems.net/KXYZ";
    """
    assert securenet.stream_urls_from_page(html) == ["https://ice7.securenetsystems.net/KXYZ"]


def test_no_mount_means_no_guess() -> None:
    """A player page with no ice URL reports nothing rather than inventing one."""
    assert securenet.stream_urls_from_page("<html><body>Player loading...</body></html>") == []


def test_scanner_offers_the_real_stream_with_a_readable_reason() -> None:
    candidates = _securenet_candidates(ROM_URL, ROM_HTML)
    assert [c.url for c in candidates] == ["https://ice66.securenetsystems.net/ROM"]
    assert candidates[0].label == "ROM"
    assert "ROM" in candidates[0].reason


def test_scanner_ignores_pages_from_other_platforms() -> None:
    assert _securenet_candidates("https://example.com/", "<html>nothing here</html>") == []
