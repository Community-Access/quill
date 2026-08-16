"""AudioPub (audiopub.site): community audio, browsed as a first-class source.

AudioPub is an open-source (AGPL-3.0) platform where people publicly share
audio they made -- its agreement states uploads are hosted for anyone to
stream and download. The *software* being open source does not make the
*audio* freely licensed: uploaders keep their rights, so QUILL Radio plays
this catalog live and never stores or redistributes it (the station catalog
deliberately excludes it).

Version 1 is **Discover only**, built on the one JSON endpoint the AudioPub
source implements for clients (``GET /quickfeed/api?page=N``, 50 items per
page, deliberately randomized server-side -- a surprise shelf, not a
newest-first shelf). The site's own pages show that queries for newest,
popular, search, and active live streams already exist server-side; rather
than screen-scrape those, the plan of record is to ask the AudioPub
developer to bless a small read-only API for them (see the radio PRD).

Each request funnels through the single reviewed egress site (:func:`_fetch`
-- see ``quill/tools/network_egress_audit.py``), HTTPS-only over a verified
TLS context with a bounded timeout and size, reached only by an explicit
browse action, and disabled in Safe Mode. wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import ssl
import urllib.error
import urllib.request

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation

_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"
_BASE = "https://audiopub.site"
_TIMEOUT_SECONDS = 20.0
_MAX_BYTES = 4_000_000
PAGE_SIZE = 50


class AudioPubError(CodedError):
    """An AudioPub request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-AUDIOPUB-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`AudioPubError` when Safe Mode is active."""
    if safe_mode:
        raise AudioPubError(
            "AudioPub is a network service and is disabled in Safe Mode. "
            "Restart QUILL normally to browse it."
        )


def _fetch(url: str) -> str:
    """One HTTPS GET -- the single reviewed egress site for AudioPub."""
    if not url.startswith("https://"):
        raise AudioPubError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (
        urllib.error.URLError,
        TimeoutError,
        ssl.SSLError,
        OSError,
        http.client.HTTPException,
    ) as error:
        raise AudioPubError(f"Could not reach AudioPub: {error}") from error
    return payload.decode("utf-8", errors="replace")


def parse_discover(json_text: str) -> list[RadioStation]:
    """Parse one quickfeed page (pure; tolerant of junk).

    A row is a finished recording, not a stream: ``is_recording=True`` so the
    player offers a timeline and remembers your place. The creator and play
    count ride along -- "by keoku, played 42 times" is what makes a random
    shelf browsable by ear.
    """
    try:
        data = json.loads(json_text)
    except ValueError:
        return []
    rows: list[RadioStation] = []
    audios = data.get("audios") if isinstance(data, dict) else None
    for entry in audios if isinstance(audios, list) else []:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        path = str(entry.get("path") or "").strip().lstrip("/")
        if not title or not path:
            continue
        raw_user = entry.get("user")
        user: dict[str, object] = raw_user if isinstance(raw_user, dict) else {}
        creator = str(user.get("displayName") or user.get("name") or "").strip()
        plays = entry.get("plays")
        note_bits = [f"by {creator}" if creator else "", f"played {plays} times" if plays else ""]
        rows.append(
            RadioStation(
                name=title,
                stream_url=f"{_BASE}/{path}",
                homepage=f"{_BASE}/audio/{entry.get('id', '')}" if entry.get("id") else _BASE,
                tags=tuple(bit for bit in note_bits if bit),
                source="AudioPub",
                is_recording=True,
            )
        )
    return rows


def discover(page: int = 1, *, safe_mode: bool = False) -> list[RadioStation]:
    """One randomized Discover page. Every call is a fresh surprise --
    the server shuffles, so this is deliberately never cached."""
    refuse_in_safe_mode(safe_mode)
    return parse_discover(_fetch(f"{_BASE}/quickfeed/api?page={max(1, int(page))}"))
