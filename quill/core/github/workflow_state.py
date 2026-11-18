"""Turning a workflow on and off (GitHub PRD 14.1: "Enable or disable a workflow").

GitHub keeps a workflow's state on the workflow itself: on (``active``), turned
off by someone (``disabled_manually``), turned off after sixty days with no
activity in the repository (``disabled_inactivity``), or off because the
repository is a fork (``disabled_fork``). :func:`set_enabled` turns one on or
off with ``PUT .../actions/workflows/{id}/enable`` or ``.../disable``; a
workflow turned off runs on no trigger at all, not even Run Workflow, until it
is turned on again.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.workbench_api import GitHubApi

__all__ = ["STATE_WORDS", "is_enabled", "set_enabled", "state_words"]

STATE_WORDS: dict[str, str] = {
    "active": "on",
    "disabled_manually": "turned off",
    "disabled_inactivity": "turned off by GitHub after 60 days without activity",
    "disabled_fork": "off, because this repository is a fork",
}


def state_words(state: str) -> str:
    return STATE_WORDS.get(state, state.replace("_", " ") or "unknown")


def is_enabled(state: str) -> bool:
    return state == "active"


def set_enabled(api: GitHubApi, repository: str, workflow_id: int, name: str, on: bool) -> str:
    """Turn workflow *workflow_id* on or off; returns the sentence to say."""
    verb = "enable" if on else "disable"
    api.rest("PUT", f"/repos/{repository}/actions/workflows/{int(workflow_id)}/{verb}")
    if on:
        return f"Turned on {name}. It runs on its triggers again."
    return f"Turned off {name}. It runs on no trigger until it is turned on again."
