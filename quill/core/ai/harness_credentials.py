"""API-key storage + environment application for env-var-authenticated SDK
harnesses (OpenAI Agents SDK, Claude Agent SDK).

Unlike Copilot (OAuth device flow, its own token store), these two harnesses
authenticate the way their upstream SDKs always have: reading a well-known
environment variable directly (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``) with
no QUILL-specific hook to inject a key at call time. So the bridge here has two
halves, mirroring :mod:`quill.core.ai.copilot_auth`'s token/environment split:
persist the key in QUILL's existing per-provider secure store (reusing
:func:`quill.core.assistant_ai.save_provider_api_key`, keyed by the harness's
``pack_id`` exactly like a chat provider), and export it to the process
environment so the SDK picks it up immediately, without requiring a restart.
"""

from __future__ import annotations

import os

__all__ = [
    "SUPPORTED_PACK_IDS",
    "env_var_names",
    "persist_key",
    "apply_key_to_environment",
    "stored_key",
    "forget_key",
    "apply_all_stored_keys",
]

# The environment variable(s) each pack's SDK reads for authentication.
_ENV_VARS: dict[str, tuple[str, ...]] = {
    "openai_agents": ("OPENAI_API_KEY",),
    "claude_agent_sdk": ("ANTHROPIC_API_KEY",),
}

SUPPORTED_PACK_IDS = tuple(_ENV_VARS)


def env_var_names(pack_id: str) -> tuple[str, ...]:
    """The environment variable(s) *pack_id*'s SDK reads, or () if unknown."""
    return _ENV_VARS.get(pack_id, ())


def persist_key(pack_id: str, api_key: str) -> bool:
    """Store *api_key* for *pack_id* in QUILL's secure per-provider store."""
    from quill.core.assistant_ai import save_provider_api_key

    return save_provider_api_key(pack_id, api_key)


def stored_key(pack_id: str) -> str:
    """Return the previously stored key for *pack_id*, or "" if none."""
    from quill.core.assistant_ai import load_provider_api_key

    try:
        return load_provider_api_key(pack_id).strip()
    except Exception:  # noqa: BLE001 - a missing/locked key just means "none on hand"
        return ""


def apply_key_to_environment(pack_id: str, api_key: str) -> None:
    """Export *api_key* so *pack_id*'s SDK picks it up for this session.

    Persisted storage (:func:`persist_key`) covers future sessions via
    :func:`apply_all_stored_keys` at startup; this bridges a just-entered key
    to the SDK immediately, without requiring a restart.
    """
    key = api_key.strip()
    if not key:
        return
    for name in env_var_names(pack_id):
        os.environ[name] = key


def forget_key(pack_id: str) -> None:
    """Forget *pack_id*'s stored key and unset it from the environment."""
    from quill.core.assistant_ai import clear_provider_api_key

    clear_provider_api_key(pack_id)
    for name in env_var_names(pack_id):
        os.environ.pop(name, None)


def apply_all_stored_keys() -> None:
    """Apply every supported pack's previously stored key to the environment.

    Call once at startup so a key entered in an earlier session is already in
    place before the engine registry is built, the same way Copilot's stored
    GitHub token bridges to its SDK. A pack with no stored key is a no-op.
    """
    for pack_id in SUPPORTED_PACK_IDS:
        key = stored_key(pack_id)
        if key:
            apply_key_to_environment(pack_id, key)
