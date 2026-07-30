"""GATE-9: the Spotify egress sites are reviewed and none are stale."""

from __future__ import annotations

from quill.tools.network_egress_audit import discover_egress_sites, find_unreviewed_egress


def test_no_unreviewed_or_stale_egress() -> None:
    unreviewed, stale = find_unreviewed_egress()
    assert unreviewed == set(), f"unreviewed egress sites: {sorted(unreviewed)}"
    assert stale == set(), f"stale reviewed entries: {sorted(stale)}"


def test_spotify_sites_are_discovered() -> None:
    sites = set(discover_egress_sites())
    assert "core/spotify/auth.py::_token_request" in sites
    assert "core/spotify/client.py::_request" in sites
