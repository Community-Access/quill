"""Spotify diagnostics: what happened during sign-in, and what state things are in.

Built after a tester reported (2026-11-04) that after entering a Client ID,
Connect said it was opening the browser and then nothing happened, and that
playing Spotify in Quill Radio did nothing either. Two things made that hard to
answer: the sign-in left no record of how far it got, and nothing said what a
working setup needs. This module answers both, in plain words a person can read
aloud to someone helping them, or paste into an email to support.

* :class:`SignInTrace` records each step of one sign-in attempt (consent, port
  bound, browser opened, redirect received, code exchanged, saved) and the
  failure, with times, and keeps the last attempt on disk.
* :func:`diagnostic_report` describes the current setup: the redirect address
  Spotify must have registered, whether a Client ID is saved, whether there is
  a sign-in and which permissions it carries, whether the sign-in port is free,
  the account type (Premium is needed to play), and the last attempt.
* :func:`plain_failure` turns a sign-in failure into one sentence that says
  what to do.

Nothing here ever records or prints a token, a code, or a code verifier. The
Client ID is not a secret (it is in every authorize URL), but the report shows
only its last four characters anyway, because a report gets pasted into
emails.
"""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir

#: Must match :data:`quill.core.spotify.auth.DEFAULT_REDIRECT_URI` exactly; the
#: report quotes it so a person can paste it into the Spotify dashboard.
from quill.core.spotify.auth import DEFAULT_REDIRECT_URI, DEFAULT_SCOPES
from quill.core.storage import read_json, write_json_atomic

TRACE_FILE = "spotify-last-sign-in.json"
REDIRECT_PORT = 43217

#: The dashboard steps, in order, as a person would do them.
SETUP_STEPS: tuple[str, ...] = (
    "In the Spotify for Developers dashboard, open your app and choose Edit Settings.",
    f"Under Redirect URIs, add exactly {DEFAULT_REDIRECT_URI} and save. "
    "It must match character for character: http, not https; 127.0.0.1, not localhost.",
    "Under APIs used, check Web API and Web Playback SDK.",
    "If you sign in with a different Spotify account from the one that created the app, "
    "add that account's email under User Management; an app in development mode only "
    "lets its owner and the people listed there sign in.",
    "Copy the Client ID from the app's Basic Information page into QUILL.",
)


@dataclass
class SignInTrace:
    """The steps of one sign-in attempt, each with the time it happened."""

    started: str = ""
    steps: list[tuple[str, str]] = field(default_factory=list)
    outcome: str = ""
    path: Path | None = None
    clock: Callable[[], float] = time.time

    def __post_init__(self) -> None:
        if not self.started:
            self.started = _stamp(self.clock())

    def step(self, text: str) -> None:
        self.steps.append((_stamp(self.clock()), text))
        self._save()

    def finish(self, outcome: str) -> None:
        self.outcome = outcome
        self._save()

    def lines(self) -> list[str]:
        if not self.steps and not self.outcome:
            return ["No sign-in has been attempted on this computer yet."]
        lines = [f"Started {self.started}."]
        lines += [f"{when}: {text}" for when, text in self.steps]
        if self.outcome:
            lines.append(f"Result: {self.outcome}")
        return lines

    def _save(self) -> None:
        target = self.path or (app_data_dir() / TRACE_FILE)
        try:
            write_json_atomic(
                target,
                {"started": self.started, "steps": self.steps, "outcome": self.outcome},
            )
        except OSError:
            pass  # a trace that cannot be written must never break a sign-in

    @classmethod
    def load_last(cls, path: Path | None = None) -> SignInTrace:
        raw = read_json(path or (app_data_dir() / TRACE_FILE), default={})
        if not isinstance(raw, dict):
            return cls(started="never")
        steps = [
            (str(item[0]), str(item[1]))
            for item in raw.get("steps", [])
            if isinstance(item, (list, tuple)) and len(item) == 2
        ]
        return cls(
            started=str(raw.get("started", "")) or "never",
            steps=steps,
            outcome=str(raw.get("outcome", "")),
            path=path,
        )


def plain_failure(error: BaseException) -> str:
    """One sentence for a failed sign-in that says what to do next."""
    text = str(error)
    lower = text.lower()
    if isinstance(error, OSError) and (
        getattr(error, "winerror", None) == 10048 or getattr(error, "errno", None) in (98, 10048)
    ):
        return (
            f"Another program is using the sign-in port {REDIRECT_PORT}. Close other "
            "copies of QUILL, Quill Radio or QUILL Cast that are signing in, then try again."
        )
    if "timed out waiting" in lower:
        return (
            "The browser never came back to QUILL. Check that "
            f"{DEFAULT_REDIRECT_URI} is listed exactly under Redirect URIs in your "
            "Spotify app. If you approved with a different Spotify account from the one "
            "that created the app, add it under User Management. Then try again."
        )
    if "invalid_client" in lower or "invalid client" in lower:
        return (
            "Spotify did not recognise that Client ID. Copy it again from your app's Basic "
            "Information page."
        )
    if "redirect" in lower and "invalid" in lower:
        return (
            f"Spotify refused the redirect address. Add {DEFAULT_REDIRECT_URI} exactly under "
            f"Redirect URIs in your Spotify app."
        )
    if "access_denied" in lower:
        return "The sign-in was cancelled in the browser, so QUILL is not connected."
    if "state" in lower and "mismatch" in lower:
        return (
            "The browser came back from a different sign-in attempt. Close the browser tab and"
            " try again."
        )
    if "could not reach spotify" in lower:
        return "QUILL could not reach Spotify. Check that you are online, then try again."
    return f"Could not connect to Spotify: {text}"


def port_is_free(port: int = REDIRECT_PORT) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def diagnostic_report(
    *,
    account_lookup: Callable[[], dict[str, Any]] | None = None,
    playback_available: Callable[[], bool] | None = None,
    trace_path: Path | None = None,
    now: Callable[[], float] = time.time,
) -> str:
    """The whole setup in plain lines. *account_lookup* reaches the network;
    pass ``None`` to skip it (Safe Mode, or no sign-in)."""
    from quill.core.spotify import token_store

    lines: list[str] = ["Spotify diagnostics", ""]
    lines.append(f"Redirect address your Spotify app must list: {DEFAULT_REDIRECT_URI}")
    client_id = token_store.load_client_id()
    lines.append(
        f"Client ID saved: yes, ending in {client_id[-4:]}" if client_id else "Client ID saved: no"
    )
    tokens = token_store.load_tokens()
    if tokens.is_empty:
        lines.append("Signed in: no. Nothing can play until the sign-in finishes.")
    else:
        left = tokens.expires_at - now()
        state = "current" if left > 0 else "expired; it renews by itself on next use"
        lines.append(f"Signed in: yes, access {state}.")
        granted = set(tokens.scope.split())
        missing = [s for s in DEFAULT_SCOPES if s not in granted]
        lines.append(
            "Permissions: all granted."
            if not missing
            else "Permissions missing: " + ", ".join(missing) + ". Sign in again to grant them."
        )
        if account_lookup is not None:
            try:
                me = account_lookup()
                product = str(me.get("product", "") or "unknown")
                lines.append(
                    f"Account type: {product}."
                    + ("" if product == "premium" else " Spotify Premium is needed to play audio.")
                )
            except Exception as exc:  # noqa: BLE001 - the report says what failed
                lines.append(f"Account check failed: {plain_failure(exc)}")
    lines.append(
        f"Sign-in port {REDIRECT_PORT}: "
        + ("free." if port_is_free() else "in use by another program.")
    )
    if playback_available is not None:
        lines.append(
            "Web playback (Microsoft Edge WebView2): "
            + (
                "available."
                if playback_available()
                else "missing. Install the WebView2 runtime to play Spotify."
            )
        )
    lines += ["", "Last sign-in attempt:"]
    lines += ["  " + line for line in SignInTrace.load_last(trace_path).lines()]
    lines += ["", "Setting up your Spotify app:"]
    lines += [f"  {n}. {step}" for n, step in enumerate(SETUP_STEPS, start=1)]
    return "\n".join(lines)


def _stamp(moment: float) -> str:
    return datetime.fromtimestamp(moment).strftime("%Y-%m-%d %H:%M:%S")
