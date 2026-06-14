"""Hand-rolled validation for ``quill.extension/1`` manifests.

QUILL ships no ``jsonschema`` dependency (see ``pyproject.toml`` — runtime deps
are only ``regex`` and ``defusedxml``), so the normative manifest contract from
``docs/quillins.md`` §13 is enforced here in pure, strictly-typed Python, the
same hand-rolled-validator style used by the other ``quill/core`` stores.

The published JSON Schema artifact lives at
``quill/core/schemas/extension.json`` for humans and external tools; this module
is the authority the loader actually enforces. ``tests`` assert the two agree.

Public API:

* :func:`validate_manifest` — return a list of human-readable problems (empty
  when the manifest is valid). Never raises for a malformed manifest.
* :func:`parse_manifest` — return a fully built :class:`ExtensionManifest`, or
  raise :class:`ManifestError` carrying every problem found.
"""

from __future__ import annotations

import re

from quill.core.quillins.model import (
    CAP_UI_COMMAND,
    CAPABILITIES,
    CONTEXT_WHEN_ALWAYS,
    CONTEXT_WHEN_VALUES,
    MENU_PARENTS,
    RUNTIME_NODE,
    RUNTIME_PYTHON,
    RUNTIMES,
    SCHEMA_ID,
    ContextMenuContribution,
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
    HotkeyContribution,
    ManifestError,
    MenuContribution,
)

_ID_PATTERN = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")
_COMMAND_ID_PATTERN = re.compile(r"^ext\.[a-z0-9]+([._-][a-z0-9]+)*$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_MAIN_PYTHON_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+\.py$")
_MAIN_JS_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+\.js$")
_MAIN_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+\.(py|js)$")

_TOP_LEVEL_KEYS = frozenset({
    "schema",
    "id",
    "name",
    "version",
    "author",
    "description",
    "license",
    "min_quill_version",
    "capabilities",
    "main",
    "runtime",
    "contributes",
})
_CONTRIBUTES_KEYS = frozenset({
    "commands",
    "menus",
    "context_menu",
    "hotkeys",
    "sound_pack",
    "sound_events",
})
_COMMAND_KEYS = frozenset({"id", "title", "run"})
_MENU_KEYS = frozenset({"parent", "command"})
_CONTEXT_KEYS = frozenset({"command", "when"})
_HOTKEY_KEYS = frozenset({"command", "binding"})


def _require_str(value: object, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be a string")
        return None
    return value


def _check_unknown_keys(
    mapping: dict[str, object], allowed: frozenset[str], label: str, errors: list[str]
) -> None:
    for key in mapping:
        if key not in allowed:
            errors.append(f"{label} has unknown property '{key}'")


def _validate_capabilities(value: object, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(value, list):
        errors.append("capabilities must be an array")
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"capabilities[{index}] must be a string")
            continue
        if item not in CAPABILITIES:
            errors.append(f"capabilities[{index}] is not a known capability: '{item}'")
            continue
        if item in seen:
            errors.append(f"capabilities[{index}] is a duplicate: '{item}'")
            continue
        seen.add(item)
        result.append(item)
    return tuple(result)


def _validate_command(
    raw: object, index: int, errors: list[str]
) -> tuple[ExtensionCommand | None, bool]:
    """Return (command, uses_handler). ``command`` is None when invalid."""

    if not isinstance(raw, dict):
        errors.append(f"contributes.commands[{index}] must be an object")
        return None, False
    label = f"contributes.commands[{index}]"
    _check_unknown_keys(raw, _COMMAND_KEYS, label, errors)

    command_id = _require_str(raw.get("id"), f"{label}.id", errors)
    if command_id is not None and not _COMMAND_ID_PATTERN.match(command_id):
        errors.append(f"{label}.id must match 'ext.<name>' (got '{command_id}')")
        command_id = None

    title = _require_str(raw.get("title"), f"{label}.title", errors)
    if title is not None and not (1 <= len(title) <= 80):
        errors.append(f"{label}.title must be 1-80 characters")

    snippet: str | None = None
    handler: str | None = None
    uses_handler = False
    run = raw.get("run")
    if not isinstance(run, dict):
        errors.append(f"{label}.run must be an object with exactly one of snippet or handler")
    else:
        has_snippet = "snippet" in run
        has_handler = "handler" in run
        extra = set(run) - {"snippet", "handler"}
        if extra:
            errors.append(f"{label}.run has unknown property '{sorted(extra)[0]}'")
        if has_snippet == has_handler:
            errors.append(f"{label}.run must have exactly one of snippet or handler")
        elif has_snippet:
            snippet = _require_str(run.get("snippet"), f"{label}.run.snippet", errors)
        else:
            handler = _require_str(run.get("handler"), f"{label}.run.handler", errors)
            uses_handler = handler is not None

    if command_id is None or title is None:
        return None, uses_handler
    if snippet is None and handler is None:
        return None, uses_handler
    return ExtensionCommand(
        id=command_id, title=title, snippet=snippet, handler=handler
    ), uses_handler


def _validate_menus(raw: object, errors: list[str]) -> tuple[MenuContribution, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.menus must be an array")
        return ()
    result: list[MenuContribution] = []
    for index, item in enumerate(raw):
        label = f"contributes.menus[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _MENU_KEYS, label, errors)
        parent = _require_str(item.get("parent"), f"{label}.parent", errors)
        command = _require_str(item.get("command"), f"{label}.command", errors)
        if parent is not None and parent not in MENU_PARENTS:
            errors.append(f"{label}.parent must be one of {list(MENU_PARENTS)} (got '{parent}')")
            parent = None
        if parent is not None and command is not None:
            result.append(MenuContribution(parent=parent, command=command))
    return tuple(result)


def _validate_context_menu(raw: object, errors: list[str]) -> tuple[ContextMenuContribution, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.context_menu must be an array")
        return ()
    result: list[ContextMenuContribution] = []
    for index, item in enumerate(raw):
        label = f"contributes.context_menu[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _CONTEXT_KEYS, label, errors)
        command = _require_str(item.get("command"), f"{label}.command", errors)
        when = CONTEXT_WHEN_ALWAYS
        if "when" in item:
            raw_when = _require_str(item.get("when"), f"{label}.when", errors)
            if raw_when is not None and raw_when not in CONTEXT_WHEN_VALUES:
                errors.append(
                    f"{label}.when must be one of {list(CONTEXT_WHEN_VALUES)} (got '{raw_when}')"
                )
            elif raw_when is not None:
                when = raw_when
        if command is not None:
            result.append(ContextMenuContribution(command=command, when=when))
    return tuple(result)


def _validate_hotkeys(raw: object, errors: list[str]) -> tuple[HotkeyContribution, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.hotkeys must be an array")
        return ()
    result: list[HotkeyContribution] = []
    for index, item in enumerate(raw):
        label = f"contributes.hotkeys[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _HOTKEY_KEYS, label, errors)
        command = _require_str(item.get("command"), f"{label}.command", errors)
        binding = _require_str(item.get("binding"), f"{label}.binding", errors)
        if binding is not None and not binding.strip():
            errors.append(f"{label}.binding must not be empty")
            binding = None
        if command is not None and binding is not None:
            result.append(HotkeyContribution(command=command, binding=binding))
    return tuple(result)


def _validate_contributes(raw: object, errors: list[str]) -> tuple[Contributions, list[str], bool]:
    """Return (contributions, contributed_command_ids, any_handler_command)."""

    if not isinstance(raw, dict):
        errors.append("contributes must be an object")
        return Contributions(), [], False
    _check_unknown_keys(raw, _CONTRIBUTES_KEYS, "contributes", errors)

    commands: list[ExtensionCommand] = []
    contributed_ids: list[str] = []
    any_handler = False
    raw_commands = raw.get("commands", [])
    if not isinstance(raw_commands, list):
        errors.append("contributes.commands must be an array")
    else:
        seen_ids: set[str] = set()
        for index, item in enumerate(raw_commands):
            command, uses_handler = _validate_command(item, index, errors)
            any_handler = any_handler or uses_handler
            if command is None:
                continue
            if command.id in seen_ids:
                errors.append(f"contributes.commands[{index}].id is a duplicate: '{command.id}'")
                continue
            seen_ids.add(command.id)
            commands.append(command)
            contributed_ids.append(command.id)

    menus = _validate_menus(raw.get("menus", []), errors)
    context_menu = _validate_context_menu(raw.get("context_menu", []), errors)
    hotkeys = _validate_hotkeys(raw.get("hotkeys", []), errors)
    sound_pack = str(raw["sound_pack"]) if isinstance(raw.get("sound_pack"), str) else ""
    raw_se = raw.get("sound_events")
    sound_events: tuple[tuple[str, str], ...] = ()
    if isinstance(raw_se, dict):
        sound_events = tuple(
            (str(k), str(v)) for k, v in raw_se.items() if isinstance(k, str) and isinstance(v, str)
        )

    contributions = Contributions(
        commands=tuple(commands),
        menus=menus,
        context_menu=context_menu,
        hotkeys=hotkeys,
        sound_pack=sound_pack,
        sound_events=sound_events,
    )
    return contributions, contributed_ids, any_handler


def _validate_command_references(
    contributions: Contributions,
    contributed_ids: list[str],
    builtin_command_ids: frozenset[str] | None,
    errors: list[str],
) -> None:
    """Every menu/context/hotkey command must resolve to a known command id.

    A reference is valid when it is a contributed ``ext.*`` id, or — when a set
    of built-in ids is supplied — a known built-in id. References to built-in ids
    are accepted unchecked when no built-in set is provided (validation has no
    inherent knowledge of the host keymap).
    """

    known = set(contributed_ids)

    def _check(command: str, where: str) -> None:
        if command in known:
            return
        if command.startswith("ext."):
            errors.append(f"{where} references unknown contributed command '{command}'")
            return
        if builtin_command_ids is not None and command not in builtin_command_ids:
            errors.append(f"{where} references unknown built-in command '{command}'")

    for index, menu in enumerate(contributions.menus):
        _check(menu.command, f"contributes.menus[{index}].command")
    for index, entry in enumerate(contributions.context_menu):
        _check(entry.command, f"contributes.context_menu[{index}].command")
    for index, hotkey in enumerate(contributions.hotkeys):
        _check(hotkey.command, f"contributes.hotkeys[{index}].command")


def validate_manifest(
    raw: object, *, builtin_command_ids: frozenset[str] | None = None
) -> list[str]:
    """Validate a parsed manifest object and return human-readable problems.

    Returns an empty list when ``raw`` is a valid ``quill.extension/1`` manifest.
    Optionally pass ``builtin_command_ids`` to additionally verify that every
    menu/context/hotkey reference to a non-``ext.`` command names a real built-in.
    """

    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["manifest must be a JSON object"]
    _check_unknown_keys(raw, _TOP_LEVEL_KEYS, "manifest", errors)

    schema = raw.get("schema")
    if schema != SCHEMA_ID:
        errors.append(f"schema must be '{SCHEMA_ID}' (got {schema!r})")

    extension_id = _require_str(raw.get("id"), "id", errors)
    if extension_id is not None:
        if not _ID_PATTERN.match(extension_id):
            errors.append(
                "id must be lowercase reverse-DNS matching '^[a-z0-9]+([._-][a-z0-9]+)*$'"
            )
        if not (3 <= len(extension_id) <= 128):
            errors.append("id must be 3-128 characters")

    name = _require_str(raw.get("name"), "name", errors)
    if name is not None and not (1 <= len(name) <= 80):
        errors.append("name must be 1-80 characters")

    version = _require_str(raw.get("version"), "version", errors)
    if version is not None and not _VERSION_PATTERN.match(version):
        errors.append("version must be MAJOR.MINOR.PATCH")

    if "author" in raw:
        candidate = _require_str(raw.get("author"), "author", errors)
        if candidate is not None and len(candidate) > 120:
            errors.append("author must be at most 120 characters")

    if "description" in raw:
        candidate = _require_str(raw.get("description"), "description", errors)
        if candidate is not None and len(candidate) > 400:
            errors.append("description must be at most 400 characters")

    if "license" in raw:
        candidate = _require_str(raw.get("license"), "license", errors)
        if candidate is not None and len(candidate) > 64:
            errors.append("license must be at most 64 characters")

    if "min_quill_version" in raw:
        candidate = _require_str(raw.get("min_quill_version"), "min_quill_version", errors)
        if candidate is not None and not _VERSION_PATTERN.match(candidate):
            errors.append("min_quill_version must be MAJOR.MINOR.PATCH")

    runtime = RUNTIME_PYTHON
    if "runtime" in raw:
        runtime_raw = raw.get("runtime")
        if not isinstance(runtime_raw, str) or runtime_raw not in RUNTIMES:
            errors.append(f"runtime must be one of {sorted(RUNTIMES)} (got {runtime_raw!r})")
        else:
            runtime = runtime_raw

    capabilities: tuple[str, ...] = ()
    if "capabilities" in raw:
        capabilities = _validate_capabilities(raw.get("capabilities"), errors)

    main: str | None = None
    if "main" in raw:
        candidate = _require_str(raw.get("main"), "main", errors)
        if candidate is not None:
            if not _MAIN_PATTERN.match(candidate):
                errors.append("main must be a relative '*.py' or '*.js' path")
            elif runtime == RUNTIME_NODE and not _MAIN_JS_PATTERN.match(candidate):
                errors.append("node runtime requires main to be a '*.js' path")
            elif runtime == RUNTIME_PYTHON and not _MAIN_PYTHON_PATTERN.match(candidate):
                errors.append("python runtime requires main to be a '*.py' path")
            else:
                main = candidate

    contributions = Contributions()
    contributed_ids: list[str] = []
    any_handler = False
    if "contributes" in raw:
        contributions, contributed_ids, any_handler = _validate_contributes(
            raw.get("contributes"), errors
        )
        _validate_command_references(contributions, contributed_ids, builtin_command_ids, errors)

    # docs/quillins.md §15 rule 6: a handler command requires an entry module
    # (Python or Node) and the ui.command capability.
    if any_handler:
        if main is None:
            errors.append("a command using run.handler requires a top-level 'main' module")
        if CAP_UI_COMMAND not in capabilities:
            errors.append("a command using run.handler requires the 'ui.command' capability")

    return errors


def parse_manifest(
    raw: object, *, builtin_command_ids: frozenset[str] | None = None
) -> ExtensionManifest:
    """Build an :class:`ExtensionManifest`, raising :class:`ManifestError`.

    Re-runs validation to guarantee the assembled manifest is well-formed, then
    constructs the immutable model. Because validation already proved the shape,
    the assembly below performs only narrow, defensive coercion.
    """

    errors = validate_manifest(raw, builtin_command_ids=builtin_command_ids)
    if errors:
        raise ManifestError(errors)
    assert isinstance(raw, dict)  # validation guarantees this

    contributions, _ids, _handler = _validate_contributes(raw.get("contributes", {}), [])
    capabilities = _validate_capabilities(raw.get("capabilities", []), [])
    main_value = raw.get("main")
    main = main_value if isinstance(main_value, str) else None
    runtime_raw = raw.get("runtime", RUNTIME_PYTHON)
    runtime = (
        runtime_raw if isinstance(runtime_raw, str) and runtime_raw in RUNTIMES else RUNTIME_PYTHON
    )

    return ExtensionManifest(
        id=str(raw["id"]),
        name=str(raw["name"]),
        version=str(raw["version"]),
        author=str(raw.get("author", "")),
        description=str(raw.get("description", "")),
        license=str(raw.get("license", "")),
        min_quill_version=str(raw.get("min_quill_version", "")),
        capabilities=capabilities,
        main=main,
        runtime=runtime,
        contributes=contributions,
    )
