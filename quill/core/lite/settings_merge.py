"""Saving QUILL Lite's settings when another QUILL Lite may have saved first.

F-11 (qc.md): ``--new-instance`` runs two processes against one settings file,
and each used to write its whole in-memory copy -- so the last one to save undid
every preference the other had changed, silently. Atomic writes stop a
half-written file; they do not stop a valid older snapshot replacing a valid
newer one.

So a save is a three-way merge, field by field (:func:`merge_for_save`). Kept
beside :mod:`quill.core.lite.settings` rather than inside it because that module
is at the 600-line cap, and because merging is one subject: what to write, given
what was loaded, what is held, and what is on disk now.

wx-free, strict-typed, pure apart from the one read in :func:`load_if_present`.
"""

from __future__ import annotations

import copy
import json
from dataclasses import fields
from pathlib import Path

from quill.core.lite.paths import settings_path
from quill.core.lite.settings import Settings, load

__all__ = ["load_if_present", "merge_for_save"]


def load_if_present(path: Path | None = None) -> Settings | None:
    """The settings on disk, or ``None`` when there is no readable file.

    :func:`~quill.core.lite.settings.load` turns a missing or corrupt file into
    defaults, which is right for starting up and wrong for merging: a merge
    against defaults would undo every preference this process had loaded and
    not touched. ``None`` tells the caller there is nothing to merge with.
    """
    target = path if path is not None else settings_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return load(target)


def merge_for_save(baseline: Settings, ours: Settings, disk: Settings) -> Settings:
    """What to write: our changes over whatever is on disk now.

    *baseline* is what this process last loaded or wrote; *ours* is what it
    holds now; *disk* is the file at this moment. A field this process changed
    since its baseline is written with its value; every other field keeps
    whatever is on disk, which is the other instance's choice if it made one.
    The last writer wins per field rather than per file, and a field neither
    instance touched is never rewritten.

    The in-memory settings are not changed by this: adopting another window's
    theme or font mid-session would be exactly the silent change to a
    screen-reader user's setup that qc.md X-05 forbids. The other instance's
    choices take effect here at the next launch.
    """
    merged = copy.deepcopy(disk)
    for spec in fields(Settings):
        mine = getattr(ours, spec.name)
        if mine != getattr(baseline, spec.name):
            setattr(merged, spec.name, copy.deepcopy(mine))
    return merged.normalized()
