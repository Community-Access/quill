"""One-provider-truth key migration (§7), extracted from ``assistant_ai`` (GATE-11).

The 2.0 platform reads one key per provider from the canonical
``provider_credential_target`` slot. Older keys may sit in the lightweight
``ai_chat`` slots (``quill-<provider>-api-key``) or the single global active-key
slot. :func:`consolidate_provider_keys` copies those into the canonical slots so
every AI surface agrees.

The migration is **reversible, non-destructive, and idempotent**: it only writes a
canonical slot that is currently empty, never overwrites a set one, and never
deletes the legacy secret (clearing the canonical slot reverts it). It is kept in
its own module so ``assistant_ai`` stays under its size budget; it reaches back
into ``assistant_ai`` for the credential primitives (so tests that monkeypatch
those still take effect).
"""

from __future__ import annotations

from quill.core import assistant_ai as _aai

__all__ = ["consolidate_provider_keys", "consolidate_provider_keys_quietly"]

# Legacy credential-store targets older builds (and ``ai_chat``) used.
_LEGACY_PROVIDER_TARGETS: dict[str, str] = {
    "openrouter": "quill-openrouter-api-key",
    "openai": "quill-openai-api-key",
    "ollama_cloud": "quill-ollama-api-key",
}


def consolidate_provider_keys() -> list[str]:
    """Fill empty canonical per-provider key slots from legacy storage.

    Returns the providers migrated. Never raises — a credential-store hiccup must
    not break startup.
    """
    migrated: list[str] = []
    try:
        for provider, legacy_target in _LEGACY_PROVIDER_TARGETS.items():
            if _aai.load_provider_api_key(provider):
                continue
            legacy_value = (_aai._cs_load(legacy_target) or "").strip()
            if legacy_value:
                _aai._cs_save(_aai.provider_credential_target(provider), legacy_value)
                migrated.append(provider)

        active = _aai.load_assistant_connection_settings().provider.strip().lower()
        if active and active != "off" and not _aai.load_provider_api_key(active):
            global_value = (_aai.load_assistant_api_key() or "").strip()
            if global_value:
                _aai._cs_save(_aai.provider_credential_target(active), global_value)
                if active not in migrated:
                    migrated.append(active)
    except Exception:  # noqa: BLE001 - a migration must never break startup
        return migrated
    return migrated


def consolidate_provider_keys_quietly() -> None:
    """Run :func:`consolidate_provider_keys`, swallowing any error (startup hook)."""
    try:
        consolidate_provider_keys()
    except Exception:  # noqa: BLE001 - key migration must never break startup
        pass
