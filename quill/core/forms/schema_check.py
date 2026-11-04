"""Checking a stored form against ``schema/form.schema.json``.

QUILL ships no ``jsonschema`` dependency (see ``quill/core/quillins/
validation.py``), so this module interprets the schema file itself, using the
part of JSON Schema 2020-12 the form schema uses: ``type``, ``const``,
``enum``, ``properties``, ``required``, ``additionalProperties``,
``propertyNames``, ``items``, ``minItems``, ``minimum``, ``pattern``,
``oneOf`` and local ``$ref``. The schema is therefore the one definition, read
by QUILL here and by BAF's PHP, rather than a copy kept in step by hand.

One keyword is QUILL's and BAF's own: ``"x-expression": true`` marks a string
that must parse in the form expression language. Other validators ignore it.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.errors import ExpressionError, FormModelError

SCHEMA_PATH = Path(__file__).parent / "schema" / "form.schema.json"

_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
    "null": (type(None),),
}


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return data


def _is_type(value: Any, name: str) -> bool:
    if name in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[name])


class _Checker:
    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root
        self.problems: list[str] = []

    def resolve(self, ref: str) -> dict[str, Any]:
        if not ref.startswith("#/"):
            raise FormModelError(f"The schema refers outside itself ({ref}).")
        node: Any = self.root
        for part in ref[2:].split("/"):
            node = node[part]
        return dict(node)

    def check(self, value: Any, schema: dict[str, Any], where: str) -> bool:  # noqa: C901
        before = len(self.problems)
        if "$ref" in schema:
            merged = self.resolve(schema["$ref"])
            merged.update({k: v for k, v in schema.items() if k != "$ref"})
            schema = merged
        if "oneOf" in schema:
            matches = 0
            for option in schema["oneOf"]:
                trial = _Checker(self.root)
                if trial.check(value, option, where):
                    matches += 1
            if matches != 1:
                kind = value.get("kind") if isinstance(value, dict) else None
                self.problems.append(
                    f"{where}: is not exactly one kind of item (kind is {kind!r})."
                )
                if isinstance(value, dict) and kind in ("field", "section", "columns", "island"):
                    self.check(value, {"$ref": f"#/$defs/{kind}"}, where)
        types = schema.get("type")
        if types is not None:
            names = [types] if isinstance(types, str) else list(types)
            if not any(_is_type(value, n) for n in names):
                self.problems.append(f"{where}: should be {' or '.join(names)}.")
                return False
        if "const" in schema and value != schema["const"]:
            self.problems.append(f"{where}: should be {schema['const']!r}.")
        if "enum" in schema and value not in schema["enum"]:
            self.problems.append(f"{where}: {value!r} is not one of the allowed values.")
        if isinstance(value, str):
            if "pattern" in schema and not re.search(schema["pattern"], value):
                self.problems.append(f"{where}: {value!r} is not in the expected form.")
            if schema.get("x-expression"):
                try:
                    E.parse(value)
                except ExpressionError as exc:
                    self.problems.append(f"{where}: the rule {value!r} does not read: {exc}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                self.problems.append(f"{where}: should be at least {schema['minimum']}.")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                self.problems.append(f"{where}: needs at least {schema['minItems']} item.")
            if "items" in schema:
                for n, item in enumerate(value):
                    self.check(item, schema["items"], f"{where}[{n}]")
        if isinstance(value, dict):
            props = schema.get("properties", {})
            for key in schema.get("required", []):
                if key not in value:
                    self.problems.append(f"{where}: is missing {key!r}.")
            key_schema = schema.get("propertyNames")
            extra = schema.get("additionalProperties", True)
            for key, item in value.items():
                if key_schema is not None:
                    self.check(key, key_schema, f"{where} key {key!r}")
                if key in props:
                    self.check(item, props[key], f"{where}.{key}")
                elif extra is False:
                    self.problems.append(f"{where}: has {key!r}, which the model does not have.")
                elif isinstance(extra, dict):
                    self.check(item, extra, f"{where}.{key}")
        return len(self.problems) == before


def problems(data: Any) -> list[str]:
    """Every way ``data`` does not fit the form schema; empty when it fits."""
    checker = _Checker(load_schema())
    checker.check(data, load_schema(), "form")
    return checker.problems


def check(data: Any) -> None:
    """Raise :class:`FormModelError` listing the problems, if there are any."""
    found = problems(data)
    if found:
        more = f" and {len(found) - 1} more" if len(found) > 1 else ""
        raise FormModelError(f"The form does not fit the form model: {found[0]}{more}", found)
