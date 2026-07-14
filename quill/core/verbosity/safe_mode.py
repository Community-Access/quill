"""Verbosity Safe Mode and scoped resets (verbosity §29).

Safe Mode temporarily ignores every custom verbosity override and falls back to
the built-in behavior, without deleting the user's customizations — a one-switch
escape hatch when a custom setup misbehaves. The scoped reset helpers return a
new :class:`CustomProfile` with one verb, one chord, or everything removed, so
the caller can offer "reset this verb" / "reset this chord" / "restore built-in
defaults" non-destructively (export-before-reset is the UI's job).

``QUILL_SAFE_MODE=1`` (or ``QUILL_VERBOSITY_SAFE_MODE=1``) starts QUILL with
built-in verbosity only.

Pure and wx-free.
"""

from __future__ import annotations

import os
from dataclasses import replace

from quill.core.verbosity.profiles import CustomProfile

__all__ = ["VerbositySafeMode", "reset_verb", "reset_chord", "restore_builtin"]

_ENV_VARS = ("QUILL_SAFE_MODE", "QUILL_VERBOSITY_SAFE_MODE")


class VerbositySafeMode:
    """Toggle that makes the engine ignore custom verbosity overrides."""

    def __init__(self, *, active: bool = False) -> None:
        self._active = active

    @property
    def is_active(self) -> bool:
        return self._active

    def enter(self) -> None:
        self._active = True

    def exit(self) -> None:
        self._active = False

    @staticmethod
    def from_env(environ: dict[str, str] | None = None) -> bool:
        """True when a Safe Mode environment variable is set to a truthy value."""
        env = environ if environ is not None else dict(os.environ)
        return any(env.get(name, "").strip().lower() in {"1", "true", "yes"} for name in _ENV_VARS)


def reset_verb(custom: CustomProfile, verb_id: str) -> CustomProfile:
    """Return a copy of ``custom`` with ``verb_id``'s per-verb override removed."""
    overrides = {k: v for k, v in custom.per_verb_overrides.items() if k != verb_id}
    data_order = {k: v for k, v in custom.data_order.items() if k != verb_id}
    return replace(custom, per_verb_overrides=overrides, data_order=data_order)


def reset_chord(custom: CustomProfile, chord: str) -> CustomProfile:
    """Return a copy of ``custom`` with ``chord``'s per-chord override removed."""
    overrides = {k: v for k, v in custom.per_chord_overrides.items() if k != chord}
    return replace(custom, per_chord_overrides=overrides)


def restore_builtin(custom: CustomProfile) -> CustomProfile:
    """Return a copy of ``custom`` stripped of every override (built-ins only)."""
    return replace(
        custom,
        per_verb_overrides={},
        per_chord_overrides={},
        templates={},
        data_order={},
    )
