"""Scribe for Documents, for the whole QUILL family (docs/planning/scribe-for-documents-prd.md).

Pneuma Solutions' Scribe for Documents rebuilds inaccessible documents (scans,
badly made PDFs, pictures of text, Office files) into accessible HTML, Word,
tagged PDF, EPUB, MOBI, DAISY, MP3 and BRF. Each person signs in with their
own Scribe account and pays Scribe for their own pages; QUILL never takes
payment and never sees a Scribe password.

The package is wx-free and strict-typed:

* :mod:`.client` -- the REST API (one reviewed egress site, GATE-9).
* :mod:`.channel` -- the Phoenix document channel over a WebSocket.
* :mod:`.auth` -- OAuth 2.0 + PKCE on a loopback port, tokens in the vault.
* :mod:`.model` -- formats, stages, settings and the server's shapes.
* :mod:`.queue` -- the family queue: one document at a time, per Windows user.
* :mod:`.runner` -- one job, from upload to downloads.
* :mod:`.library` -- the local record of what was downloaded where.
* :mod:`.sentences` -- every sentence the person hears, and when.
* :mod:`.options` -- the family's shared Scribe options.

**The client ID.** QUILL is a public client (PKCE, no secret), so its ID may
ship in the source. It has not been issued yet (QUILL is waiting for
Pneuma's review), so :data:`CLIENT_ID` is empty and every Scribe command says
plainly that the service is not available in this build. Set
``QUILL_SCRIBE_CLIENT_ID`` in a development build to try it against a test
server; release builds ignore the variable.
"""

from __future__ import annotations

import os

#: Pneuma's product name, said by every command, title and result (SCR-POL-1).
PRODUCT_NAME = "Scribe for Documents"

#: The one place the issued client ID goes. Empty until Pneuma approves QUILL.
CLIENT_ID = ""

#: The service. The channel is the same host over ``wss``.
BASE_URL = "https://scribeit.io"

#: Where the person buys pages, manages retention and deletes the account.
LINKS: dict[str, str] = {
    "website": "https://scribeit.io",
    "terms": "https://scribeit.io/terms",
    "privacy": "https://scribeit.io/privacy",
    "manual": "https://manual.scribeit.io",
    "purchase": "https://scribeit.io/purchase",
}

#: Said when a command is chosen but the build has no client ID.
NOT_AVAILABLE_SENTENCE = (
    "Scribe for Documents is not available in this build of {app} yet. "
    "It will arrive in an update once Pneuma Solutions has approved {app}."
)


def client_id() -> str:
    """The issued client ID, or ``""`` when this build has none.

    A development build may name one in ``QUILL_SCRIBE_CLIENT_ID`` to test
    against a server; a release build ignores the variable.
    """
    if CLIENT_ID:
        return CLIENT_ID
    from quill.core import paths

    if getattr(paths, "_DEV_BUILD", False):
        return os.environ.get("QUILL_SCRIBE_CLIENT_ID", "").strip()
    return ""


def base_url() -> str:
    """The service address; a development build may point at a test server."""
    from quill.core import paths

    if getattr(paths, "_DEV_BUILD", False):
        override = os.environ.get("QUILL_SCRIBE_BASE_URL", "").strip().rstrip("/")
        if override:
            return override
    return BASE_URL


def safe_mode_active() -> bool:
    """True in Safe Mode, which turns every Scribe command off (PRD 10.1.3)."""
    return os.environ.get("QUILL_SAFE_MODE") == "1"


def unavailable_reason(app_name: str = "QUILL") -> str:
    """Why Scribe cannot be used right now, or ``""`` when it can.

    Safe Mode first (the family's usual sentence), then a build with no
    client ID. Nothing is queued when this is not empty.
    """
    if safe_mode_active():
        return (
            f"{PRODUCT_NAME} is disabled in Safe Mode. Restart {app_name} without "
            "--safe-mode to use network features."
        )
    if not client_id():
        return NOT_AVAILABLE_SENTENCE.format(app=app_name)
    return ""


__all__ = [
    "BASE_URL",
    "CLIENT_ID",
    "LINKS",
    "NOT_AVAILABLE_SENTENCE",
    "PRODUCT_NAME",
    "base_url",
    "client_id",
    "safe_mode_active",
    "unavailable_reason",
]
