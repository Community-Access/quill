"""Reading and writing a stored form model, and upgrading old ones.

The model is BAF's JSON (``schema/form.schema.json``); QUILL keeps it as plain
dicts and lists, so this module only reads, writes, and upgrades.

**Versions and migrations** (BAF's ``docs/form-model.md``, "Versions"):
every form carries ``version``. A reader that meets a newer version refuses
it and says which it needs. A change that only adds optional properties keeps
the version; anything that changes the meaning of an existing form makes a new
version, with a written migration registered here for the old number::

    @migration(1)
    def _one_to_two(data: dict) -> dict:
        return {**data, "version": 2}

``upgrade`` runs the chain one step at a time, so a form written for any
earlier version always opens and is never changed in place.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any

from quill.core.forms.errors import FormModelError, FormVersionError
from quill.core.forms.model import MODEL_VERSION, Model, encode

Migration = Callable[[dict[str, Any]], dict[str, Any]]
MIGRATIONS: dict[int, Migration] = {}


def migration(from_version: int) -> Callable[[Migration], Migration]:
    """Register the migration from ``from_version`` to the next version."""

    def register(func: Migration) -> Migration:
        MIGRATIONS[from_version] = func
        return func

    return register


def upgrade(data: dict[str, Any], target: int = MODEL_VERSION) -> dict[str, Any]:
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise FormVersionError(f"The form's version, {version!r}, is not a version number.")
    if version > target:
        raise FormVersionError(
            f"This form was written for form model version {version}; this copy of "
            f"QUILL reads up to version {target}. Update QUILL to open it."
        )
    data = copy.deepcopy(data)
    while version < target:
        step = MIGRATIONS.get(version)
        if step is None:
            raise FormVersionError(f"There is no way to upgrade a version {version} form yet.")
        data = step(data)
        if data.get("version") != version + 1:
            raise FormVersionError(
                f"The upgrade from version {version} did not reach {version + 1}."
            )
        version += 1
    return data


def from_dict(data: Any) -> Model:
    """A stored form, upgraded to this version. Use ``model.validate`` to check it."""
    if not isinstance(data, dict):
        raise FormModelError("A form must be a JSON object.")
    return upgrade(data)


def loads(text: str) -> Model:
    try:
        data = json.loads(text.lstrip("﻿"))
    except json.JSONDecodeError as exc:
        raise FormModelError(f"The form is not valid JSON: {exc.msg}, line {exc.lineno}.") from exc
    return from_dict(data)


def dumps(model: Model) -> str:
    """The model as BAF writes it: pretty JSON, UTF-8, ending in a newline."""
    return encode(model, pretty=True) + "\n"


to_dict = copy.deepcopy
