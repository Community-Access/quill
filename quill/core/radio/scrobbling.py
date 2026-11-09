"""Scrobbling, put together: who is signed in, and sending what is waiting.

The pieces live beside this module -- what counts as heard
(:mod:`~quill.core.radio.scrobble_tracker`), what waits to be sent
(:mod:`~quill.core.radio.scrobble_queue`), and the services
(:mod:`~quill.core.radio.listenbrainz`, :mod:`~quill.core.radio.lastfm`). This
module joins them, so the app's side only has to say "a song was heard" and
"send what is due", and never touches a request.

**Privacy, in one sentence the user guide repeats:** scrobbling sends the
artist, title and album of the songs you hear, and when you heard them, to
ListenBrainz, last.fm or Libre.fm -- only the services you turn on, and only
after you sign in or paste your token. Never the station, never anything else.

Credit: scrobbling from a radio player, and the one-minute rule, come from
BlindRadio by serrebidev (MIT). wx-free, strict-typed; network only through the
service modules, and only from a worker.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.radio import lastfm, listenbrainz, radio_credentials
from quill.core.radio.scrobble_queue import REJECTED, RETRY, Outcome, ScrobbleQueue
from quill.core.radio.scrobble_tracker import Listen

PRIVACY_NOTE = (
    "Scrobbling sends the artist, title and album of each song you hear for a "
    "minute or more, and when you heard it, to the services you turn on here -- "
    "only when you turn one on and sign in or paste your token. Nothing about "
    "the station or about you is sent."
)


@dataclass(frozen=True, slots=True)
class Accounts:
    """What is turned on and signed in, read once and handed to a worker."""

    listenbrainz_token: str = ""
    lastfm_session: str = ""
    librefm_session: str = ""
    api_key: str = ""
    secret: str = ""

    def services(self) -> list[str]:
        """The service ids that can be sent to now."""
        found: list[str] = []
        if self.listenbrainz_token:
            found.append(listenbrainz.SERVICE)
        if self.api_key and self.secret:
            if self.lastfm_session:
                found.append(lastfm.LASTFM.id)
            if self.librefm_session:
                found.append(lastfm.LIBREFM.id)
        return found


def load_accounts(history: Any) -> Accounts:
    """Read the switches from *history* and the secrets from the credential store."""
    lb_on = bool(getattr(history, "scrobble_listenbrainz", False))
    fm_on = bool(getattr(history, "scrobble_lastfm", False))
    libre_on = bool(getattr(history, "scrobble_librefm", False))
    if not (lb_on or fm_on or libre_on):
        return Accounts()
    key, secret = lastfm.stored_app_credentials() if (fm_on or libre_on) else ("", "")
    return Accounts(
        listenbrainz_token=(
            radio_credentials.load(radio_credentials.LISTENBRAINZ_TOKEN).secret if lb_on else ""
        ),
        lastfm_session=(
            radio_credentials.load(radio_credentials.LASTFM_SESSION).secret if fm_on else ""
        ),
        librefm_session=(
            radio_credentials.load(radio_credentials.LIBREFM_SESSION).secret if libre_on else ""
        ),
        api_key=key,
        secret=secret,
    )


def _service_for(service_id: str) -> lastfm.Service:
    return lastfm.LIBREFM if service_id == lastfm.LIBREFM.id else lastfm.LASTFM


def _send(
    service_id: str,
    accounts: Accounts,
    batch: list[Listen],
    *,
    safe_mode: bool,
    post: Callable[..., Any] | None,
) -> Outcome:
    if service_id == listenbrainz.SERVICE:
        return listenbrainz.submit(
            accounts.listenbrainz_token, batch, safe_mode=safe_mode, post=post
        )
    service = _service_for(service_id)
    session = accounts.librefm_session if service is lastfm.LIBREFM else accounts.lastfm_session
    return lastfm.scrobble(
        service,
        batch,
        api_key=accounts.api_key,
        secret=accounts.secret,
        session_key=session,
        safe_mode=safe_mode,
        post=post,
    )


def submit_due(
    queue: ScrobbleQueue,
    accounts: Accounts,
    *,
    now: float,
    safe_mode: bool = False,
    post: Callable[..., Any] | None = None,
) -> list[tuple[str, Outcome]]:
    """Send every due batch for every signed-in service. Runs on a worker.

    Returns ``(service id, outcome)`` for each batch tried. A RETRY stops that
    service for this round; the queue says when to try again. A batch refused
    as a whole is sent again one song at a time, so one song the service will
    not take never throws away the other forty-nine.
    """
    results: list[tuple[str, Outcome]] = []
    for service_id in accounts.services():
        for _round in range(20):  # never loop forever on a full queue
            batch = queue.due_batch(service_id, now=now)
            if not batch:
                break
            outcome = _send(service_id, accounts, batch, safe_mode=safe_mode, post=post)
            if outcome.kind == REJECTED and len(batch) > 1:
                outcome = _send_singly(
                    queue,
                    accounts,
                    service_id,
                    batch,
                    results,
                    now=now,
                    safe_mode=safe_mode,
                    post=post,
                )
            else:
                queue.settle(service_id, batch, outcome, now=now)
                results.append((service_id, outcome))
            if outcome.kind == RETRY or queue.is_blocked(service_id):
                break
    return results


def _send_singly(
    queue: ScrobbleQueue,
    accounts: Accounts,
    service_id: str,
    batch: list[Listen],
    results: list[tuple[str, Outcome]],
    *,
    now: float,
    safe_mode: bool,
    post: Callable[..., Any] | None,
) -> Outcome:
    """A refused batch, again one song at a time; the last outcome is returned."""
    outcome = Outcome(REJECTED)
    for listen in batch:
        outcome = _send(service_id, accounts, [listen], safe_mode=safe_mode, post=post)
        queue.settle(service_id, [listen], outcome, now=now)
        results.append((service_id, outcome))
        if outcome.kind == RETRY or queue.is_blocked(service_id):
            break
    return outcome


def send_now_playing(
    accounts: Accounts,
    listen: Listen,
    *,
    safe_mode: bool = False,
    post: Callable[..., Any] | None = None,
) -> None:
    """Tell each signed-in service what just started. Failures are dropped."""
    for service_id in accounts.services():
        if service_id == listenbrainz.SERVICE:
            listenbrainz.submit(
                accounts.listenbrainz_token,
                [listen],
                playing_now=True,
                safe_mode=safe_mode,
                post=post,
            )
            continue
        service = _service_for(service_id)
        session = accounts.librefm_session if service is lastfm.LIBREFM else accounts.lastfm_session
        lastfm.update_now_playing(
            service,
            listen,
            api_key=accounts.api_key,
            secret=accounts.secret,
            session_key=session,
            safe_mode=safe_mode,
            post=post,
        )


def service_name(service_id: str) -> str:
    if service_id == listenbrainz.SERVICE:
        return listenbrainz.NAME
    return _service_for(service_id).name


__all__ = [
    "PRIVACY_NOTE",
    "Accounts",
    "load_accounts",
    "send_now_playing",
    "service_name",
    "submit_due",
]
