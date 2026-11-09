"""Sign in with GitHub for the GitHub Workbench: the device code, the wait, the token.

A personal access token is the hardest thing the Workbench ever asked of
anybody: five pages of GitHub settings, a list of scopes with names like
``repo`` and ``workflow``, and a 40-character secret pasted blind. This module
is the wx-free half of the easier road, GitHub's OAuth device flow (RFC 8628):
QUILL asks GitHub for a short code, the person types it on
github.com/login/device and approves QUILL there, and QUILL waits in the
background until they have.

**One registration per app, shared with Copilot, one token each.** The client
ids are :data:`quill.core.ai.copilot_auth.CLIENT_IDS` -- the same OAuth App
per app that My GitHub Copilot signs in through, so the approval page names
"QUILL" or "QUILL Lite" either way. The tokens stay apart: Copilot's is
``read:user`` in ``SecretRef("copilot", <slug>)``, and the Workbench's is the
scope set below, saved by the account flow with
:func:`quill.core.github.accounts.save_github_account`, exactly as a pasted
token would be. Signing out of one leaves the other alone.

**Nothing is stored here.** :meth:`WorkbenchSignIn.wait` returns the token; the
caller asks GitHub whose it is and only then saves it, the same check a pasted
token goes through.

**Its own poster.** The device and token endpoints are posted through
:func:`post_github_form`, which reuses :func:`quill.core.ai.oauth_poster.post_form`
for the form encoding and JSON parsing but opens the request itself: only the
two fixed github.com addresses, verified TLS, and redirects refused, so a
token GitHub has just issued can never be handed to another host. That opener
is the Workbench's reviewed egress site
(``core/github/oauth_sign_in.py::_github_opener``).

Both blocking calls belong on a worker thread. wx-free and strict-typed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.ai import copilot_auth
from quill.core.ai.device_login import (
    STATUS_AUTHORIZED,
    STATUS_DENIED,
    STATUS_EXPIRED,
    DeviceCodeGrant,
    DeviceFlowConfig,
    request_device_code,
    run_device_login,
    spoken_code,
)
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

__all__ = [
    "DEVICE_PAGE",
    "WORKBENCH_SCOPES",
    "WORKBENCH_SCOPE",
    "GitHubSignInCancelled",
    "GitHubSignInFailed",
    "GitHubSignInUnavailable",
    "WorkbenchSignIn",
    "is_available",
    "post_github_form",
    "sign_in_unavailable_message",
    "spoken_code",
    "workbench_device_flow_config",
]

Poster = Callable[[str, dict[str, str]], dict[str, Any]]

#: Where the person types the code. GitHub also returns it as
#: ``verification_uri``; this is the fallback and what the guides name.
DEVICE_PAGE = "https://github.com/login/device"

#: The scopes the Workbench asks for, each with the shipped feature that needs
#: it. Checked against Waves 1 to 4 and PR 1791 on 2026-11-07: the smallest set
#: under which every Workbench command works. GitHub shows these on the
#: approval page, so a scope earns its place by a command, never "in case".
WORKBENCH_SCOPES: tuple[tuple[str, str], ...] = (
    (
        "repo",
        "Private repositories, and every write: issues, pull requests, reviews and "
        "merging, labels, milestones, releases, discussions, commit comments, "
        "Actions runs, secrets, variables and environments, saving a file, Copilot "
        "review and the Copilot agent. It also covers the notifications inbox and "
        "secret-scanning alerts, so neither needs a scope of its own.",
    ),
    (
        "workflow",
        "Saving a file under .github/workflows. GitHub refuses any change to a "
        "workflow file from a token without it, even with repo.",
    ),
    ("gist", "Explore's Gists view and the gist editor: create, edit, star and delete."),
    (
        "read:org",
        "Listing the organizations you belong to, for New Repository, Fork and "
        "an organization's repositories, including private memberships.",
    ),
    ("project", "The Projects (v2) dialog: reading boards and changing an item's fields."),
    (
        "security_events",
        "Code-scanning and Dependabot alerts: listing, dismissing and reopening them.",
    ),
    ("user:follow", "Follow and Unfollow on a person's profile."),
    (
        "delete_repo",
        "Delete Repository. Jeff chose one sign-in that covers every Workbench "
        "command (2026-11-08) over a second token for this one; the command "
        "still asks you to type the full name before it deletes anything.",
    ),
)
# notifications, read:user and user:email are covered by repo or unneeded: GET
# /user answers for any token, and nothing in the Workbench reads an email.

#: The space-separated scope string sent to GitHub.
WORKBENCH_SCOPE = " ".join(name for name, _reason in WORKBENCH_SCOPES)

_ALLOWED_URLS = frozenset({copilot_auth.GITHUB_DEVICE_AUTH_URL, copilot_auth.GITHUB_TOKEN_URL})
_TIMEOUT_SECONDS = 30.0
_MAX_RESPONSE_BYTES = 64_000


class GitHubSignInUnavailable(CodedError, ValueError):
    """This app has no GitHub OAuth registration, so Sign in with GitHub cannot run."""

    code = "QUILL-GITHUB-OAUTH-UNAVAILABLE"
    user_hint = "Use Add Token in Manage GitHub Accounts to sign in with a token instead."


class GitHubSignInFailed(CodedError):
    """The device flow ended without a token; ``args[0]`` is the one sentence to say."""

    code = "QUILL-GITHUB-OAUTH-FAILED"
    user_hint = "Choose Sign In with GitHub again for a new code, or Add Token."


class GitHubSignInCancelled(CodedError):
    """The person pressed Cancel while QUILL was waiting for GitHub."""

    code = "QUILL-GITHUB-OAUTH-CANCELLED"


def is_available(agent_name: str = copilot_auth.DEFAULT_AGENT_NAME) -> bool:
    """True when *agent_name* has a GitHub registration to sign in with."""
    return copilot_auth.is_configured(agent_name)


def sign_in_unavailable_message(agent_name: str = copilot_auth.DEFAULT_AGENT_NAME) -> str:
    """The one sentence said when *agent_name* cannot use Sign in with GitHub."""
    name = agent_name.strip() or copilot_auth.DEFAULT_AGENT_NAME
    return (
        f"Sign in with GitHub is not available in this copy of {name}. "
        "Choose Add Token to sign in with a personal access token instead."
    )


def workbench_device_flow_config(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME,
) -> DeviceFlowConfig:
    """GitHub's device endpoints, this app's client id and the Workbench scopes.

    Raises :class:`GitHubSignInUnavailable` (a ``ValueError``) when
    *agent_name* has no client id, so callers check :func:`is_available` first.
    """
    cid = copilot_auth.client_id(agent_name)
    if not cid:
        raise GitHubSignInUnavailable(sign_in_unavailable_message(agent_name))
    return DeviceFlowConfig(
        client_id=cid,
        device_authorization_url=copilot_auth.GITHUB_DEVICE_AUTH_URL,
        token_url=copilot_auth.GITHUB_TOKEN_URL,
        scope=WORKBENCH_SCOPE,
    )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def _github_opener(request: Request) -> tuple[int, bytes]:
    """POST to one of GitHub's two fixed sign-in addresses; never follow a redirect."""
    url = request.full_url
    if url not in _ALLOWED_URLS or urlsplit(url).hostname != "github.com":
        raise GitHubSignInFailed("QUILL refused to send a sign-in request anywhere but GitHub.")
    opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
    try:
        with opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
            return int(getattr(response, "status", 200) or 200), response.read(_MAX_RESPONSE_BYTES)
    except HTTPError as error:
        if error.code in (301, 302, 303, 307, 308):
            raise GitHubSignInFailed(
                "GitHub redirected the sign-in, and QUILL did not follow it."
            ) from error
        # GitHub answers the token endpoint's "still waiting" with a JSON body
        # on an error status; read it so the state machine can classify it.
        return int(error.code), error.read(_MAX_RESPONSE_BYTES)


def post_github_form(url: str, fields: dict[str, str]) -> dict[str, Any]:
    """A :data:`quill.core.ai.device_login.Poster` for GitHub's sign-in endpoints."""
    from quill.core.ai.oauth_poster import post_form

    return post_form(url, fields, opener=_github_opener)


class WorkbenchSignIn:
    """One Sign in with GitHub attempt for one app. Make a new one for each attempt."""

    def __init__(
        self,
        agent_name: str = copilot_auth.DEFAULT_AGENT_NAME,
        *,
        poster: Poster | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.agent_name = agent_name or copilot_auth.DEFAULT_AGENT_NAME
        self._poster: Poster = poster or post_github_form
        self._clock = clock
        self.cancelled = threading.Event()

    def available(self) -> bool:
        return is_available(self.agent_name)

    def request_code(self) -> DeviceCodeGrant:
        """Ask GitHub for a code. Raises :class:`GitHubSignInUnavailable` with no client id."""
        config = workbench_device_flow_config(self.agent_name)
        try:
            return request_device_code(config, poster=self._poster)
        except CodedError:
            raise
        except Exception as error:  # noqa: BLE001 - the network, worded once
            raise GitHubSignInFailed(
                "GitHub did not give a sign-in code. Check your connection and try again."
            ) from error

    def cancel(self) -> None:
        """Stop waiting; :meth:`wait` raises :class:`GitHubSignInCancelled` at once."""
        self.cancelled.set()

    def _sleep(self, seconds: float) -> None:
        if self.cancelled.wait(seconds):
            raise GitHubSignInCancelled("Sign-in cancelled.")

    def wait(self, grant: DeviceCodeGrant) -> str:
        """Poll at GitHub's interval until the person answers; return the token.

        ``slow_down`` adds five seconds to the interval (RFC 8628, in
        :func:`run_device_login`). Raises :class:`GitHubSignInCancelled` on
        Cancel and :class:`GitHubSignInFailed` with one sentence otherwise.
        """
        config = workbench_device_flow_config(self.agent_name)
        if self.cancelled.is_set():
            raise GitHubSignInCancelled("Sign-in cancelled.")
        try:
            result = run_device_login(
                config, grant, poster=self._poster, clock=self._clock, sleeper=self._sleep
            )
        except CodedError:
            raise
        except Exception as error:  # noqa: BLE001 - the network, worded once
            raise GitHubSignInFailed(
                "GitHub stopped answering before the sign-in finished. "
                "Check your connection and try again."
            ) from error
        if result.status == STATUS_EXPIRED:
            raise GitHubSignInFailed(
                "The code expired before it was used. Choose Sign In with GitHub for a new one."
            )
        if result.status == STATUS_DENIED:
            raise GitHubSignInFailed(
                "The sign-in was declined on GitHub's page. Nothing was saved."
            )
        token = str((result.tokens or {}).get("access_token", "") or "").strip()
        if result.status != STATUS_AUTHORIZED or not token:
            detail = (result.error or "").strip().rstrip(".")
            raise GitHubSignInFailed(
                f"GitHub did not finish the sign-in: {detail}."
                if detail
                else "GitHub did not finish the sign-in."
            )
        return token
