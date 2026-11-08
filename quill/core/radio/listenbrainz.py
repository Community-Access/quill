"""ListenBrainz: send the songs you heard, with your own user token.

ListenBrainz is the open, non-profit listening log run by the MetaBrainz
Foundation (the people behind MusicBrainz). Its ``submit-listens`` call takes
a user token -- found on the listener's own settings page, pasted into
Preferences -- and a JSON list of listens. Nothing here runs unless the
listener turned ListenBrainz on and pasted a token.

Two kinds of request: ``single`` (or ``import`` for several at once) for a
song heard for a minute, and ``playing_now`` for the song just started, which
ListenBrainz shows on the profile and does not keep. A failed ``playing_now``
is never retried; it is out of date by then.

The request shape follows BlindRadio by serrebidev (MIT),
``crates/blindradio-core/src/scrobble.rs``, and the official API docs at
https://listenbrainz.readthedocs.io/en/latest/users/api/core.html.
wx-free, strict-typed; the one network call is :func:`quill.core.radio.scrobble_http.post`.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from quill.core.radio import scrobble_http
from quill.core.radio.scrobble_queue import REJECTED, RETRY, SENT, SIGN_IN, Outcome
from quill.core.radio.scrobble_tracker import Listen

SUBMIT_URL = "https://api.listenbrainz.org/1/submit-listens"

#: Where a listener finds their user token.
TOKEN_URL = "https://listenbrainz.org/settings/"

SERVICE = "listenbrainz"
NAME = "ListenBrainz"

Poster = Callable[..., scrobble_http.Reply]


def _track(listen: Listen) -> dict[str, object]:
    metadata: dict[str, object] = {
        "artist_name": listen.artist,
        "track_name": listen.title,
        "additional_info": {
            "submission_client": "Quill Radio",
            "media_player": "Quill Radio",
        },
    }
    if listen.album:
        metadata["release_name"] = listen.album
    return metadata


def build_body(listens: list[Listen], *, playing_now: bool = False) -> bytes:
    """The JSON body for *listens* (pure).

    ``playing_now`` sends one song with no ``listened_at``; otherwise one song
    is ``single`` and several are ``import``, as the API asks.
    """
    if playing_now:
        payload: list[dict[str, object]] = [{"track_metadata": _track(listens[0])}]
        kind = "playing_now"
    else:
        payload = [
            {"listened_at": listen.listened_at, "track_metadata": _track(listen)}
            for listen in listens
        ]
        kind = "single" if len(listens) == 1 else "import"
    return json.dumps({"listen_type": kind, "payload": payload}).encode("utf-8")


def parse_reply(reply: scrobble_http.Reply) -> Outcome:
    """What a ``submit-listens`` answer means for the songs sent (pure)."""
    message = ""
    try:
        data = json.loads(reply.text) if reply.text else {}
        if isinstance(data, dict):
            message = str(data.get("error", "") or data.get("message", "") or "")
    except ValueError:
        data = {}
    if reply.status == 200:
        return Outcome(SENT)
    if reply.status == 401:
        return Outcome(
            SIGN_IN,
            "ListenBrainz did not accept your user token. Copy it again from "
            f"{TOKEN_URL} and paste it into Preferences.",
        )
    if reply.status == 429 or reply.status >= 500:
        return Outcome(RETRY, message or f"ListenBrainz is busy ({reply.status}).")
    return Outcome(REJECTED, message or f"ListenBrainz refused the listens ({reply.status}).")


def submit(
    token: str,
    listens: list[Listen],
    *,
    playing_now: bool = False,
    safe_mode: bool = False,
    post: Poster | None = None,
) -> Outcome:
    """Send *listens*. Network trouble is a RETRY, never an exception."""
    if not token.strip():
        return Outcome(SIGN_IN, "ListenBrainz needs your user token in Preferences.")
    if not listens:
        return Outcome(SENT)
    sender = post if post is not None else scrobble_http.post
    try:
        reply = sender(
            SUBMIT_URL,
            build_body(listens, playing_now=playing_now),
            content_type="application/json",
            headers={"Authorization": f"Token {token.strip()}"},
            safe_mode=safe_mode,
        )
    except scrobble_http.ScrobbleNetworkError as error:
        return Outcome(RETRY, str(error.args[0]) if error.args else "")
    return parse_reply(reply)


__all__ = ["NAME", "SERVICE", "SUBMIT_URL", "TOKEN_URL", "build_body", "parse_reply", "submit"]
