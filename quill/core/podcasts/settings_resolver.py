"""Four levels, one resolver: where a QUILL Cast setting's value comes from.

Cast had three of the four levels and they did not compose. The shared default
was real; a podcast's override was real; a *folder's* was not -- Folder Settings
wrote the chosen values into each member show's own override and then forgot
them, which made a folder a bulk-edit tool rather than a level. The cost was
paid twice: a show moved into a folder afterwards inherited nothing, and a show
that had ever been touched by the folder dialog stopped following the shared
default forever, because the override it was given was a **complete copy** of
the settings record rather than the one field somebody meant.

That is the bug this module exists to remove, and it is worth naming precisely:
Cast could not tell **"I have no opinion"** from **"I want exactly this"**. Once
those two are the same thing, changing a shared default silently stops reaching
the podcasts that most need it.

## The model

::

    shared default  ->  folder (outermost first)  ->  podcast

Nearest wins. Every level stores **only the settings it has an opinion about**
-- a sparse map of setting id to value, never a copy of the record -- so a level
with nothing to say is invisible and the level above it reaches through.

A folder inherits from *its* parent folder, so "all my news shows check hourly"
is set once on News and reaches News/Politics without being copied into it.

## What this buys, concretely

* **Changing a shared default reaches everything with no opinion**, at any
  depth. That is the entire point of having a shared default.
* **A folder is a real level.** Move a podcast into News and it starts checking
  hourly; move it out and it stops. Nothing was copied, so nothing drifts.
* **Every editor can say where a value came from** --
  :func:`describe_provenance` turns that into a sentence, and "every 60
  minutes, from the folder News" is an answer where "60" is a reading of a box.
* **Reset means something at each level.** Clearing a podcast's override drops
  it back to its folder, not to the class default.

## The migration, stated plainly

A library written before this carries whole-record overrides on
``PodcastShow.settings``. :func:`migrate_legacy_overrides` converts each into a
sparse map by **diffing it against the shared default**, keeping only the fields
that differ. That is a best-effort recovery: a podcast whose frozen copy
happened to match the shared default is read as having no opinion, which is
almost always what was meant and is in every case the safer of the two
readings -- the worst outcome is that a value starts following a default the
listener can change back in one place.

wx-free, strict-typed.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from quill.core.podcasts.models import PodcastSettings, PodcastShow
from quill.core.podcasts.settings_types import (
    LEVEL_FOLDER,
    LEVEL_GLOBAL,
    LEVEL_SHOW,
    SettingDef,
)
from quill.core.podcasts.subscriptions import PodcastLibrary

#: Scope keys in ``PodcastLibrary.scope_overrides``.
FOLDER_PREFIX = "folder:"
SHOW_PREFIX = "show:"


def scope_key(level: str, scope_id: str) -> str:
    """The storage key for one level's override map."""
    if level == LEVEL_FOLDER:
        return f"{FOLDER_PREFIX}{scope_id}"
    if level == LEVEL_SHOW:
        return f"{SHOW_PREFIX}{scope_id}"
    return LEVEL_GLOBAL


# -- the folder chain --------------------------------------------------------


def folder_chain(library: PodcastLibrary, folder_id: str | None) -> list[str]:
    """Folder ids from *folder_id* outwards to the root, nearest first.

    Guarded against a cycle: a hand-edited or half-synced library can name a
    folder its own ancestor, and a resolver that looped on it would hang the
    app rather than misreport one setting.
    """
    chain: list[str] = []
    seen: set[str] = set()
    current = folder_id
    while current and current not in seen:
        seen.add(current)
        chain.append(current)
        folder = library.find_folder(current)
        current = folder.parent_folder_id if folder is not None else None
    return chain


def _show_chain(library: PodcastLibrary, show: PodcastShow) -> list[str]:
    """Every scope key that may answer for *show*, nearest first."""
    keys = [f"{SHOW_PREFIX}{show.id}"]
    keys.extend(
        f"{FOLDER_PREFIX}{folder_id}" for folder_id in folder_chain(library, show.folder_id)
    )
    return keys


# -- resolution --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Resolved:
    """A value, and the level that answered for it."""

    value: object
    level: str
    #: The folder or show id that answered, or ``""`` for the shared default.
    scope_id: str = ""
    #: The folder's name, when a folder answered -- so the sentence can name it.
    scope_name: str = ""

    @property
    def is_default(self) -> bool:
        return self.level == LEVEL_GLOBAL


def _global_value(library: PodcastLibrary, definition: SettingDef) -> object:
    """The shared default's value: the dataclass field, or the by-id store."""
    if definition.settings_field:
        return getattr(library.settings, definition.settings_field, definition.default)
    if definition.id in library.extra_settings:
        return definition.coerce(library.extra_settings[definition.id])
    return definition.default


def resolve(
    library: PodcastLibrary,
    definition: SettingDef,
    *,
    show: PodcastShow | None = None,
    folder_id: str | None = None,
) -> Resolved:
    """This setting's value for a podcast (or a folder), and who decided it.

    Asked for a *folder* rather than a show when the folder's own editor wants
    to display what the folder would inherit; asked for a show everywhere else.
    A setting the definition does not allow at a level is never read there, so
    a global-only setting cannot be quietly overridden by a stray stored key.
    """
    if show is not None:
        keys = _show_chain(library, show)
    elif folder_id:
        keys = [f"{FOLDER_PREFIX}{fid}" for fid in folder_chain(library, folder_id)]
    else:
        keys = []

    for key in keys:
        level = LEVEL_SHOW if key.startswith(SHOW_PREFIX) else LEVEL_FOLDER
        if not definition.allows(level):
            continue
        stored = library.scope_overrides.get(key)
        if stored is not None and definition.id in stored:
            scope_id = key.split(":", 1)[1]
            folder = library.find_folder(scope_id) if level == LEVEL_FOLDER else None
            return Resolved(
                value=definition.coerce(stored[definition.id]),
                level=level,
                scope_id=scope_id,
                scope_name=folder.name if folder is not None else "",
            )

    # The legacy whole-record override, for a show built in memory rather than
    # loaded (load_library migrates the stored ones away). Sits below the
    # sparse map and above the folders, which is where a show-level opinion
    # belongs.
    if (
        show is not None
        and show.settings is not None
        and definition.settings_field
        and definition.allows(LEVEL_SHOW)
    ):
        return Resolved(
            value=getattr(show.settings, definition.settings_field, definition.default),
            level=LEVEL_SHOW,
            scope_id=show.id,
        )

    return Resolved(value=_global_value(library, definition), level=LEVEL_GLOBAL)


def value_of(
    library: PodcastLibrary,
    definition: SettingDef,
    *,
    show: PodcastShow | None = None,
    folder_id: str | None = None,
) -> object:
    """Just the value -- the common case, without the provenance."""
    return resolve(library, definition, show=show, folder_id=folder_id).value


def values_for(
    library: PodcastLibrary,
    definitions: tuple[SettingDef, ...],
    *,
    show: PodcastShow | None = None,
) -> dict[str, object]:
    """A family of settings resolved at once, keyed by id.

    What the row-speech composer and the arrival policy actually want: one
    walk of the chain per call site rather than one per setting.
    """
    return {item.id: value_of(library, item, show=show) for item in definitions}


def describe_provenance(definition: SettingDef, resolved: Resolved) -> str:
    """Where this value came from, as a sentence an editor can speak.

    The half of the inheritance model a listener can actually perceive. An
    editor that shows ``60`` has told somebody the number; one that says
    "Every 60 minutes, from the folder News" has told them why, and where to
    go to change it for everything else in that folder too.
    """
    said = definition.say(resolved.value)
    if resolved.level == LEVEL_GLOBAL:
        return f"{said}, from the shared default."
    if resolved.level == LEVEL_FOLDER:
        where = f"the folder {resolved.scope_name}" if resolved.scope_name else "a folder"
        return f"{said}, from {where}."
    return f"{said}, set for this podcast."


# -- writing -----------------------------------------------------------------


def set_value(
    library: PodcastLibrary,
    definition: SettingDef,
    value: object,
    *,
    level: str,
    scope_id: str = "",
) -> bool:
    """Set one setting at one level; True when anything changed.

    Writing at the shared default goes to the dataclass field when the setting
    has one and to the by-id store otherwise -- the difference is invisible to
    every caller, which is what lets a new setting arrive without growing a
    500-line record.
    """
    if not definition.allows(level):
        return False
    coerced = definition.coerce(value)
    if level == LEVEL_GLOBAL:
        if definition.settings_field:
            if getattr(library.settings, definition.settings_field, None) == coerced:
                return False
            setattr(library.settings, definition.settings_field, coerced)
            return True
        if library.extra_settings.get(definition.id) == coerced:
            return False
        library.extra_settings[definition.id] = coerced
        return True

    if level == LEVEL_SHOW:
        show = library.find_show(scope_id)
        if show is not None:
            # Fold any legacy whole-record override into the sparse map first,
            # so the two storage shapes can never disagree about one podcast.
            migrate_show(library, show)
    key = scope_key(level, scope_id)
    bucket = library.scope_overrides.setdefault(key, {})
    if bucket.get(definition.id) == coerced:
        return False
    bucket[definition.id] = coerced
    return True


def clear_value(
    library: PodcastLibrary, definition: SettingDef, *, level: str, scope_id: str = ""
) -> bool:
    """Remove one level's opinion; True when there was one.

    Never writes a value in its place. Clearing is how a podcast goes back to
    following its folder, and a folder back to following the shared default --
    which is only possible because an absent key and a stored key are
    different things here.
    """
    if level == LEVEL_GLOBAL:
        return library.extra_settings.pop(definition.id, None) is not None
    bucket = library.scope_overrides.get(scope_key(level, scope_id))
    if bucket is None or definition.id not in bucket:
        return False
    del bucket[definition.id]
    if not bucket:
        library.scope_overrides.pop(scope_key(level, scope_id), None)
    return True


def clear_scope(library: PodcastLibrary, *, level: str, scope_id: str) -> int:
    """Drop every override at one level; returns how many were dropped.

    *Follow the shared defaults* for a podcast, and its folder equivalent.
    """
    key = scope_key(level, scope_id)
    bucket = library.scope_overrides.pop(key, None)
    if level == LEVEL_SHOW:
        show = library.find_show(scope_id)
        if show is not None and show.settings is not None:
            show.settings = None
    return len(bucket or {})


def overrides_at(library: PodcastLibrary, *, level: str, scope_id: str = "") -> dict[str, object]:
    """One level's stored opinions, as a plain dict."""
    if level == LEVEL_GLOBAL:
        return dict(library.extra_settings)
    return dict(library.scope_overrides.get(scope_key(level, scope_id), {}))


def has_override(
    library: PodcastLibrary, definition: SettingDef, *, level: str, scope_id: str = ""
) -> bool:
    """Whether *level* has an opinion about this setting."""
    if level == LEVEL_GLOBAL:
        return definition.id in library.extra_settings
    return definition.id in library.scope_overrides.get(scope_key(level, scope_id), {})


# -- migration ---------------------------------------------------------------


def migrate_show(library: PodcastLibrary, show: PodcastShow) -> int:
    """Turn one podcast's whole-record override into a sparse one.

    Diffs the stored record against the shared default and keeps only the
    fields that differ; a field that matches is read as "no opinion", which is
    the safer of the two readings and almost always what was meant. Returns
    how many opinions survived the diff. Idempotent.
    """
    record = show.settings
    if record is None:
        return 0
    key = f"{SHOW_PREFIX}{show.id}"
    bucket = library.scope_overrides.setdefault(key, {})
    kept = 0
    for field in dataclasses.fields(PodcastSettings):
        stored = getattr(record, field.name)
        if stored == getattr(library.settings, field.name):
            continue
        # An opinion already written by the newer path wins: it is the more
        # recent statement, and re-importing the frozen copy over it would
        # undo a setting somebody just changed.
        bucket.setdefault(field.name, stored)
        kept += 1
    if not bucket:
        library.scope_overrides.pop(key, None)
    show.settings = None
    return kept


def migrate_legacy_overrides(library: PodcastLibrary) -> int:
    """Migrate every podcast's whole-record override; returns how many moved.

    Run once at load. Cheap on a library that has already been migrated: every
    show's ``settings`` is ``None`` and the loop does nothing.
    """
    moved = 0
    for show in library.shows:
        if show.settings is not None:
            migrate_show(library, show)
            moved += 1
    return moved


# -- the settings record, resolved -------------------------------------------


def effective_settings(library: PodcastLibrary, show: PodcastShow) -> PodcastSettings:
    """The whole :class:`PodcastSettings` record in force for *show*.

    The compatibility bridge: every existing caller of
    ``PodcastLibrary.effective_settings`` keeps working and silently gains the
    folder level.

    **The fast path is the common one.** A podcast with no override of its own,
    in no folder that has one, gets the shared record back by identity -- no
    copy, no dataclass construction, nothing allocated. That matters because
    this is called per show per refresh, and on some paths per episode.
    """
    keys = _show_chain(library, show)
    if show.settings is None and not any(library.scope_overrides.get(key) for key in keys):
        return library.settings

    merged: dict[str, object] = {}
    # Outermost folder first, so a nearer level overwrites a further one, and
    # the show's own opinion is written last.
    for key in reversed(keys):
        merged.update(library.scope_overrides.get(key, {}))
    if show.settings is not None:
        for field in dataclasses.fields(PodcastSettings):
            stored = getattr(show.settings, field.name)
            if stored != getattr(library.settings, field.name):
                merged[field.name] = stored
    known = {field.name for field in dataclasses.fields(PodcastSettings)}
    updates = {name: value for name, value in merged.items() if name in known}
    if not updates:
        return library.settings
    return dataclasses.replace(library.settings, **updates)  # type: ignore[arg-type]


__all__ = [
    "FOLDER_PREFIX",
    "SHOW_PREFIX",
    "Resolved",
    "clear_scope",
    "clear_value",
    "describe_provenance",
    "effective_settings",
    "folder_chain",
    "has_override",
    "migrate_legacy_overrides",
    "migrate_show",
    "overrides_at",
    "resolve",
    "scope_key",
    "set_value",
    "value_of",
    "values_for",
]
