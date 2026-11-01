"""GitHub Copilot sign-in: device-flow config, per-app client ids, token storage (AI-19).

This is the wx-free orchestration the onboarding dialog drives. It binds the
generic :mod:`quill.core.ai.device_login` state machine to GitHub's OAuth device
endpoints and keeps the resulting token in the OS secure store.

**One registration and one token per app.** Every QuillVille app signs in to
GitHub separately and appears by its own name on GitHub's approval page, so
each has its own OAuth App under Community Access and its own client id
(:data:`CLIENT_IDS`, keyed by the app's agent name -- the same name the app's
ChatGPT sign-in uses). GitHub allows ten tokens per user, app and scope; one
shared registration would let eleven apps sign each other out.

**Apart from the repository features.** The Copilot token lives in its own
store entry, ``SecretRef("copilot", <agent slug>)``, never in the GitHub
repository features' entry (:mod:`quill.core.github.token_store`). Signing out
of Copilot leaves the repository sign-in alone and the other way round.
Migration is deliberately a no-op on the data: before this split the Copilot
sign-in wrote into the shared repository entry, and that token simply stays
with the repository features; Copilot finds its own entry empty and asks for
its own sign-in once (:func:`needs_own_sign_in` says when that is the case).

**Never in the environment.** The token is not exported to ``os.environ``;
the Copilot pack reads it with :func:`stored_token` at session start and hands
it to the SDK as the explicit ``github_token`` argument, so no child process
can inherit it.

With no client id for an app, :func:`is_configured` is False and the dialog
says, in one sentence, that sign-in is not available yet
(:func:`sign_in_unavailable_message`) instead of presenting a broken flow.
"""

from __future__ import annotations

import os

from quill.core import paths
from quill.core.ai.chatgpt_state import slug_for
from quill.core.ai.device_login import DeviceFlowConfig
from quill.core.error_codes import CodedError
from quill.core.github.token_store import load_github_token
from quill.core.secrets import SecretRef, default_secrets_manager

__all__ = [
    "GITHUB_DEVICE_AUTH_URL",
    "GITHUB_TOKEN_URL",
    "GITHUB_SCOPE",
    "DEFAULT_AGENT_NAME",
    "CLIENT_IDS",
    "CLIENT_ID_OVERRIDE_ENV",
    "CopilotSignInUnavailable",
    "client_id",
    "is_configured",
    "sign_in_unavailable_message",
    "github_device_flow_config",
    "token_ref",
    "persist_token",
    "stored_token",
    "forget_token",
    "needs_own_sign_in",
]

GITHUB_DEVICE_AUTH_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
# Copilot access is entitlement-based on the account; read:user is enough to
# identify the signed-in user and exchange the device code.
GITHUB_SCOPE = "read:user"

#: The agent name QUILL itself signs in under.
DEFAULT_AGENT_NAME = "QUILL"

#: One GitHub OAuth App client id per app, keyed by the app's agent name.
#: Jeff supplies these from the Community-Access organization's OAuth Apps
#: (one registration per app, Device Flow enabled, no client secret -- a
#: client id is public and grants nothing). An empty value means that app's
#: in-app sign-in is not available yet.
CLIENT_IDS: dict[str, str] = {
    "QUILL": "",
    "QUILL Lite": "",
    "QUILL Radio": "",
    "QUILL Cast": "",
    "QUILL Studio": "",
    "QUILL Transcribe": "",
    "QUILL Converter": "",
    "QUILL Player": "",
    "QUILL Weather": "",
    "QUILL Inkwell": "",
    "QUILL Beacon": "",
    "QUILL Social": "",
}

#: Developer override for the client id. Honoured only in a dev build
#: (``QUILL_DEV_BUILD=1``), like ``QUILL_DATA_DIR``: a release build must not
#: let an environment variable point a user's sign-in at another registration.
CLIENT_ID_OVERRIDE_ENV = "QUILL_GITHUB_CLIENT_ID"

_STORE_NAMESPACE = "copilot"


class CopilotSignInUnavailable(CodedError, ValueError):
    """This app has no GitHub OAuth client id yet, so in-app sign-in cannot run."""

    code = "QUILL-AI-COPILOT-SIGNIN-UNAVAILABLE"
    user_hint = (
        "Sign in once with the Copilot or GitHub command-line tool, "
        "or wait for a QUILL update that carries the sign-in."
    )


def client_id(agent_name: str = DEFAULT_AGENT_NAME) -> str:
    """The GitHub OAuth App client id for *agent_name* ("" when it has none).

    The dev-build override wins; otherwise the built-in table answers.
    """
    if paths._DEV_BUILD:
        override = os.environ.get(CLIENT_ID_OVERRIDE_ENV, "").strip()
        if override:
            return override
    return CLIENT_IDS.get(agent_name.strip(), "").strip()


def is_configured(agent_name: str = DEFAULT_AGENT_NAME) -> bool:
    """True when *agent_name* has a client id to drive the device flow."""
    return bool(client_id(agent_name))


def sign_in_unavailable_message(agent_name: str = DEFAULT_AGENT_NAME) -> str:
    """The one sentence spoken when *agent_name* cannot sign in from inside the app."""
    name = agent_name.strip() or DEFAULT_AGENT_NAME
    return (
        f"Signing in to GitHub from inside {name} is not available yet. "
        "If you have signed in with the Copilot or GitHub command-line tool, "
        "Copilot still works."
    )


def github_device_flow_config(agent_name: str = DEFAULT_AGENT_NAME) -> DeviceFlowConfig:
    """Build the :class:`DeviceFlowConfig` for GitHub's device endpoints.

    Raises :class:`CopilotSignInUnavailable` (a ``ValueError``) when
    *agent_name* has no client id, so callers check :func:`is_configured` first.
    """
    cid = client_id(agent_name)
    if not cid:
        raise CopilotSignInUnavailable(sign_in_unavailable_message(agent_name))
    return DeviceFlowConfig(
        client_id=cid,
        device_authorization_url=GITHUB_DEVICE_AUTH_URL,
        token_url=GITHUB_TOKEN_URL,
        scope=GITHUB_SCOPE,
    )


def token_ref(agent_name: str = DEFAULT_AGENT_NAME) -> SecretRef:
    """The secure-store entry for *agent_name*'s Copilot token.

    ``"QUILL Lite"`` -> ``quill-copilot-quill-lite``; never the repository
    features' ``quill-github-token``.
    """
    return SecretRef(_STORE_NAMESPACE, slug_for(agent_name or DEFAULT_AGENT_NAME))


def persist_token(token: str, agent_name: str = DEFAULT_AGENT_NAME) -> bool:
    """Store *agent_name*'s Copilot token. Returns True when the write landed."""
    token = token.strip()
    if not token:
        return False
    manager = default_secrets_manager()
    ref = token_ref(agent_name)
    manager.set(ref, token)
    return manager.get(ref) == token


def stored_token(agent_name: str = DEFAULT_AGENT_NAME) -> str | None:
    """*agent_name*'s stored Copilot token, or None.

    Reads only the Copilot entry: a token the repository features hold is
    never borrowed, which is the whole migration (see the module docstring).
    """
    value = default_secrets_manager().get(token_ref(agent_name))
    return value.strip() if value and value.strip() else None


def forget_token(agent_name: str = DEFAULT_AGENT_NAME) -> bool:
    """Sign *agent_name* out of Copilot. The repository token is untouched."""
    return default_secrets_manager().delete(token_ref(agent_name))


def needs_own_sign_in(agent_name: str = DEFAULT_AGENT_NAME) -> bool:
    """True when the old shared token exists but this app's Copilot entry is empty.

    That is the one-time migration state: the person signed in before the
    split, the token stayed with the repository features, and Copilot now asks
    for its own sign-in once.
    """
    if stored_token(agent_name):
        return False
    try:
        return bool(load_github_token())
    except Exception:  # noqa: BLE001 - a locked or missing store just means "no"
        return False
