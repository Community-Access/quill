"""The verb registry (verbosity §15).

:class:`VerbRegistry` owns the set of known verbs and is the lookup the engine
and the prefs UI use. Duplicate registration is a structured error, never a
silent overwrite, so two features can't quietly fight over a verb id.

Pure and wx-free.
"""

from __future__ import annotations

from quill.core.verbosity.verbs import BUILTIN_VERBS, VerbSpec

__all__ = ["DuplicateVerbError", "VerbRegistry", "default_registry"]


class DuplicateVerbError(ValueError):
    """Raised when a verb id is registered twice."""

    def __init__(self, verb_id: str) -> None:
        super().__init__(f"Verb '{verb_id}' is already registered")
        self.verb_id = verb_id


class VerbRegistry:
    """An ordered, lookup-by-id collection of :class:`VerbSpec`."""

    def __init__(self) -> None:
        self._verbs: dict[str, VerbSpec] = {}

    def register(self, verb: VerbSpec) -> None:
        """Register ``verb``; raise :class:`DuplicateVerbError` on a repeat id."""
        if verb.id in self._verbs:
            raise DuplicateVerbError(verb.id)
        self._verbs[verb.id] = verb

    def get(self, verb_id: str) -> VerbSpec | None:
        """Return the verb registered under ``verb_id``, or ``None``."""
        return self._verbs.get(verb_id)

    def all(self) -> tuple[VerbSpec, ...]:
        """Return every registered verb, sorted by id."""
        return tuple(self._verbs[key] for key in sorted(self._verbs))

    def __len__(self) -> int:
        return len(self._verbs)

    def __contains__(self, verb_id: object) -> bool:
        return verb_id in self._verbs


def default_registry() -> VerbRegistry:
    """Build a registry pre-populated with the built-in verb catalog."""
    registry = VerbRegistry()
    for verb in BUILTIN_VERBS:
        registry.register(verb)
    return registry
