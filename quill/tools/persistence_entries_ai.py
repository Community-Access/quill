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
}
