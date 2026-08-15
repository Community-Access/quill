"""Abbreviations a Quillin contributes: built from manifests, never persisted.

Extracted from :mod:`quill.core.abbreviations` when per-application scoping
pushed that module to its GATE-11 ceiling. It is a real seam rather than a
convenient one: everything here concerns entries that come from an **extension
manifest**, are rebuilt on every load, and are never written to the user's file
-- which is a different lifetime from every other abbreviation in QUILL, and the
reason uninstalling a Quillin can take its abbreviations with it.

Consumed by two hosts now: QUILL's editor
(``ui/main_frame_quillins.py``) and system-wide expansion
(``core/expansion/contributed.py``), which is the second reason it is worth its
own module.

Re-exported from ``quill.core.abbreviations`` so every existing import keeps
working.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from quill.core.abbreviations import Abbreviation, AbbreviationLibrary


def contributed_abbreviation_id(quillin_id: str, trigger: str) -> str:
    """Return a stable, namespaced id for a Quillin-contributed abbreviation."""
    return f"quillin:{quillin_id}:{trigger}"


def build_contributed_library(
    contributions: Iterable[tuple[str, Iterable[object]]],
    *,
    is_enabled: Callable[[str, str, bool], bool] | None = None,
) -> AbbreviationLibrary:
    """Build an in-memory library from Quillin-contributed abbreviation dicts.

    *contributions* pairs a ``quillin_id`` with that manifest's raw
    ``contributes.abbreviations`` entries. Only *static* abbreviations (those
    with an ``expansion``) are included; handler-based entries are skipped
    because the bare-word expander cannot run a handler mid-type (use a smart
    trigger or menu command for those). ``is_enabled(quillin_id, trigger,
    enabled_by_default)`` decides inclusion; when omitted the entry's
    ``enabled_by_default`` (default True) is used. Ids are deterministic so this
    library can be rebuilt on every Quillin reload without churn, and is kept
    separate from the user's saved library (it is never persisted).
    """
    abbreviations: list[Abbreviation] = []
    for quillin_id, entries in contributions:
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            trigger = str(raw.get("trigger", "")).strip()
            expansion = raw.get("expansion")
            if not trigger or not isinstance(expansion, str):
                continue
            default_enabled = bool(raw.get("enabled_by_default", True))
            if is_enabled is not None:
                if not is_enabled(quillin_id, trigger, default_enabled):
                    continue
            elif not default_enabled:
                continue
            abbreviations.append(
                Abbreviation(
                    id=contributed_abbreviation_id(quillin_id, trigger),
                    abbreviation=trigger,
                    expansion=expansion,
                    description=str(raw.get("description", "")),
                    case_sensitive=bool(raw.get("case_sensitive", False)),
                )
            )
    return AbbreviationLibrary(version=1, abbreviations=abbreviations)
