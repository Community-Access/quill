"""Quick-switch the active AI engine (harness) — the plumbing behind the hotkey
and the status-bar cell (Phase 6 UI).

Users asked to flip between the agentic engines they have — Native, GitHub
Copilot, Claude Agent, OpenAI Agents — the way you flip a layout: one keystroke,
or one click on a status-bar cell, with a spoken confirmation. This module is the
wx-free core of that. It composes the :class:`~quill.core.ai.harness.HarnessRegistry`
(Native plus any installed SDK packs) into an ordered list of switch *targets*,
persists the user's preferred engine under ``<app data>/ai/active-harness.json``,
and round-robins to the next available engine.

Two ideas keep this honest:

* **Preferred vs. running.** The user may *prefer* an engine whose SDK is not
  installed yet (they picked Copilot before installing the pack). The preference
  is persisted as-is so the UI can offer to install/sign in; the *running* engine
  is always what ``registry.resolve`` actually returns (Native in a bare install),
  so QUILL never breaks by selecting an absent engine.
* **Cycle only available.** The hotkey cycles among engines that are ready to run;
  picking an unavailable engine is an explicit choice in the Hub that triggers
  onboarding (:mod:`quill.core.ai.sdk_install`), not a silent no-op.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.ai.harness import Harness, HarnessRegistry
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "SwitchTarget",
    "AUTO",
    "preferred_harness_id",
    "save_preferred_harness_id",
    "list_targets",
    "active_target",
    "set_active",
    "cycle_next",
    "announce_active",
    "announce_switch",
]

AUTO = "auto"
_CHOICE_FILE = "active-harness.json"


@dataclass(frozen=True, slots=True)
class SwitchTarget:
    """One selectable AI engine and its readiness."""

    harness_id: str
    display_name: str
    available: bool
    reason: str | None  # install/sign-in hint when not available, else None
    active: bool  # True for the engine that would actually run right now


def _choice_path() -> Path:
    return app_data_dir() / "ai" / _CHOICE_FILE


def preferred_harness_id() -> str:
    """Return the saved preferred engine id, or ``"auto"`` (let the registry pick)."""
    raw = read_json(_choice_path(), default={})
    if isinstance(raw, dict):
        choice = raw.get("harness")
        if isinstance(choice, str) and choice.strip():
            return choice.strip()
    return AUTO


def save_preferred_harness_id(harness_id: str) -> None:
    """Persist the preferred engine id (``"auto"`` or any harness id)."""
    write_json_atomic(_choice_path(), {"harness": harness_id})


def _resolved(registry: HarnessRegistry) -> Harness | None:
    """The engine that would actually run for the saved preference."""
    return registry.resolve(preferred_harness_id())


def list_targets(registry: HarnessRegistry) -> list[SwitchTarget]:
    """All registered engines, in registration order, with readiness and the
    running engine flagged ``active``.

    The order is stable (Native first in a normal wiring), which is what the
    hotkey cycles through and the Hub lists.
    """
    running = _resolved(registry)
    running_id = running.id if running is not None else None
    targets: list[SwitchTarget] = []
    for harness in registry.all():
        available, reason = harness.is_available()
        targets.append(
            SwitchTarget(
                harness_id=harness.id,
                display_name=harness.display_name,
                available=available,
                reason=reason,
                active=harness.id == running_id,
            )
        )
    return targets


def active_target(registry: HarnessRegistry) -> SwitchTarget | None:
    """The currently running engine as a :class:`SwitchTarget`, or ``None`` if no
    engine is available at all (an empty registry)."""
    for target in list_targets(registry):
        if target.active:
            return target
    return None


def set_active(registry: HarnessRegistry, harness_id: str) -> SwitchTarget:
    """Set the preferred engine and persist it.

    Accepts any **registered** engine id (or ``"auto"``), even one whose SDK is
    not installed — the returned target's ``available`` flag tells the caller
    whether to launch onboarding. Raises :class:`ValueError` for an id the
    registry does not know.
    """
    if harness_id != AUTO and registry.get(harness_id) is None:
        raise ValueError(f"Unknown AI engine: {harness_id!r}")
    save_preferred_harness_id(harness_id)
    # Report the chosen engine's own readiness (not the resolved fallback), so the
    # UI can offer to install a pack the user just picked.
    if harness_id == AUTO:
        target = active_target(registry)
        if target is None:
            raise ValueError("No AI engine is available.")
        return target
    harness = registry.get(harness_id)
    assert harness is not None  # guarded above
    available, reason = harness.is_available()
    running = _resolved(registry)
    return SwitchTarget(
        harness_id=harness.id,
        display_name=harness.display_name,
        available=available,
        reason=reason,
        active=running is not None and running.id == harness.id,
    )


def cycle_next(registry: HarnessRegistry) -> SwitchTarget:
    """Advance to the next **available** engine (round-robin) and persist it.

    With one available engine this is a no-op that re-confirms it. Raises
    :class:`ValueError` if nothing is available.
    """
    available = [t for t in list_targets(registry) if t.available]
    if not available:
        raise ValueError("No AI engine is available.")
    current_index = next((i for i, t in enumerate(available) if t.active), -1)
    nxt = available[(current_index + 1) % len(available)]
    return set_active(registry, nxt.harness_id)


def announce_active(target: SwitchTarget | None) -> str:
    """A spoken description of the running engine (A11Y-1 grammar)."""
    if target is None:
        return "No AI engine is available."
    return f"AI engine: {target.display_name}."


def announce_switch(target: SwitchTarget) -> str:
    """A spoken confirmation of a switch.

    When the user selected an engine whose pack is not installed, the message
    names what is needed instead of pretending the switch took effect.
    """
    if not target.available:
        reason = target.reason or "it is not installed yet"
        return f"{target.display_name} is not ready: {reason}."
    return f"Switched AI engine to {target.display_name}."
