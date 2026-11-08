"""Quill Radio's keys and sign-ins, in the Windows credential store.

The scrobbling tokens, the last.fm sign-ins and the AudD token all live here,
never in a settings file: Windows keeps them sealed to this user (DPAPI, under
the credential store), so a synced or copied data folder carries none of them.
The same rule AcoustID's key follows (:mod:`quill.core.radio.acoustid`).

One small surface, so tests replace it in one place (``tests/conftest.py``)
and nothing here can reach the developer's real store. A computer with no
credential store keeps nothing rather than writing a token somewhere less
safe. BlindRadio by serrebidev (MIT) seals its tokens with DPAPI the same way
(``crates/blindradio-core/src/secret.rs``); Quill uses the credential store
it already had. wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

LISTENBRAINZ_TOKEN = "quill:radio:listenbrainz:token"
LASTFM_API_KEY = "quill:radio:lastfm:api-key"
LASTFM_SECRET = "quill:radio:lastfm:secret"
LASTFM_SESSION = "quill:radio:lastfm:session"
LIBREFM_SESSION = "quill:radio:librefm:session"
AUDD_TOKEN = "quill:radio:audd:token"


@dataclass(frozen=True, slots=True)
class Stored:
    secret: str = ""
    #: The account name a sign-in belongs to, when there is one.
    user_name: str = ""


def load(target: str) -> Stored:
    """What is stored under *target*, or an empty :class:`Stored`."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential
    except ImportError:
        return Stored()
    try:
        found = load_generic_credential(target)
    except (OSError, ValueError, RuntimeError):  # pragma: no cover - platform dependent
        return Stored()
    if found is None:
        return Stored()
    user = str(getattr(found, "user_name", "") or "")
    return Stored(
        str(getattr(found, "secret", "") or "").strip(),
        "" if user == "quill-user" else user,
    )


def save(target: str, secret: str, user_name: str = "") -> bool:
    """Store *secret* (removing it when blank). True when the store agreed."""
    try:
        from quill.platform.windows.credential_manager import (
            delete_generic_credential,
            save_generic_credential,
        )
    except ImportError:
        return False
    try:
        if secret.strip():
            if user_name:
                save_generic_credential(target, secret.strip(), user_name=user_name)
            else:
                save_generic_credential(target, secret.strip())
        else:
            delete_generic_credential(target)
    except (OSError, ValueError, RuntimeError):  # pragma: no cover - platform dependent
        return False
    return True


__all__ = [
    "AUDD_TOKEN",
    "LASTFM_API_KEY",
    "LASTFM_SECRET",
    "LASTFM_SESSION",
    "LIBREFM_SESSION",
    "LISTENBRAINZ_TOKEN",
    "Stored",
    "load",
    "save",
]
