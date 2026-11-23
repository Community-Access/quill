"""The last ten website addresses Find Streams found live streams on.

A station's site is scanned again next week, and the week after: so the
Website address field remembers the addresses that worked, newest first, as an
editable combo box. Nothing is spoken when it changes.

Rules that keep the list safe and worth opening:

* **Only an address that found at least one live stream** is remembered. A
  typo, a dead site or a page of podcast files is not worth coming back to.
* **Never an address with a query, a fragment or a user name**, because those
  can carry a session token or a password. Only the scheme, host, port and path
  are kept, and only for ``http`` and ``https``.
* **Never one on this computer or your own network**: Find Streams does not
  read those (:mod:`quill.core.net_public`).
* **Repeating an address moves it up** rather than adding a second copy, and
  the list keeps at most :data:`MAX_RECENT_WEBSITES`.

It rides ``radio_history.json`` with the recent searches, on the listener's own
computer, and is never sent anywhere. **Clear Recent Searches...** (Quill
Radio's Station menu, QUILL's Internet Radio menu; ``quill/ui/radio/
clear_recent.py``) empties it together with the searches. Remembering addresses that worked is an
idea from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift),
written here in QUILL's own code.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterable

from quill.core.net_public import host_is_refused

__all__ = ["MAX_RECENT_WEBSITES", "from_json", "remember", "storable", "to_json"]

MAX_RECENT_WEBSITES = 10
_MAX_CHARS = 2048


def storable(address: str) -> bool:
    """True when *address* may be remembered at all (see the module rules)."""
    text = address.strip()
    if not text or len(text) > _MAX_CHARS or any(ch.isspace() for ch in text):
        return False
    parts = urllib.parse.urlsplit(text)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return False
    if parts.query or parts.fragment or "@" in parts.netloc or "?" in text or "#" in text:
        return False
    try:
        _port = parts.port
    except ValueError:
        return False
    return not host_is_refused(parts.hostname)


def _same(first: str, second: str) -> bool:
    return first.rstrip("/").casefold() == second.rstrip("/").casefold()


def remember(recent: Iterable[str], address: str) -> tuple[str, ...]:
    """*address* first, any earlier copy gone, at most ten; unchanged if not storable."""
    current = tuple(recent)
    if not storable(address):
        return current
    kept = [old for old in current if not _same(old, address)]
    return (address.strip(), *kept)[:MAX_RECENT_WEBSITES]


def from_json(raw: object) -> tuple[str, ...]:
    """The stored list, with anything that should never have been kept dropped."""
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and storable(item) and not any(_same(item, o) for o in out):
            out.append(item.strip())
    return tuple(out[:MAX_RECENT_WEBSITES])


def to_json(recent: Iterable[str]) -> list[str]:
    return [address for address in recent if storable(address)][:MAX_RECENT_WEBSITES]
