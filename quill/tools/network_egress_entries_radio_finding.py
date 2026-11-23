"""Quill Radio's reviewed call sites for Find Streams from a Website.

Extracted from :mod:`quill.tools.network_egress_entries_radio` under GATE-11
(extract, never rebaseline) when Find Streams moved onto
:mod:`quill.core.net_public`, the public-internet-only fetch: that module was
near its ceiling, and these entries are one feature's, reviewed together.
The public-only guard, like the live check and the server listings these
entries describe, is an idea from Andre Louis's StreamSift
(https://github.com/OnjLouis/StreamSift), written in QUILL's own code.
"""

from __future__ import annotations

RADIO_FINDING_EGRESS: dict[str, str] = {
    "core/net_public.py::_connect_pinned": (
        "Single egress site for 'Find Streams from a Website...' "
        "(core/radio/link_finder.py::_http_get and ::_probe, both through "
        "net_public.fetch): fetches the "
        "one page the user typed to look for a station's own stream link "
        "(audio/source tags, playlist-shaped hrefs, player data attributes and "
        "script settings), plus, from that page only, a capped number of "
        "follow-ons: up to 3 iframes, 2 window.open pop-up players, 3 portal or "
        "Listen pages, 3 of the SAME site's own player scripts, and up to 2 "
        "Icecast status pages (status-json.xsl, falling back to status.xsl) the "
        "page links to. Reached by the explicit Scan button, which states the "
        "exact URL before fetching, AND -- corrected 2026-09-23, this entry "
        "previously said 'only' -- automatically by stream recovery when a "
        "station fails to play, which fetches that station's own website with "
        "no prompt and no URL stated. That path is gated by "
        "history.recover_from_website (on by default) and runs once per station "
        "per session. HTTPS-first over a verified TLS context, bounded timeout "
        "(12 s) and response size (2 MB); on a certificate *hostname* failure "
        "_fetch_html retries the www-toggled host (still fully verified), and "
        "-- widened 2026-11-21, ideas from Andre Louis's StreamSift -- on a "
        "refused or reset connection, a timeout or any TLS failure it reads the "
        "plain-http page, because many small community stations have no HTTPS "
        "at all; only public HTML is read and verification is never relaxed. "
        "THE LIVE CHECK (2026-11-21, same call site, no new one): each candidate "
        "the scan found is opened once (one more for a playlist or HLS master) "
        "and only its headers and first 4 KB are read (live_check.PROBE_BYTES), "
        "to tell live audio from a web page or a podcast file. At most 16 "
        "candidates (48 with a server listing or the soundmap), 4 at a time, "
        "under one 20-second overall deadline, each "
        "request inside the same 12 s timeout; a GET with QUILL's User-Agent "
        "and nothing else -- no cookie, no credential. These go to the stream "
        "addresses the scanned page itself names, which may be plain http "
        "(Icecast on a high port): the same address Test or Play would open "
        "anyway. SERVER LISTINGS (2026-11-22, same call site, ideas from "
        "StreamSift): when the scanned page is a streaming server's front or "
        "status page, or links to one, up to 2 servers are asked what they "
        "serve -- Icecast status-json.xsl (then its HTML status page) or "
        "SHOUTcast v2 /statistics?json=1 -- on the host and port the page "
        "named, never a backend host the statistics report. A Global Player "
        "page (www.globalplayer.com/live/...) is read like any page; its free "
        "streams (media-ssl.musicradio.com) come from the page's own state. "
        "The IPRD website match reads only the cached catalogue, no request. "
        "PUBLIC INTERNET ONLY (2026-11-22, ideas from Andre Louis's StreamSift, "
        "https://github.com/OnjLouis/StreamSift): every request, the page typed "
        "included, goes through net_public.fetch, which refuses before anything "
        "is sent any scheme but http and https, userinfo, control characters "
        "or a backslash, an address over 4096 characters, a host that is empty, "
        "a single label, localhost, *.localhost, *.local, *.internal, "
        "*.home.arpa or all numbers, and any name whose lookup returns even one "
        "address that is not globally reachable (private, loopback, link-local "
        "and so cloud metadata, CGNAT, test and documentation ranges, IPv6 "
        "unique-local and link-local; IPv4-mapped, IPv4-compatible, NAT64 and "
        "6to4 addresses are unwrapped first). The connection is then pinned to "
        "the address that was checked (this function), so DNS rebinding cannot "
        "move it; HTTPS still verifies the certificate against the host name "
        "through quill.core.net. Redirects are followed by hand, at most 5, each "
        "re-checked; the opener has no redirect, FTP, file or data handler. The "
        "body is read in 64 KB chunks under an overall deadline (twice the "
        "timeout for a page, the remaining budget for a live check). A "
        "configured proxy is honoured: then the proxy resolves and connects, so "
        "pinning is not possible, but the address is still checked first and a "
        "name that resolves here to a private address is still refused. An "
        "address on this computer or the listener's own network is never read "
        "here; My Servers is the path for a server on your own network. "
        "Disabled in Safe Mode via link_finder.refuse_in_safe_mode."
    ),
    "core/radio/triton.py::_fetch_api": (
        "Follow-on egress for 'Find Streams from a Website...' when the scanned "
        "page is a Triton Digital / StreamTheWorld web player (e.g. the "
        "player.listenlive.co network). Such players compute their stream URL "
        "in JavaScript, so it never appears in the page HTML; this resolves the "
        "callsign the page advertises to a real playable mount through Triton's "
        "JS-free provisioning API (playerservices.streamtheworld.com). One "
        "HTTPS GET, for pages that look like Triton players "
        "(triton.page_is_triton_player). Reached from the explicit Scan button "
        "and -- corrected 2026-09-23, this entry previously said 'only' from it "
        "-- automatically by stream recovery after a failed play, gated by "
        "history.recover_from_website. "
        "HTTPS-only over a verified TLS context, bounded timeout and response "
        "size. Disabled in Safe Mode via triton.refuse_in_safe_mode."
    ),
}


__all__ = ["RADIO_FINDING_EGRESS"]
