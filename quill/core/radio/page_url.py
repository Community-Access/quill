"""What counts as a website address, and how to normalise one.

Two small pure predicates, together because they answer halves of the same
question and because more than one surface asks it. They started inside
:mod:`quill.core.radio.link_finder` and the Find Stations dialog, which was
fine while the scanner was the only caller -- and stopped being fine the
moment a second search box needed to recognise an address (#1491).

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import re
import urllib.parse

__all__ = ["looks_like_url", "normalize_page_url"]


def looks_like_url(text: str) -> bool:
    """True when *text* is a website address, not a station-name query (pure).

    What lets a search box fold in "Find Streams from a Website": an entry that
    is a URL (an explicit scheme, or a bare ``host.tld/...`` with no spaces) is
    scanned for streams instead of run as a directory name search.

    #1491 is what its absence cost: Search All Sources handed ``oj991.com`` to
    every directory as a *name*, Radio Browser matched the token "com", and the
    answer was 33 rows of Cruisin92.com and STAR1079.com without the station
    anywhere in it.
    """
    value = text.strip()
    if not value or " " in value:
        return False
    if value.lower().startswith(("http://", "https://")):
        return True
    host = value.split("/", 1)[0]
    return "." in host and not host.endswith(".")


def normalize_page_url(text: str) -> str:
    """Turn a loosely-typed site name/URL into an https:// URL, best effort."""
    candidate = text.strip()
    if not candidate:
        return ""
    if not re.match(r"^https?://", candidate, re.IGNORECASE):
        candidate = f"https://{candidate}"
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    return urllib.parse.urlunsplit(parsed)
