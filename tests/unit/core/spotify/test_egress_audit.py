"""GATE-9: the Spotify egress sites are reviewed and none are stale."""

from __future__ import annotations

import pytest

from quill.tools.network_egress_audit import discover_egress_sites, find_unreviewed_egress


# This reads and AST-parses every module in ``quill/`` -- around 1,300 files --
# and it is the *first* whole-tree scanner pytest reaches, so it pays that cost
# with nothing warmed up. Measured: ~19s on its own, ~16s inside
# ``tests/unit/core``, and over 180s inside a full ``pytest`` run.
#
# That last figure is not explained. GC pressure was measured and ruled out
# (1.1x, and disabling the collector changed nothing); coverage is not enabled;
# the source-text cache in ``quill.tools.source_cache`` removed the repeated
# disk reads for every *later* scanner but cannot help the first one. The
# remaining suspects are page-cache eviction and on-access virus scanning, both
# environmental and neither confirmed.
#
# So this number is sized from observation rather than from a theory, which is
# worth saying plainly: it is headroom for an unexplained slowdown, not a
# considered budget. A required gate that fails on machine load instead of on a
# real violation is one people learn to re-run rather than believe -- that is
# the thing being avoided here, and the same reason
# ``test_check_banned_patterns.py::test_clean_tree_has_no_violations`` carries
# a marker of its own.
@pytest.mark.timeout(600)
def test_no_unreviewed_or_stale_egress() -> None:
    unreviewed, stale = find_unreviewed_egress()
    assert unreviewed == set(), f"unreviewed egress sites: {sorted(unreviewed)}"
    assert stale == set(), f"stale reviewed entries: {sorted(stale)}"


def test_spotify_sites_are_discovered() -> None:
    sites = set(discover_egress_sites())
    assert "core/spotify/auth.py::_token_request" in sites
    assert "core/spotify/client.py::_request" in sites
