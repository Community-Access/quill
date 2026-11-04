"""Checking a model against the published schema: a port of ``BAF_JSON_Schema``.

The schema file, ``schema/form.schema.json``, is BAF's own, copied unchanged
(its ``$id`` is BAF's); the conformance test checks it is byte-identical to
BAF's when BAF is on the machine. QUILL ships no ``jsonschema`` dependency, so
this interprets the file itself, using the same keywords BAF's PHP does and
reporting the same JSON pointers. ``"format": "baf-expression"`` means "parses
as an expression".
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.errors import FormModelError

SCHEMA_PATH = Path(__file__).parent / "schema" / "form.schema.json"

Problem = dict[str, str]


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return data


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _has_type(v: Any, kind: str) -> bool:
    if kind == "object":
        return isinstance(v, dict)
    if kind == "array":
        return isinstance(v, list)
    if kind == "string":
        return isinstance(v, str)
    if kind == "integer":
        return (
            isinstance(v, int)
            and not isinstance(v, bool)
            or (isinstance(v, float) and v.is_integer())
        )
    if kind == "number":
        return _is_num(v)
    if kind == "boolean":
        return isinstance(v, bool)
    if kind == "null":
        return v is None
    return False


def _same(a: Any, b: Any) -> bool:
    """PHP's ``===`` on decoded JSON: no True == 1."""
    if type(a) is not type(b) and not (_is_num(a) and _is_num(b) and type(a) is type(b)):
        return False
    return bool(a == b)


def _show(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


class _Checker:
    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root
        self.errors: list[Problem] = []

    def resolve(self, ref: str) -> Any:
        node: Any = self.root
        for part in ref[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node

    def passes(self, v: Any, schema: Any, path: str) -> bool:
        saved = self.errors
        self.errors = []
        self.check(v, schema, path)
        ok = not self.errors
        self.errors = saved
        return ok

    def error(self, path: str, message: str) -> None:
        self.errors.append({"path": path or "/", "message": message})

    def check(self, v: Any, schema: Any, path: str) -> None:  # noqa: C901 - one case per keyword
        if schema is True:
            return
        if schema is False:
            self.error(path, "Nothing is allowed here.")
            return
        if "$ref" in schema:
            self.check(v, self.resolve(schema["$ref"]), path)
        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_has_type(v, t) for t in types):
                self.error(path, "Expected " + " or ".join(types) + ".")
                return
        if "const" in schema and not _same(v, schema["const"]):
            self.error(path, "Must be " + _show(schema["const"]) + ".")
        if "enum" in schema and not any(_same(v, e) for e in schema["enum"]):
            self.error(path, "Must be one of: " + ", ".join(_show(e) for e in schema["enum"]) + ".")
        if isinstance(v, str):
            if "minLength" in schema and len(v) < schema["minLength"]:
                self.error(path, f"Must be at least {schema['minLength']} character(s).")
            if "pattern" in schema and not re.search(schema["pattern"], v):
                self.error(path, f"Does not match the pattern {schema['pattern']}.")
            if schema.get("format") == "baf-expression":
                problem = E.check(v)
                if problem is not None:
                    self.error(path, "Not a valid expression: " + problem)
        if _is_num(v):
            if "minimum" in schema and v < schema["minimum"]:
                self.error(path, f"Must be at least {schema['minimum']}.")
            if "maximum" in schema and v > schema["maximum"]:
                self.error(path, f"Must be at most {schema['maximum']}.")
        if isinstance(v, list):
            if "minItems" in schema and len(v) < schema["minItems"]:
                self.error(path, f"Needs at least {schema['minItems']} item(s).")
            if "maxItems" in schema and len(v) > schema["maxItems"]:
                self.error(path, f"Allows at most {schema['maxItems']} item(s).")
            if schema.get("uniqueItems"):
                seen = [json.dumps(x, sort_keys=True) for x in v]
                if len(set(seen)) != len(seen):
                    self.error(path, "Items must not repeat.")
            if "items" in schema:
                for i, item in enumerate(v):
                    self.check(item, schema["items"], f"{path}/{i}")
        if isinstance(v, dict):
            for key in schema.get("required", []):
                if key not in v:
                    self.error(path, f'Missing "{key}".')
            props = schema.get("properties", {})
            for key, value in v.items():
                sub = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
                if "propertyNames" in schema and not self.passes(key, schema["propertyNames"], sub):
                    self.error(sub, f'The name "{key}" is not allowed here.')
                if key in props:
                    self.check(value, props[key], sub)
                elif "additionalProperties" in schema:
                    if schema["additionalProperties"] is False:
                        self.error(sub, f'Unknown property "{key}".')
                    else:
                        self.check(value, schema["additionalProperties"], sub)
        for sub_schema in schema.get("allOf", []):
            self.check(v, sub_schema, path)
        if "anyOf" in schema and not any(self.passes(v, s, path) for s in schema["anyOf"]):
            self.error(path, schema.get("x-message", "Does not match any allowed shape."))
        if "oneOf" in schema and sum(1 for s in schema["oneOf"] if self.passes(v, s, path)) != 1:
            self.error(path, schema.get("x-message", "Must match exactly one allowed shape."))
        if "not" in schema and self.passes(v, schema["not"], path):
            self.error(path, schema.get("x-message", "This shape is not allowed here."))
        if "if" in schema:
            if self.passes(v, schema["if"], path):
                if "then" in schema:
                    self.check(v, schema["then"], path)
            elif "else" in schema:
                self.check(v, schema["else"], path)


def schema_problems(data: Any) -> list[Problem]:
    """Every way ``data`` does not fit the schema, as ``{"path", "message"}``."""
    checker = _Checker(load_schema())
    checker.check(data, load_schema(), "")
    return checker.errors


def problems(data: Any) -> list[Problem]:
    """The schema's problems, then (if it fits) the rules beyond the schema."""
    found = schema_problems(data)
    if found:
        return found
    from quill.core.forms.model import semantic_errors

    return semantic_errors(data)


def check(data: Any) -> None:
    """Raise :class:`FormModelError` listing the problems, if there are any."""
    found = problems(data)
    if found:
        first = found[0]
        more = f" and {len(found) - 1} more" if len(found) > 1 else ""
        raise FormModelError(
            f"The form does not fit the form model: {first['path']}: {first['message']}{more}",
            [f"{p['path']}: {p['message']}" for p in found],
        )
