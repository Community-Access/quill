"""Per-host HTTP headers a stream needs before its server will answer.

ccMixter's content host answers 403 to any request without a Referer from
ccmixter.org (measured 2026-08-16: same URL, same client -- 403 bare, 206
with the header). The browse row was honest, the URL was right, and playback
still failed silently, because neither mpv nor ffmpeg sends a Referer unless
told to. This module is the one place that knowledge lives; the playback
engine and the recorder both ask it per URL.

Empty string means "send nothing", which is every other host. wx-free.
"""

from __future__ import annotations

from urllib.parse import urlparse


def referrer_for(url: str) -> str:
    """The Referer header *url* needs, or "" for none."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if host == "ccmixter.org" or host.endswith(".ccmixter.org"):
        return "https://ccmixter.org/"
    return ""
