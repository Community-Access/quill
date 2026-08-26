"""Resolve the GitHub token used for issue submission (#210 follow-up).

Both the Report a Bug dialog and the crash reporter need a GitHub token to
create an issue. This unifies the sources: QUILL's OS-encrypted token store is
the single source of truth, with a one-time import of whatever ``feedback_hub``
resolves from the environment so a token configured for one path is reliably
available to the other. No token is ever bundled or written to the repo; the
store is per-user and encrypted (Windows Credential Manager / macOS Keychain).

**As of 2026-08-26 the preferred path needs no token at all**: reports are
POSTed to the feedback-hub submission server, which holds the only credential.
See :data:`DEFAULT_FEEDBACK_SERVER` below. Everything about the token remains
as a fallback for builds with no server configured, and can be removed once the
server path has shipped in a release.

Ordinary users who have never signed in to GitHub still need a working
"Report a Bug" dialog, so a narrowly-scoped, issues-only token is bundled at
build time into the generated ``quill._feedback_token`` module (see
``tools/generate_feedback_token.py`` and
``docs/superpowers/specs/2026-07-06-bundled-feedback-token-design.md``). That
bundled token is tried after the user's own stored/env token, never before
it.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _bundled_token() -> str:
    """Return the token baked in at build time, or "" in an unbuilt checkout."""
    try:
        from quill._feedback_token import BUNDLED_TOKEN  # type: ignore[import-untyped]
    except ImportError:
        return ""
    return (BUNDLED_TOKEN or "").strip()


def effective_github_token(*, import_from_env: bool = True) -> str:
    """Return the GitHub token to use, or an empty string when none is available.

    Order of preference:

    1. QUILL's secure token store (``token_store.load_github_token``).
    2. ``feedback_hub.resolve_token()``, given the bundled, issues-only token
       (baked in at build time) as its first candidate, so it wins over the
       env-var fallback but never over a user's own stored token.

    When a token is found only in the environment/bundle and the secure store
    is empty, it is copied into the store (best effort) so subsequent calls —
    and the other reporting path — resolve it reliably without depending on
    env vars.
    """
    from quill.core.github.token_store import load_github_token, save_github_token

    stored = load_github_token()
    if stored:
        return stored

    env_token = ""
    try:
        from feedback_hub import resolve_token

        env_token = (resolve_token(_bundled_token()) or "").strip()
    except Exception:  # noqa: BLE001 - a missing/broken feedback_hub is non-fatal
        env_token = ""

    if env_token and import_from_env:
        try:
            save_github_token(env_token)
        except Exception:  # noqa: BLE001 - persisting is a convenience, not required
            logger.warning("Could not persist resolved GitHub token", exc_info=True)
    return env_token


def github_token_present() -> bool:
    """Return True when a token is available without importing it into the store."""
    return bool(effective_github_token(import_from_env=False))


#: Where reports are sent when no token is involved at all.
#:
#: This is the whole point of the constant. A build that posts here needs no
#: credential, so nothing has to be compiled into the installer -- and today
#: every installer carries a fine-grained token that anybody who unzips one can
#: read. Issues-only scope on a single repository bounds that to issue spam,
#: which is why it has been tolerable; it stops being necessary once a server
#: holds the credential instead.
#:
#: It also decides where reports go *later*. Once submission is a POST to a
#: URL, moving Report a Bug from a GitHub issue to a support conversation in
#: the help desk is a change on the server -- not a release to every installed
#: copy, and not a long tail of old versions still filing into the wrong place.
#:
#: Overridable by environment variable because the hostname is not settled:
#: see section 6 of docs/design/2026-08-26-feedback-redesign-for-freescout.md.
#: Setting it empty falls back to the bundled token, which is what a fork with
#: no server of its own needs.
DEFAULT_FEEDBACK_SERVER = "https://lp.csedesigns.com/submit/feedback"


def feedback_server_url() -> str:
    """The submission server to post reports to, or "" to use a token."""
    import os

    override = os.environ.get("QUILL_FEEDBACK_SERVER_URL")
    if override is not None:
        return override.strip()
    return DEFAULT_FEEDBACK_SERVER


def submission_kwargs() -> dict[str, str]:
    """The transport arguments for ``FeedbackDialog`` and ``submit()``.

    One place, so the two call sites cannot drift and neither has to know the
    order of preference. ``server_url`` wins inside feedback-hub when both are
    given, which is what makes a build shippable with no token at all: the
    token here is only the fallback for a build with no server configured.
    """
    return {
        "server_url": feedback_server_url(),
        "github_token": effective_github_token(),
    }


def can_submit_reports() -> bool:
    """True when Report a Bug has *any* way to send, server or token.

    Replaces asking about the token alone, which was the right question only
    while a token was the only transport. Asking it now would send somebody to
    the web form on a build that can submit perfectly well.
    """
    return bool(feedback_server_url()) or github_token_present()
