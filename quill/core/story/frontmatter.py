"""Front-matter codec for story element files (wx-free, dependency-free).

An element file may carry an optional leading block, fenced by ``---`` lines,
holding light structured fields (a character's goal, a plot thread's status,
tags). The body below is ordinary prose. The codec round-trips both:
``join_front_matter(*split_front_matter(text))`` reproduces the text.

This is a deliberately small subset of YAML — ``key: value`` scalars and simple
``- item`` lists — so Story Studio adds no third-party dependency for a format
it fully controls. The block stays human-readable and hand-editable; values are
read as plain strings (no type coercion), and a key whose value is an indented
or dashed list becomes a list of strings.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["split_front_matter", "join_front_matter"]

_FENCE = "---"


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(fields, body)`` for ``text``.

    When ``text`` opens with a ``---`` fenced block, its ``key: value`` / list
    entries are returned as ``fields`` and everything after the closing fence as
    ``body``. Otherwise ``fields`` is empty and ``body`` is ``text`` unchanged.
    A block with no closing fence is treated as "no front matter" so a stray
    ``---`` never swallows the prose.
    """
    first_line, newline, _rest = text.partition("\n")
    # Accept a CRLF first line too: Windows files often open with "---\r\n".
    if not newline or first_line.rstrip("\r") != _FENCE:
        return {}, text
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].strip() == _FENCE:
            fields = _parse_block(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return fields, body
    return {}, text


def join_front_matter(fields: Mapping[str, Any], body: str) -> str:
    """Serialize ``fields`` as a leading ``---`` block prepended to ``body``.

    Returns ``body`` unchanged when ``fields`` is empty. Insertion order is
    preserved (no sorting) so a file the user arranged stays arranged.
    """
    if not fields:
        return body
    out: list[str] = [_FENCE]
    for key, value in fields.items():
        if isinstance(value, (list, tuple)):
            out.append(f"{key}:")
            out.extend(f"- {_emit_scalar(str(item))}" for item in value)
        else:
            out.append(f"{key}: {_emit_scalar(str(value))}")
    out.append(_FENCE)
    return "\n".join(out) + "\n" + body


def _parse_block(block_lines: list[str]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw in block_lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped == "-" or stripped.startswith("- "):
            item = stripped[1:].strip()
            if current_list_key is not None and isinstance(fields.get(current_list_key), list):
                fields[current_list_key].append(_read_scalar(item))
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            continue  # not a key line; ignore rather than corrupt the rest
        key = key.strip()
        value = value.strip()
        if value == "":
            fields[key] = []
            current_list_key = key
        else:
            fields[key] = _read_scalar(value)
            current_list_key = None
    return fields


def _read_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            # Mirror _emit_scalar: backslash escapes are decoded so quoted
            # values round-trip (backslashes first would double-decode).
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return value


def _emit_scalar(value: str) -> str:
    # Quote only when a bare value would not round-trip: empty, surrounding
    # whitespace, an embedded quote, or a leading character a reader could
    # mistake for structure. Backslashes are escaped before quotes so
    # _read_scalar can decode unambiguously.
    if value == "" or value != value.strip() or '"' in value or value[:1] in ("-", "'", '"', "#"):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value
