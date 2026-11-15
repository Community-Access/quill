"""The REST Console's knowledge of a site's routes (PRD 15.9; W7).

Everything here is read from the site's own index (``GET /wp-json/``), whose
``routes`` map each route pattern to its endpoints, and each endpoint to its
methods and arguments; nothing is guessed from a list kept in QUILL.

- :func:`route_template` turns a pattern (``/wp/v2/posts/(?P<id>[\\d]+)``)
  into what a person types (``wp/v2/posts/{id}``), and :func:`fill_route`
  fills the braces from the parameters given, so ``id=12`` reaches
  ``wp/v2/posts/12`` and is not sent twice.
- :func:`find_entry` finds the index entry a typed route belongs to, by the
  site's own patterns.
- :func:`argument_lines` and :func:`argument_problems` are the "what it
  accepts" for the chosen method, and the check a write's preview shows:
  a missing required argument, a name the route does not take, a value outside
  its list.
- :func:`schema_lines` reads what the route returns, from the ``schema`` an
  ``OPTIONS`` request answers with.

Wx-free and network-free.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = [
    "argument_lines",
    "argument_problems",
    "arguments",
    "fill_route",
    "find_entry",
    "methods_for",
    "route_template",
    "schema_lines",
    "templates",
]

_NAMED = re.compile(r"\(\?P<(\w+)>(?:[^()]|\([^()]*\))*\)")


def route_template(pattern: str) -> str:
    """``/wp/v2/posts/(?P<id>[\\d]+)`` -> ``wp/v2/posts/{id}``."""
    text = _NAMED.sub(lambda m: "{" + m.group(1) + "}", pattern)
    text = text.replace("(?:", "").replace(")?", "").replace("\\", "")
    return text.strip("/").rstrip("$").lstrip("^")


def templates(routes: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for pattern in routes:
        template = route_template(pattern)
        if template and template not in seen:
            seen.append(template)
    return seen


def fill_route(route: str, params: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    """*route* with each ``{name}`` filled from *params*, and the params left over."""
    left = dict(params)
    missing: list[str] = []

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in left:
            return str(left.pop(name))
        missing.append(name)
        return match.group(0)

    filled = re.sub(r"\{(\w+)\}", fill, route)
    if missing:
        raise ValueError(f"The route needs {', '.join(missing)}: give it as name=value.")
    return filled, left


def find_entry(routes: Mapping[str, Any], route: str) -> Mapping[str, Any]:
    """The index entry for *route* (``wp/v2/posts/12``), or an empty mapping."""
    clean = "/" + route.strip("/")
    entry = routes.get(clean)
    if isinstance(entry, Mapping):
        return entry
    for pattern, value in routes.items():
        try:
            if re.fullmatch(pattern.rstrip("$"), clean) and isinstance(value, Mapping):
                return value
        except re.error:
            continue
    return {}


def methods_for(entry: Mapping[str, Any]) -> list[str]:
    found: list[str] = []
    for endpoint in entry.get("endpoints", []) or []:
        for method in endpoint.get("methods", []) if isinstance(endpoint, dict) else []:
            if method not in found:
                found.append(str(method))
    return found or [str(m) for m in entry.get("methods", []) or []]


def arguments(entry: Mapping[str, Any], method: str) -> dict[str, Mapping[str, Any]]:
    """The arguments the route takes for *method*, by name."""
    found: dict[str, Mapping[str, Any]] = {}
    for endpoint in entry.get("endpoints", []) or []:
        if not isinstance(endpoint, dict) or method.upper() not in endpoint.get("methods", []):
            continue
        for name, spec in (endpoint.get("args") or {}).items():
            found[str(name)] = spec if isinstance(spec, dict) else {}
    return found


def _kind(spec: Mapping[str, Any]) -> str:
    kind = spec.get("type", "")
    return " or ".join(map(str, kind)) if isinstance(kind, list) else str(kind or "any")


def argument_lines(args: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """One line per argument: its name, type, whether required, and what it is."""
    lines: list[str] = []
    for name in sorted(args, key=lambda n: (not args[n].get("required"), n)):
        spec = args[name]
        said = f"{name} ({_kind(spec)}{', required' if spec.get('required') else ''})"
        if spec.get("description"):
            said += f": {spec['description']}"
        if isinstance(spec.get("enum"), list):
            said += f" One of: {', '.join(map(str, spec['enum']))}."
        if "default" in spec and spec["default"] not in (None, "", [], {}):
            said += f" Default: {spec['default']}."
        lines.append(said)
    return lines


def argument_problems(
    args: Mapping[str, Mapping[str, Any]], given: Mapping[str, Any], *, filled: Iterable[str] = ()
) -> list[str]:
    """What is wrong with *given*, judged by the route's own arguments."""
    if not args:
        return []
    problems: list[str] = []
    in_route = set(filled)
    for name, spec in args.items():
        if spec.get("required") and name not in given and name not in in_route:
            problems.append(f"{name} is required.")
    for name, value in given.items():
        found = args.get(name)
        if found is None:
            problems.append(f"{name} is not something this route takes.")
            continue
        enum = found.get("enum")
        if isinstance(enum, list) and enum and str(value) not in map(str, enum):
            problems.append(f"{name} must be one of {', '.join(map(str, enum))}.")
        if found.get("type") == "integer" and not re.fullmatch(r"-?\d+", str(value)):
            problems.append(f"{name} must be a whole number.")
    return problems


def schema_lines(schema: Mapping[str, Any]) -> list[str]:
    """What the route answers with, one line per field, from its schema."""
    title = str(schema.get("title", "") or "")
    lines = [f"Answers with: {title}"] if title else []
    properties = schema.get("properties") or {}
    for name in sorted(properties):
        spec = properties[name] if isinstance(properties[name], dict) else {}
        said = f"{name} ({_kind(spec)}{', read only' if spec.get('readonly') else ''})"
        if spec.get("description"):
            said += f": {spec['description']}"
        lines.append(said)
    return lines
