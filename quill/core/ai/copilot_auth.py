"""GitHub Copilot sign-in: device-flow config, polling, and token handoff (AI-19).

This is the wx-free orchestration the onboarding dialog drives. It binds the
generic :mod:`quill.core.ai.device_login` state machine to GitHub's OAuth device
endpoints, persists the resulting token in the OS secure store (reusing the
GitHub token store, DPAPI on Windows / Keychain on macOS), and hands the token to
the Copilot SDK for the running session by exporting it to the environment the
SDK reads.

Auth model: the ``copilot`` SDK authenticates as the user's GitHub account. The
cleanest accessible path (the AI-19 win) is the OAuth 2.0 Device Authorization
Grant — a short, speakable code the user types in their browser — rather than a
pasted token. Driving it needs a registered GitHub OAuth App **client id**; it is
read from ``QUILL_GITHUB_CLIENT_ID`` so the production app id is configured at
build/deploy time rather than hard-coded here. With no client id configured,
:func:`is_configured` is False and the dialog points the user at the SDK's own
``copilot`` CLI sign-in instead of presenting a broken flow.
"""

from __future__ import annotations

import os

from quill.core.ai.device_login import DeviceFlowConfig
from quill.core.github.token_store import (
    delete_github_token,
    load_github_token,
    save_github_token,
)

__all__ = [
    "GITHUB_DEVICE_AUTH_URL",
    "GITHUB_TOKEN_URL",
    "GITHUB_SCOPE",
    "client_id",
    "is_configured",
    "github_device_flow_config",
    "persist_token",
    "apply_token_to_environment",
    "stored_token",
    "forget_token",
]

GITHUB_DEVICE_AUTH_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
# Copilot access is entitlement-based on the account; read:user is enough to
# identify the signed-in user and exchange the device code.
GITHUB_SCOPE = "read:user"

# Environment variables the Copilot SDK / GitHub tooling reads for a token.
_SDK_TOKEN_ENV_VARS = ("GITHUB_TOKEN", "GH_TOKEN")


def client_id() -> str:
    """The GitHub OAuth App client id, from the environment (empty if unset)."""
    return os.environ.get("QUILL_GITHUB_CLIENT_ID", "").strip()


def is_configured() -> bool:
    """True when a client id is available to drive the device flow."""
    return bool(client_id())


def github_device_flow_config() -> DeviceFlowConfig:
    """Build the :class:`DeviceFlowConfig` for GitHub's device endpoints.

    Raises :class:`ValueError` when no client id is configured, so callers check
    :func:`is_configured` first and offer the SDK's own sign-in as the fallback.
    """
    cid = client_id()
    if not cid:
        raise ValueError(
            "No GitHub OAuth client id configured (set QUILL_GITHUB_CLIENT_ID). "
            "Use the Copilot CLI sign-in instead."
        )
    return DeviceFlowConfig(
        client_id=cid,
        device_authorization_url=GITHUB_DEVICE_AUTH_URL,
        token_url=GITHUB_TOKEN_URL,
        scope=GITHUB_SCOPE,
    )


def persist_token(token: str) -> bool:
    """Store the access token in the OS secure store. Returns True on success."""
    if not token.strip():
        return False
    return save_github_token(token.strip())


def apply_token_to_environment(token: str) -> None:
    """Export the token so the Copilot SDK picks it up for this session.

    The SDK authenticates as the user's GitHub account; setting the standard
    token environment variables bridges a just-completed sign-in to the SDK
    without requiring a restart. Persisted storage (:func:`persist_token`) covers
    future sessions.
    """
    if not token.strip():
        return
    for name in _SDK_TOKEN_ENV_VARS:
        os.environ[name] = token.strip()


def stored_token() -> str | None:
    """Return the previously stored token, or None."""
    return load_github_token()


def forget_token() -> bool:
    """Remove the stored token and clear it from this session's environment."""
    for name in _SDK_TOKEN_ENV_VARS:
        os.environ.pop(name, None)
    return delete_github_token()
