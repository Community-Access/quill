"""Whether My GitHub Copilot is ready in this app, read locally (codex.md 10A.12).

Three things must all be true before a request can go to Copilot, and each
missing one has its own row state in Choose Your AI:

* **this app has a GitHub client id** (:func:`copilot_auth.is_configured`):
  without Jeff's OAuth App registration for the app there is no sign-in at
  all, so the row reads "not available yet";
* **the engine ships in this build**: the SDK (``github-copilot-sdk``, bundled
  in the shared runtime since Phase 2) is importable, and the Copilot CLI is
  bundled in ``tools\\copilot`` or a developer named one with
  ``COPILOT_CLI_PATH`` -- also "not available yet" when absent;
* **this app holds its own token** (:func:`copilot_auth.stored_token`):
  otherwise the row reads "not set up".

Two outcomes GitHub reports are kept on disk per app, so the row says them
after a restart: **ended by GitHub** (a 401, revoked or expired token; the
token is forgotten and the row reads "signed out by GitHub") and **not
available for your account** (an organisation or plan has Copilot switched
off, R15). Both live in ``<app data>/ai/copilot-<slug>.json``, written with
``write_json_atomic``; a fresh sign-in clears them.

Nothing here makes a network call, starts the CLI, or hashes the bundle (the
SHA-256 pin is checked at launch by
:func:`copilot_runtime.cli_path_for_launch`). wx-free and strict-typed.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.ai import copilot_auth
from quill.core.ai.chatgpt_state import slug_for
from quill.core.ai.copilot_runtime import resolve_cli_path
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "CopilotMarks",
    "CopilotReadiness",
    "clear_marks",
    "connection_facts_fields",
    "load_marks",
    "mark_ended_by_github",
    "mark_policy_off",
    "readiness",
    "sdk_bundled",
]

_STATE_DIR = "ai"


def sdk_bundled() -> bool:
    """True when the Copilot SDK is importable here (found, not imported)."""
    try:
        return importlib.util.find_spec("copilot") is not None
    except (ImportError, ValueError):
        return False


@dataclass(frozen=True, slots=True)
class CopilotMarks:
    """What GitHub last said about this app's Copilot, kept across restarts."""

    ended_by_github: bool = False
    policy_off: bool = False


def _data_dir(data_dir: Path | None) -> Path:
    if data_dir is not None:
        return data_dir
    from quill.core.paths import app_data_dir

    return app_data_dir()


def _marks_path(agent_name: str, data_dir: Path | None) -> Path:
    slug = slug_for(agent_name or copilot_auth.DEFAULT_AGENT_NAME)
    return _data_dir(data_dir) / _STATE_DIR / f"copilot-{slug}.json"


def load_marks(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME, *, data_dir: Path | None = None
) -> CopilotMarks:
    """This app's marks; an unreadable or missing file means none."""
    data: Any = read_json(_marks_path(agent_name, data_dir), default={})
    if not isinstance(data, dict):
        return CopilotMarks()
    return CopilotMarks(
        ended_by_github=bool(data.get("ended_by_github", False)),
        policy_off=bool(data.get("policy_off", False)),
    )


def _save(agent_name: str, marks: CopilotMarks, data_dir: Path | None) -> None:
    path = _marks_path(agent_name, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        path, {"ended_by_github": marks.ended_by_github, "policy_off": marks.policy_off}
    )


def mark_ended_by_github(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME, *, data_dir: Path | None = None
) -> None:
    """GitHub refused the token: forget it and remember why (10A.5).

    No retry and no fallback follow; the row reads "signed out by GitHub"
    until the person signs in again.
    """
    try:
        copilot_auth.forget_token(agent_name)
    except Exception:  # noqa: BLE001 - a locked store still records the ending
        pass
    _save(agent_name, CopilotMarks(ended_by_github=True), data_dir)


def mark_policy_off(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME, *, data_dir: Path | None = None
) -> None:
    """GitHub said Copilot is switched off for this account (R15). The token stays."""
    _save(agent_name, CopilotMarks(policy_off=True), data_dir)


def clear_marks(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME, *, data_dir: Path | None = None
) -> None:
    """Forget both marks: called after a sign-in, and after a request that worked."""
    path = _marks_path(agent_name, data_dir)
    if path.exists():
        _save(agent_name, CopilotMarks(), data_dir)


@dataclass(frozen=True, slots=True)
class CopilotReadiness:
    """Each precondition, so the window can say which one is missing."""

    client_id: bool
    sdk: bool
    cli: bool
    signed_in: bool
    marks: CopilotMarks = CopilotMarks()

    @property
    def available(self) -> bool:
        """The build and the registration allow Copilot at all."""
        return self.client_id and self.sdk and self.cli

    @property
    def ready(self) -> bool:
        """A request could go to Copilot now."""
        return self.available and self.signed_in and not self.marks.policy_off


def readiness(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME, *, data_dir: Path | None = None
) -> CopilotReadiness:
    """Read every precondition for *agent_name* from this computer (no network)."""
    try:
        signed_in = bool(copilot_auth.stored_token(agent_name))
    except Exception:  # noqa: BLE001 - an unreadable store is "not signed in"
        signed_in = False
    try:
        cli = resolve_cli_path() is not None
    except OSError:
        cli = False
    marks = load_marks(agent_name, data_dir=data_dir)
    if signed_in and marks.ended_by_github:
        marks = CopilotMarks(policy_off=marks.policy_off)  # a newer sign-in wins
    return CopilotReadiness(
        client_id=copilot_auth.is_configured(agent_name),
        sdk=sdk_bundled(),
        cli=cli,
        signed_in=signed_in,
        marks=marks,
    )


def connection_facts_fields(
    agent_name: str = copilot_auth.DEFAULT_AGENT_NAME, *, data_dir: Path | None = None
) -> dict[str, bool]:
    """The Copilot fields of :class:`~quill.core.ai.connection_choice.ConnectionFacts`.

    ``ConnectionFacts(stored=..., ..., **connection_facts_fields(agent_name))``.
    """
    state = readiness(agent_name, data_dir=data_dir)
    return {
        "copilot_available": state.available,
        "copilot_signed_in": state.signed_in,
        "copilot_ended": state.marks.ended_by_github and not state.signed_in,
        "copilot_policy_off": state.marks.policy_off,
    }
