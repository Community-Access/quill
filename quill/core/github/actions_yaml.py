"""Reading and writing the YAML of workflow and Dependabot files (GitHub PRD 22.1).

The Workbench edits ``.github/workflows/*.yml`` and ``.github/dependabot.yml``
as forms, so it has to read and write their YAML without changing what the
file means. Two things PyYAML gets wrong for these files by default, put
right here:

* **``on`` is a key, not a yes.** YAML 1.1 reads ``on``, ``off``, ``yes``
  and ``no`` as true and false, so a plain ``safe_load`` turns a workflow's
  ``on:`` into the key ``True``. GitHub reads YAML 1.2, where only ``true``
  and ``false`` are booleans; :class:`_Loader` and :class:`_Dumper` do the
  same, so ``on:`` is read and written as ``on:``.
* **Lists are indented under their key** and multi-line ``run:`` scripts are
  written as ``|`` blocks, the way people write workflows, so a saved file
  reads like the one that was opened.

What the repository's YAML tooling cannot do: PyYAML (the only YAML library
QUILL ships) drops comments inside the file. :func:`dump_mapping` keeps the
comment block at the top of the file, and a file the form did not change is
never rewritten at all (the caller compares before saving); the editors say
so in one sentence and offer the source for anything else. Keeping every
comment would need ``ruamel.yaml``, a new dependency that has not been
added.

Read with ``safe_load`` semantics only: no tags, no objects. wx-free and
strict-typed.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import yaml  # type: ignore[import-untyped]

from quill.core.error_codes import CodedError

__all__ = [
    "COMMENTS_NOTE",
    "ActionsYamlError",
    "dump_mapping",
    "header_comments",
    "load_mapping",
    "same_data",
    "scalar",
    "scalar_text",
]

#: The one sentence the editors say about comments.
COMMENTS_NOTE = (
    "Saving from this window keeps the comments at the top of the file; comments "
    "inside it are not kept. To keep those, edit the source instead."
)

_MAX_BYTES = 200_000
_BOOL = "tag:yaml.org,2002:bool"
_YAML12_BOOL = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")


class ActionsYamlError(CodedError):
    """A workflow or Dependabot file could not be read as YAML; the message says why."""

    code = "QUILL-GITHUB-ACTIONS-YAML-INVALID"


def _yaml12_resolvers(base: Any) -> dict[Any, list[Any]]:
    resolvers: dict[Any, list[Any]] = {}
    for first, pairs in base.yaml_implicit_resolvers.items():
        kept = [pair for pair in pairs if pair[0] != _BOOL]
        if kept:
            resolvers[first] = kept
    for first in "tTfF":
        resolvers.setdefault(first, []).append((_BOOL, _YAML12_BOOL))
    return resolvers


class _Loader(yaml.SafeLoader):  # type: ignore[misc]
    """``safe_load`` with YAML 1.2 booleans, so ``on`` stays a string."""


_Loader.yaml_implicit_resolvers = _yaml12_resolvers(yaml.SafeLoader)


class _Dumper(yaml.SafeDumper):  # type: ignore[misc]
    """``safe_dump`` that writes ``on`` bare, indents lists and blocks scripts."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> Any:
        return super().increase_indent(flow, False)


_Dumper.yaml_implicit_resolvers = _yaml12_resolvers(yaml.SafeDumper)


def _represent_text(dumper: Any, value: str) -> Any:
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


def _represent_none(dumper: Any, _value: None) -> Any:
    # ``workflow_dispatch:`` with nothing after it, as people write it.
    return dumper.represent_scalar("tag:yaml.org,2002:null", "")


_Dumper.add_representer(str, _represent_text)
_Dumper.add_representer(type(None), _represent_none)


def header_comments(text: str) -> str:
    """The comment lines (and blank lines between them) at the top of *text*."""
    kept: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or (not stripped and kept):
            kept.append(line.rstrip())
            continue
        break
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept)


def load_mapping(text: str, what: str) -> dict[str, Any]:
    """The top level of *text* as a dictionary; *what* names the file in errors."""
    if len(text.encode("utf-8")) > _MAX_BYTES:
        raise ActionsYamlError(
            f"The {what} is larger than {_MAX_BYTES // 1000} KB; edit its source instead."
        )
    try:
        data = yaml.load(text, Loader=_Loader) if text.strip() else {}  # noqa: S506 - safe loader
    except yaml.YAMLError as exc:
        where = getattr(exc, "problem_mark", None)
        line = f" at line {where.line + 1}" if where is not None else ""
        problem = getattr(exc, "problem", None) or "it is not valid YAML"
        raise ActionsYamlError(
            f"The {what} cannot be read{line}: {problem}. Edit its source to fix it."
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ActionsYamlError(f"The {what}'s top level is not a set of keys.")
    return {str(key): value for key, value in data.items()}


def dump_mapping(data: dict[str, Any], header: str = "") -> str:
    """*data* as YAML, keys in their order, after the *header* comment block."""
    body = str(
        yaml.dump(
            data,
            Dumper=_Dumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=4096,
        )
    )
    if header.strip():
        return header.rstrip() + "\n\n" + body
    return body


def same_data(first: Any, second: Any) -> bool:
    """Whether two loaded documents mean the same (deep, order of keys included)."""
    return bool(
        copy.deepcopy(first) == copy.deepcopy(second) and list(_keys(first)) == list(_keys(second))
    )


def _keys(value: Any) -> list[Any]:
    if isinstance(value, dict):
        out: list[Any] = []
        for key, inner in value.items():
            out.append(key)
            out.extend(_keys(inner))
        return out
    if isinstance(value, list):
        out = []
        for inner in value:
            out.extend(_keys(inner))
        return out
    return []


def scalar(text: str) -> Any:
    """One typed value as YAML reads it ("0" is 0, "true" is true), else the text."""
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        value = yaml.load(stripped, Loader=_Loader)  # noqa: S506 - safe loader
    except yaml.YAMLError:
        return stripped
    if value is None or isinstance(value, (str, int, float, bool)):
        return stripped if value is None else value
    return stripped


def scalar_text(value: Any) -> str:
    """A value as it is typed in a form: true and false in lower case, None as nothing."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
