"""Versioned, nested serialization and migration for :class:`Settings` (SET-5).

This is the settings half of QUILL's release-to-release persistence contract
(the keymap and feature-flag stores follow the same rule):

    **Defaults live in code; disk stores only the user's deltas from those
    defaults, stamped with a schema version.**

Why a *delta*, not a full snapshot? Because it is what makes upgrades "just
work":

* A **new** setting added in a release is absent from an old file, so the user
  picks up its default automatically.
* A **changed default** reaches every user who never overrode that field --
  their delta has no entry for it, so it resolves to the new default. (A full
  snapshot, by contrast, pins every field to its value at save time, so a
  changed default would never reach an existing user. That was the latent bug
  this rewrite removes; see ``schema_version`` 2 below.)
* A **user customization** is the only thing actually written, so it is
  preserved verbatim across upgrades.

Document shape (``schema_version`` 2)::

    {"schema_version": 2, "groups": {"general": {<overrides>}, "_ungrouped": {...}}}

Only fields whose value differs from ``Settings()`` (the canonical default
instance, the single source of truth) are written, grouped by their registry
group for readability. A pristine ``Settings()`` therefore serializes to
``{"schema_version": 2, "groups": {}}``.

Other design guarantees:

* **Round-trip fidelity** - ``from_versioned(to_versioned(s)) == s`` still
  holds: the dropped fields equal their defaults, and :meth:`Settings.from_dict`
  refills any missing field with that same default.
* **Corrupt-file recovery that preserves other settings** - a bad value in one
  group falls back to that field's default without discarding the rest, because
  the flattened payload is validated field-by-field through
  :meth:`Settings.from_dict`.
* **Backward compatibility** - any older shape is read transparently: a
  ``schema_version`` 1 *full snapshot*, a stamp-less legacy *flat* document, or
  junk. :func:`is_legacy_settings_document` reports whether the on-disk shape
  predates the current schema so the loader can back it up before rewriting it
  to the canonical delta (see ``quill.core.settings.load_settings``).

No ``wx`` imports: this is pure model code. It is imported lazily by
:mod:`quill.core.settings` to avoid an import cycle with the registry.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from quill.core.settings import Settings
from quill.core.settings_registry import find_spec

#: Bump when the on-disk document shape changes in a way that should trigger the
#: one-time legacy clean-up + backup on load. History:
#:   1 - nested ``{"schema_version", "groups"}`` *full snapshot* of every field.
#:   2 - nested ``groups`` hold only the *delta* from ``Settings()`` defaults,
#:       so changed/added defaults reach existing users automatically.
SETTINGS_SCHEMA_VERSION = 2

#: Bucket for fields that have no registry spec (still serialized when they
#: differ from the default, never lost).
UNGROUPED_KEY = "_ungrouped"


def _group_for_key(key: str) -> str:
    spec = find_spec(key)
    if spec is not None and spec.group:
        return spec.group
    return UNGROUPED_KEY


def to_versioned(settings: Settings) -> dict[str, Any]:
    """Return the nested, versioned *delta* document for ``settings``.

    Shape::

        {"schema_version": 2, "groups": {"general": {<overrides>}, ...}}

    Only fields whose value differs from ``Settings()`` -- the canonical default
    instance and the single source of truth for "what is the default" -- are
    written, each under its registry group (fields without a spec go to the
    ``_ungrouped`` bucket). Omitting defaults is deliberate: it is what lets a
    later change to a default reach existing users (see the module docstring).
    """
    defaults = asdict(Settings())
    groups: dict[str, dict[str, Any]] = {}
    for key, value in asdict(settings).items():
        if value == defaults.get(key):
            # Equal to the default -> omit, so the field tracks the current
            # default on every load rather than being pinned to this value.
            continue
        groups.setdefault(_group_for_key(key), {})[key] = value
    return {"schema_version": SETTINGS_SCHEMA_VERSION, "groups": groups}


def is_legacy_settings_document(raw: object) -> bool:
    """Return True when ``raw`` predates the current ``SETTINGS_SCHEMA_VERSION``.

    Covers an unstamped legacy flat document and any stamped document whose
    version is below the current one (e.g. the v1 full snapshot). The loader
    uses this to decide whether to back the file up before rewriting it to the
    canonical delta shape, so a one-time migration is always recoverable.
    """
    if not isinstance(raw, dict):
        return False
    version = raw.get("schema_version")
    if not isinstance(version, int):
        return True
    return version < SETTINGS_SCHEMA_VERSION


def _flatten_groups(groups: object) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if not isinstance(groups, dict):
        return flat
    for bucket in groups.values():
        if isinstance(bucket, dict):
            for key, value in bucket.items():
                flat[str(key)] = value
    return flat


def migrate(raw: object) -> dict[str, Any]:
    """Return a flat settings mapping from any supported on-disk shape.

    Accepts the nested ``{"schema_version", "groups"}`` document, a legacy flat
    mapping, or junk (returns an empty mapping). The result is suitable for
    :meth:`Settings.from_dict`, which validates and defaults field-by-field.
    """
    if not isinstance(raw, dict):
        return {}
    if "groups" in raw:
        return _flatten_groups(raw.get("groups"))
    # Legacy flat document: every key is already a candidate field.
    return {str(key): value for key, value in raw.items() if key != "schema_version"}


def _accepts(key: str, value: Any) -> bool:
    try:
        Settings.from_dict({key: value})
    except (TypeError, ValueError):
        return False
    return True


def _safe_from_dict(flat: dict[str, Any]) -> Settings:
    try:
        return Settings.from_dict(flat)
    except (TypeError, ValueError):
        # A corrupt value raised on the whole load; keep every field that
        # validates on its own and drop only the offending ones.
        good: dict[str, Any] = {}
        for key, value in flat.items():
            try:
                Settings.from_dict({key: value})
                good[key] = value
            except (TypeError, ValueError):
                continue
        return Settings.from_dict(good)


def from_versioned(raw: object) -> Settings:
    """Build a validated :class:`Settings` from any supported document shape.

    A corrupt individual value is dropped (falling back to that field's
    default) without discarding the surrounding settings; an unreadable
    document yields an all-defaults :class:`Settings`.
    """
    return _safe_from_dict(migrate(raw))
