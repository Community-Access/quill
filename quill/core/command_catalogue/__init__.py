"""The family command catalogue (docs/design/command-key.md, section 5).

One table says what every command is: its spoken name, aliases, example
sentences, description, arguments, risk class, surfaces and opposite. The
Command Palette, the push-to-talk voice commands, the AI agents' safe list and
the Command Key all read it; nothing is listed twice.

The runtime half -- whether a command can run *here, now* -- is the
:class:`~quill.core.commands.CommandRegistry` and its per-command probes. The
two halves are joined by command id.

QUILL Lite has no rows of its own. It reaches QUILL's rows through
``COMMAND_EQUIVALENTS``, so it can never offer a sentence QUILL cannot (rule 10).
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import cache

from quill.core.command_catalogue.editor import EDITOR_ROWS
from quill.core.command_catalogue.radio import RADIO_ROWS
from quill.core.command_catalogue.spec import Arg, ArgKind, CommandSpec, Kind, Risk

__all__ = [
    "APPS",
    "Arg",
    "ArgKind",
    "CommandSpec",
    "Kind",
    "Risk",
    "agent_ok_ids",
    "aliases_for",
    "all_rows",
    "lite_handler_for",
    "palette_alias_text",
    "row",
    "rows_for_app",
]

#: The apps with catalogue rows. ``lite`` is a view of ``quill``.
APPS: tuple[str, ...] = ("quill", "lite", "radio")

#: The prefix QUILL Lite's registry gives each handler (``lite_services``).
LITE_PREFIX = "lite."


def all_rows() -> tuple[CommandSpec, ...]:
    """Every row, in table order."""
    return EDITOR_ROWS + RADIO_ROWS


@cache
def _by_app() -> dict[str, dict[str, CommandSpec]]:
    tables: dict[str, dict[str, CommandSpec]] = {}
    for spec in all_rows():
        for app in spec.apps:
            tables.setdefault(app, {})[spec.id] = spec
    tables["lite"] = _lite_rows(tables.get("quill", {}))
    return tables


def _lite_rows(quill_rows: dict[str, CommandSpec]) -> dict[str, CommandSpec]:
    """QUILL Lite's view: QUILL's rows, under QUILL Lite's ids."""
    import dataclasses

    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    rows: dict[str, CommandSpec] = {}
    for handler, quill_id in COMMAND_EQUIVALENTS.items():
        spec = quill_rows.get(quill_id)
        if spec is None:
            continue
        lite_id = LITE_PREFIX + handler
        rows[lite_id] = dataclasses.replace(spec, id=lite_id, apps=("lite",))
    return rows


def rows_for_app(app: str) -> tuple[CommandSpec, ...]:
    """The rows *app* has, in table order. Unknown apps have none."""
    return tuple(_by_app().get(app, {}).values())


def row(command_id: str, app: str = "quill") -> CommandSpec | None:
    """The row for *command_id* in *app*, or None when it has none."""
    return _by_app().get(app, {}).get(command_id)


def lite_handler_for(quill_id: str) -> tuple[str, ...]:
    """QUILL Lite's handlers that mean *quill_id* (usually one, sometimes none)."""
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    return tuple(handler for handler, target in COMMAND_EQUIVALENTS.items() if target == quill_id)


def agent_ok_ids(app: str = "quill") -> tuple[str, ...]:
    """The ids the AI agents may run in *app*: the safe list, as a view."""
    return tuple(spec.id for spec in rows_for_app(app) if spec.agent_ok)


def aliases_for(command_id: str, app: str = "quill") -> tuple[str, ...]:
    """The aliases of *command_id*, or () when it has no row."""
    spec = row(command_id, app)
    return spec.aliases if spec is not None else ()


def palette_alias_text(command_id: str, apps: Iterable[str] = ("quill", "lite", "radio")) -> str:
    """The alias words the Command Palette searches for *command_id*.

    The palette has no idea which app it is in, and the ids are unique across
    the family, so it looks in every app it is given.
    """
    for app in apps:
        spec = row(command_id, app)
        if spec is not None:
            return " ".join(spec.aliases)
    return ""
