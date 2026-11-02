"""The ChatGPT plan's reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 -- extract, never
rebaseline -- when the local request count (codex.md decision 24) joined the
sign-in state: both are one small file per app in ``<data>/ai``, kept apart
from the refresh token, which goes to the OS credential store.
"""

from __future__ import annotations

AI_ENTRIES: dict[str, str] = {
    # The ChatGPT sign-in's non-secret state (<data>/ai/chatgpt.json): the
    # issued client id, the host id, the account label, the chosen model, the
    # web-search switch and whether OpenAI ended the sign-in. Same shape and
    # same reasons as the gateway session; the refresh token goes to the OS
    # store. One file per app since 2026-10-02 (chatgpt-<slug>.json).
    "core/ai/chatgpt_state.py::save_state": "marker",
    # The local ChatGPT request count (<data>/ai/chatgpt-usage-<slug>.json):
    # fourteen days of request and token counts under a version stamp, rebuilt
    # from zero if lost, and never used to infer a limit.
    "core/ai/chatgpt_usage.py::record_request": "cache",
    # What GitHub last said about this app's Copilot (<data>/ai/copilot-<slug>.json):
    # two flags, "ended by GitHub" and "not available for your account", so the
    # Choose Your AI row says them after a restart. No token; a sign-in clears it.
    "core/ai/copilot_state.py::_save": "marker",
    # The family prompt store (codex.md decision 18): the user prompts in
    # <app data>/prompts.json, in the Prompt Library's own shape, every unknown
    # key kept on write -- user-created, additive content. Its sidecar
    # prompts-family.json holds each prompt's `needs` and the migration's
    # done/checked record under a version stamp; lost, it reads as no needs
    # and an unchecked migration, which only delays retiring the old files.
    "core/ai/family_prompts.py::_write_prompts": "content",
    "core/ai/family_prompts.py::_write_meta": "marker",
    # My own key's server address for a custom service or Ollama on this
    # computer (decision 20), assistant-own-key-hosts.json beside the AI Hub's
    # assistant-connection.json: a schema_version envelope and one address per
    # provider, never a key. Lost, each provider reads its default address.
    "core/ai/own_key_providers.py::save_host": "versioned",
    # <app data>/<app>-ai.json: Quill Weather's, Quill Converter's, Quill Media
    # Player's, Quill Inkwell's and QuillBeacon's own Choose Your AI choice and
    # picture consent (codex.md Phase 3), as Studio's studio-ai.json: names and
    # ids only, never a key or a token; no version stamp yet.
    "core/ai/app_ai_settings.py::save_app_ai_settings": "needs-versioning",
}
