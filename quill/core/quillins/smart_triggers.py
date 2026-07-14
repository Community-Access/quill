"""Smart-trigger parsing for Quillin ``=name(args)`` commands (wx-free).

A *smart trigger* is a line the user types that is exactly ``=name(arg, arg)``
and activates on Enter, dispatching to a Quillin-contributed command. This
module is pure and unit-tested: it parses a line into a :class:`SmartTriggerMatch`
and builds an index of contributed :class:`SmartTriggerDef` definitions. The
wxPython host (``main_frame``) consumes both to detect and dispatch a trigger.

The parser deliberately requires the trigger to occupy the whole line (bar
surrounding whitespace) so ordinary prose containing ``=foo()`` never fires, and
requires a name-then-parens shape so a bare ``=5`` or spreadsheet-style ``=a+b``
is never mistaken for a trigger.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

# ^=name(...)$ — name starts with a letter; args captured raw for later split.
_LINE_RE = re.compile(r"^\s*=([A-Za-z][A-Za-z0-9_]*)\((.*)\)\s*$")


@dataclass(frozen=True, slots=True)
class SmartTriggerMatch:
    """A parsed ``=name(args)`` line."""

    name: str
    args: list[str]


@dataclass(frozen=True, slots=True)
class SmartTriggerDef:
    """A smart trigger contributed by a Quillin manifest."""

    name: str
    command_id: str
    quillin_id: str
    enabled_by_default: bool = True
    min_args: int | None = None
    max_args: int | None = None

    def accepts_arg_count(self, count: int) -> bool:
        """Return True when *count* satisfies the declared ``min``/``max`` bounds."""
        if self.min_args is not None and count < self.min_args:
            return False
        if self.max_args is not None and count > self.max_args:
            return False
        return True


@dataclass(frozen=True, slots=True)
class SmartTriggerResolution:
    """A matched trigger ready to dispatch: its definition plus parsed args."""

    definition: SmartTriggerDef
    args: list[str]


def parse_smart_trigger_line(line: str) -> SmartTriggerMatch | None:
    """Parse *line* as ``=name(args)``; return None when it is not a trigger.

    Arguments are comma-separated and individually stripped; empty arguments
    (e.g. a trailing comma) are dropped so ``=rand(10,)`` yields one argument.
    """
    match = _LINE_RE.match(line)
    if match is None:
        return None
    name = match.group(1)
    raw_args = match.group(2).strip()
    if not raw_args:
        return SmartTriggerMatch(name, [])
    args = [part.strip() for part in raw_args.split(",")]
    args = [part for part in args if part]
    return SmartTriggerMatch(name, args)


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def smart_trigger_def_from_dict(data: object, quillin_id: str) -> SmartTriggerDef | None:
    """Build a :class:`SmartTriggerDef` from a raw manifest dict, or None if invalid."""
    if not isinstance(data, dict):
        return None
    name = str(data.get("trigger", "")).strip()
    command_id = str(data.get("command", "")).strip()
    if not name or not command_id:
        return None
    return SmartTriggerDef(
        name=name,
        command_id=command_id,
        quillin_id=quillin_id,
        enabled_by_default=bool(data.get("enabled_by_default", True)),
        min_args=_optional_int(data.get("min_args")),
        max_args=_optional_int(data.get("max_args")),
    )


def build_smart_trigger_index(
    contributions: Iterable[tuple[str, Iterable[object]]],
) -> dict[str, SmartTriggerDef]:
    """Index contributed smart triggers by name across manifests.

    *contributions* pairs a ``quillin_id`` with that manifest's raw smart-trigger
    dicts. On a name collision the first definition wins (load order), matching
    the command-id collision policy in the registry. Malformed entries are
    skipped rather than raising, so one bad Quillin never breaks the others.
    """
    index: dict[str, SmartTriggerDef] = {}
    for quillin_id, triggers in contributions:
        for raw in triggers:
            definition = smart_trigger_def_from_dict(raw, quillin_id)
            if definition is None or definition.name in index:
                continue
            index[definition.name] = definition
    return index


def resolve_smart_trigger(
    match: SmartTriggerMatch,
    index: dict[str, SmartTriggerDef],
    *,
    is_enabled: Callable[[SmartTriggerDef], bool],
) -> SmartTriggerResolution | None:
    """Resolve a parsed *match* to a dispatchable trigger, or None.

    Returns None when the name is unknown, the trigger is disabled (per
    *is_enabled*, which the host wires to the feature gate and per-Quillin
    settings), or the argument count is outside the declared bounds.
    """
    definition = index.get(match.name)
    if definition is None:
        return None
    if not is_enabled(definition):
        return None
    if not definition.accepts_arg_count(len(match.args)):
        return None
    return SmartTriggerResolution(definition, match.args)
