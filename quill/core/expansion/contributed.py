"""Quillin-contributed abbreviations, available system-wide.

A Quillin can contribute abbreviations, and until now they worked in one place:
inside QUILL's editor. Quill Inkwell -- the same abbreviations, expanded into any
application -- did not see them, so a Quillin that added a set of medical
abbreviations or a company's boilerplate stopped at the edge of the editor. That
is the wrong boundary: the whole point of Inkwell is that an abbreviation is an
abbreviation wherever you are typing.

This joins them. It discovers installed Quillins the same way the editor does,
builds the same in-memory library from their static contributions, and merges it
with the user's own for matching.

Three rules the merge keeps:

* **The user's own entry always wins.** If somebody has defined ``addr``
  themselves and a Quillin also contributes ``addr``, theirs is what fires.
  Anything else means an installed extension silently changing what a key
  sequence does.
* **Contributed entries are never persisted.** They are rebuilt on every load
  from the manifests, exactly as in the editor, so uninstalling a Quillin takes
  its abbreviations with it and nothing is left behind in
  ``abbreviations.json``.
* **Only static expansions.** A contributed entry with a handler rather than an
  expansion is skipped, because a bare-word expander cannot run a handler
  mid-type -- the same rule the editor applies, for the same reason.

Refused in Safe Mode, where no Quillin is loaded at all.

wx-free, strict-typed.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.abbreviations import (
    AbbreviationLibrary,
    build_contributed_library,
)

#: The app id Quillins target when they contribute to system-wide expansion.
#: The editor's own id: an abbreviation pack is written once and works in both,
#: which is the point. A separate "inkwell" id would mean every existing pack
#: had to be re-published to be usable outside the editor.
EXPANSION_APP_ID = "editor"


def contributed_library(
    features: object,
    *,
    root: Path | None = None,
    safe_mode: bool = False,
) -> AbbreviationLibrary:
    """Every static abbreviation the installed Quillins contribute.

    Never raises: a Quillin tree that cannot be read is no abbreviations, not a
    keyboard hook that fails to install.
    """
    if safe_mode:
        return AbbreviationLibrary(version=1, abbreviations=[])
    try:
        from quill.core.quillins.loader import (
            load_enabled_bundled_manifests,
            load_enabled_manifests,
        )

        manifests = [
            *load_enabled_bundled_manifests(features, root=root, app_id=EXPANSION_APP_ID),
            *load_enabled_manifests(features, root=root, app_id=EXPANSION_APP_ID),
        ]
        return build_contributed_library(
            (manifest.id, manifest.contributes.abbreviations) for manifest in manifests
        )
    except Exception:  # noqa: BLE001 - no Quillins is a valid state, not a failure
        return AbbreviationLibrary(version=1, abbreviations=[])


def merge_libraries(
    user: AbbreviationLibrary, contributed: AbbreviationLibrary
) -> AbbreviationLibrary:
    """The user's library plus anything contributed it does not already define.

    Matching is on the trigger, case-insensitively, because that is what the
    expander matches on: two entries that differ only in case would both fire on
    the same typing, and which one won would be an implementation detail.

    Returns a new library; neither input is modified, and the result is never
    saved -- persisting it would bake an extension's entries into the user's own
    file, where uninstalling the Quillin could not remove them.
    """
    if not contributed.abbreviations:
        return user
    taken = {entry.abbreviation.strip().lower() for entry in user.abbreviations}
    extra = [
        entry
        for entry in contributed.abbreviations
        if entry.abbreviation.strip().lower() not in taken
    ]
    if not extra:
        return user
    return AbbreviationLibrary(
        version=user.version,
        abbreviations=[*user.abbreviations, *extra],
    )


def describe(contributed: AbbreviationLibrary) -> str:
    """The status line: how many abbreviations came from Quillins."""
    count = len(contributed.abbreviations)
    if not count:
        return ""
    return f"{count} abbreviation{'' if count == 1 else 's'} from your Quillins."
