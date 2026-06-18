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
    CAP_DOCUMENT_EVENTS,
    CAP_NET,
    CAP_SCHEDULE,
    CAP_SETTINGS_OWN_READ,
    CAP_SETTINGS_OWN_WRITE,
    CAP_UI_COMMAND,
    CAP_UI_STATUS,
    CAPABILITIES,
    CONTEXT_WHEN_ALWAYS,
    CONTEXT_WHEN_VALUES,
    DOCUMENT_EVENTS,
    MENU_PARENTS,
    QUILLIN_CATEGORIES,
    RUNTIME_NODE,
    RUNTIME_PYTHON,
    RUNTIMES,
    SCHEMA_ID,
    ContextMenuContribution,
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
    FileTypeContribution,
    HotkeyContribution,
    ManifestError,
    MenuContribution,
    RequiresDependency,
    ScheduleContribution,
    SnippetGalleryEntry,
    SnippetParam,
    StatusBarContribution,
)

_ID_PATTERN = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")
_HOSTNAME_PATTERN = re.compile(
    r"^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)
_COMMAND_ID_PATTERN = re.compile(r"^ext\.[a-z0-9]+([._-][a-z0-9]+)*$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_MAIN_PYTHON_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+\.py$")
_MAIN_JS_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+\.js$")
_MAIN_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+\.(py|js)$")
_SMART_TRIGGER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9._-]*$")

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
    "categories",
    "requires",
    "net_allowed_hosts",
})
_CONTRIBUTES_KEYS = frozenset({
    "commands",
    "menus",
    "context_menu",
    "hotkeys",
    "sound_pack",
    "sound_events",
    "abbreviations",
    "smart_triggers",
    "preferences",
    "document_events",
    "status_bar",
    "schedule",
    "file_types",
    "snippet_gallery",
})
_COMMAND_KEYS = frozenset({"id", "title", "description", "run"})
_SCHEDULE_KEYS = frozenset({"id", "interval_seconds", "handler", "description"})
_FILE_TYPE_KEYS = frozenset({"extensions", "handler", "description"})
_SNIPPET_GALLERY_KEYS = frozenset({
    "id",
    "name",
    "body",
    "description",
    "category",
    "params",
})
_SNIPPET_PARAM_KEYS = frozenset({"name", "label", "default"})
_STATUS_BAR_KEYS = frozenset({"id", "label", "handler", "tooltip", "width"})
_REQUIRES_KEYS = frozenset({"id", "min_version"})
_MENU_KEYS = frozenset({"parent", "command"})
_CONTEXT_KEYS = frozenset({"command", "when"})
_HOTKEY_KEYS = frozenset({"command", "binding"})
_ABBREVIATION_KEYS = frozenset({
    "trigger",
    "expansion",
    "handler",
    "description",
    "category",
    "enabled_by_default",
    "case_sensitive",
    "file_extensions",
})
_SMART_TRIGGER_KEYS = frozenset({
    "trigger",
    "command",
    "syntax",
    "description",
    "category",
    "enabled_by_default",
    "min_args",
    "max_args",
    "large_insert_threshold",
    "file_extensions",
})
_PREF_PAGE_KEYS = frozenset({
    "id",
    "title",
    "parent",
    "section",
    "placement",
    "description",
    "tabs",
    "sections",
    "settings",
})
_PREF_TAB_KEYS = frozenset({
    "id",
    "title",
    "description",
    "order",
    "sections",
    "visible_when",
    "enabled_when",
})
_PREF_SECTION_KEYS = frozenset({
    "id",
    "title",
    "description",
    "order",
    "settings",
    "visible_when",
    "enabled_when",
})
_PREF_SETTING_KEYS = frozenset({
    "key",
    "label",
    "type",
    "default",
    "description",
    "choices",
    "minimum",
    "maximum",
    "step",
    "placeholder",
    "requires_restart",
    "visible_when",
    "enabled_when",
    "advanced",
    "sensitive",
    "search_keywords",
})
_PREF_SETTING_TYPES = frozenset({
    "boolean",
    "choice",
    "radio",
    "string",
    "text",
    "integer",
    "number",
    "path",
    "password",
    "list",
    "action",
    "info",
})
_PREF_CONDITION_KEYS = frozenset({"setting", "equals"})
_DOCUMENT_EVENT_KEYS = frozenset({
    "event",
    "handler",
    "title",
    "description",
    "conditions",
    "filter_extensions",
    "enabled_by_default",
})
_DOCUMENT_EVENT_CONDITION_KEYS = frozenset({
    "file_extension",
    "file_path_pattern",
    "content_pattern",
})


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

    description = ""
    if "description" in raw:
        desc_raw = _require_str(raw.get("description"), f"{label}.description", errors)
        if desc_raw is not None:
            if len(desc_raw) > 400:
                errors.append(f"{label}.description must be at most 400 characters")
            else:
                description = desc_raw

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
        id=command_id, title=title, description=description, snippet=snippet, handler=handler
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


def _validate_file_extensions_list(raw: object, label: str, errors: list[str]) -> None:
    """Each element of a file_extensions array must be a dot-prefixed string."""

    if not isinstance(raw, list):
        errors.append(f"{label} must be an array")
        return
    for i, ext in enumerate(raw):
        if not isinstance(ext, str):
            errors.append(f"{label}[{i}] must be a string")
        elif not ext.startswith("."):
            errors.append(f"{label}[{i}] must start with '.' (got '{ext}')")


def _validate_abbreviations(raw: object, errors: list[str]) -> tuple[tuple[object, ...], bool]:
    """Return (entries, any_handler_abbreviation)."""

    if not isinstance(raw, list):
        errors.append("contributes.abbreviations must be an array")
        return (), False
    result: list[object] = []
    any_handler = False
    seen_triggers: set[str] = set()
    for index, item in enumerate(raw):
        label = f"contributes.abbreviations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _ABBREVIATION_KEYS, label, errors)
        trigger = _require_str(item.get("trigger"), f"{label}.trigger", errors)
        if trigger is not None:
            if not (1 <= len(trigger) <= 64):
                errors.append(f"{label}.trigger must be 1-64 characters")
            elif trigger in seen_triggers:
                errors.append(f"{label}.trigger is a duplicate: '{trigger}'")
            else:
                seen_triggers.add(trigger)
        desc = _require_str(item.get("description"), f"{label}.description", errors)
        if desc is not None and len(desc) > 200:
            errors.append(f"{label}.description must be at most 200 characters")
        has_expansion = "expansion" in item
        has_handler = "handler" in item
        if has_expansion == has_handler:
            errors.append(f"{label} must have exactly one of 'expansion' or 'handler'")
        elif has_handler:
            h = _require_str(item.get("handler"), f"{label}.handler", errors)
            if h is not None:
                any_handler = True
        if "file_extensions" in item:
            _validate_file_extensions_list(
                item["file_extensions"], f"{label}.file_extensions", errors
            )
        result.append(item)
    return tuple(result), any_handler


def _validate_smart_triggers(raw: object, errors: list[str]) -> tuple[object, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.smart_triggers must be an array")
        return ()
    result: list[object] = []
    seen_names: set[str] = set()
    for index, item in enumerate(raw):
        label = f"contributes.smart_triggers[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _SMART_TRIGGER_KEYS, label, errors)
        trigger = _require_str(item.get("trigger"), f"{label}.trigger", errors)
        if trigger is not None:
            if not _SMART_TRIGGER_NAME_PATTERN.match(trigger):
                errors.append(f"{label}.trigger must match '^[a-z][a-z0-9._-]*$' (got '{trigger}')")
            elif len(trigger) > 64:
                errors.append(f"{label}.trigger must be at most 64 characters")
            elif trigger in seen_names:
                errors.append(f"{label}.trigger is a duplicate: '{trigger}'")
            else:
                seen_names.add(trigger)
        _require_str(item.get("command"), f"{label}.command", errors)
        _require_str(item.get("syntax"), f"{label}.syntax", errors)
        desc = _require_str(item.get("description"), f"{label}.description", errors)
        if desc is not None and len(desc) > 200:
            errors.append(f"{label}.description must be at most 200 characters")
        min_args = item.get("min_args")
        max_args = item.get("max_args")
        if isinstance(min_args, int) and isinstance(max_args, int) and min_args > max_args:
            errors.append(f"{label}.min_args ({min_args}) must not exceed max_args ({max_args})")
        if "file_extensions" in item:
            _validate_file_extensions_list(
                item["file_extensions"], f"{label}.file_extensions", errors
            )
        result.append(item)
    return tuple(result)


def _validate_pref_condition(raw: object, label: str, errors: list[str]) -> None:
    if not isinstance(raw, dict):
        errors.append(f"{label} must be an object with 'setting' and 'equals'")
        return
    _check_unknown_keys(raw, _PREF_CONDITION_KEYS, label, errors)
    if "setting" not in raw:
        errors.append(f"{label} must have 'setting'")
    else:
        _require_str(raw.get("setting"), f"{label}.setting", errors)
    if "equals" not in raw:
        errors.append(f"{label} must have 'equals'")


def _validate_pref_settings_list(raw: object, label: str, errors: list[str]) -> None:
    if not isinstance(raw, list):
        errors.append(f"{label} must be an array")
        return
    for si, setting in enumerate(raw):
        slabel = f"{label}[{si}]"
        if not isinstance(setting, dict):
            errors.append(f"{slabel} must be an object")
            continue
        _check_unknown_keys(setting, _PREF_SETTING_KEYS, slabel, errors)
        _require_str(setting.get("key"), f"{slabel}.key", errors)
        _require_str(setting.get("label"), f"{slabel}.label", errors)
        stype = _require_str(setting.get("type"), f"{slabel}.type", errors)
        if stype is not None and stype not in _PREF_SETTING_TYPES:
            errors.append(
                f"{slabel}.type must be one of {sorted(_PREF_SETTING_TYPES)} (got '{stype}')"
            )
        if "default" not in setting:
            errors.append(f"{slabel} must have 'default'")
        if "description" not in setting:
            errors.append(f"{slabel} must have 'description'")
        if "search_keywords" in setting:
            kws = setting["search_keywords"]
            if not isinstance(kws, list):
                errors.append(f"{slabel}.search_keywords must be an array")
            else:
                for ki, kw in enumerate(kws):
                    if not isinstance(kw, str):
                        errors.append(f"{slabel}.search_keywords[{ki}] must be a string")
                    elif len(kw) > 64:
                        errors.append(
                            f"{slabel}.search_keywords[{ki}] must be at most 64 characters"
                        )
        if "visible_when" in setting:
            _validate_pref_condition(setting["visible_when"], f"{slabel}.visible_when", errors)
        if "enabled_when" in setting:
            _validate_pref_condition(setting["enabled_when"], f"{slabel}.enabled_when", errors)


def _validate_pref_sections_list(raw: object, label: str, errors: list[str]) -> None:
    if not isinstance(raw, list):
        errors.append(f"{label} must be an array")
        return
    for si, section in enumerate(raw):
        slabel = f"{label}[{si}]"
        if not isinstance(section, dict):
            errors.append(f"{slabel} must be an object")
            continue
        _check_unknown_keys(section, _PREF_SECTION_KEYS, slabel, errors)
        _require_str(section.get("id"), f"{slabel}.id", errors)
        title = _require_str(section.get("title"), f"{slabel}.title", errors)
        if title is not None and not (1 <= len(title) <= 80):
            errors.append(f"{slabel}.title must be 1-80 characters")
        if "settings" in section:
            _validate_pref_settings_list(section["settings"], f"{slabel}.settings", errors)
        if "visible_when" in section:
            _validate_pref_condition(section["visible_when"], f"{slabel}.visible_when", errors)
        if "enabled_when" in section:
            _validate_pref_condition(section["enabled_when"], f"{slabel}.enabled_when", errors)


def _validate_pref_tabs(raw: object, parent_label: str, errors: list[str]) -> None:
    if not isinstance(raw, list):
        errors.append(f"{parent_label}.tabs must be an array")
        return
    for ti, tab in enumerate(raw):
        tlabel = f"{parent_label}.tabs[{ti}]"
        if not isinstance(tab, dict):
            errors.append(f"{tlabel} must be an object")
            continue
        _check_unknown_keys(tab, _PREF_TAB_KEYS, tlabel, errors)
        _require_str(tab.get("id"), f"{tlabel}.id", errors)
        title = _require_str(tab.get("title"), f"{tlabel}.title", errors)
        if title is not None and not (1 <= len(title) <= 60):
            errors.append(f"{tlabel}.title must be 1-60 characters")
        if "description" not in tab:
            errors.append(f"{tlabel} must have 'description'")
        if "order" not in tab or not isinstance(tab.get("order"), int):
            errors.append(f"{tlabel} must have 'order' as an integer")
        if "sections" in tab:
            _validate_pref_sections_list(tab["sections"], f"{tlabel}.sections", errors)
        if "visible_when" in tab:
            _validate_pref_condition(tab["visible_when"], f"{tlabel}.visible_when", errors)
        if "enabled_when" in tab:
            _validate_pref_condition(tab["enabled_when"], f"{tlabel}.enabled_when", errors)


def _validate_preferences(raw: object, errors: list[str]) -> tuple[object, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.preferences must be an array")
        return ()
    result: list[object] = []
    for index, page in enumerate(raw):
        label = f"contributes.preferences[{index}]"
        if not isinstance(page, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(page, _PREF_PAGE_KEYS, label, errors)
        _require_str(page.get("id"), f"{label}.id", errors)
        title = _require_str(page.get("title"), f"{label}.title", errors)
        if title is not None and not (1 <= len(title) <= 80):
            errors.append(f"{label}.title must be 1-80 characters")
        desc = _require_str(page.get("description"), f"{label}.description", errors)
        if desc is not None and len(desc) > 400:
            errors.append(f"{label}.description must be at most 400 characters")
        if "tabs" in page:
            _validate_pref_tabs(page["tabs"], label, errors)
        if "sections" in page:
            _validate_pref_sections_list(page["sections"], f"{label}.sections", errors)
        if "settings" in page:
            _validate_pref_settings_list(page["settings"], f"{label}.settings", errors)
        result.append(page)
    return tuple(result)


def _validate_document_events(raw: object, errors: list[str]) -> tuple[object, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.document_events must be an array")
        return ()
    result: list[object] = []
    seen_event_handler_pairs: set[tuple[str, str]] = set()
    for index, item in enumerate(raw):
        label = f"contributes.document_events[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _DOCUMENT_EVENT_KEYS, label, errors)
        event = _require_str(item.get("event"), f"{label}.event", errors)
        if event is not None and event not in DOCUMENT_EVENTS:
            errors.append(
                f"{label}.event is not a recognized event: '{event}'"
                f" (valid: {sorted(DOCUMENT_EVENTS)})"
            )
        handler = _require_str(item.get("handler"), f"{label}.handler", errors)
        if event is not None and handler is not None:
            pair = (event, handler)
            if pair in seen_event_handler_pairs:
                errors.append(f"{label} duplicates event '{event}' with handler '{handler}'")
            else:
                seen_event_handler_pairs.add(pair)
        _require_str(item.get("title"), f"{label}.title", errors)
        desc = _require_str(item.get("description"), f"{label}.description", errors)
        if desc is not None and len(desc) > 400:
            errors.append(f"{label}.description must be at most 400 characters")
        if "conditions" in item:
            cond = item["conditions"]
            if not isinstance(cond, dict):
                errors.append(f"{label}.conditions must be an object")
            else:
                _check_unknown_keys(
                    cond, _DOCUMENT_EVENT_CONDITION_KEYS, f"{label}.conditions", errors
                )
        if "filter_extensions" in item:
            _validate_file_extensions_list(
                item["filter_extensions"], f"{label}.filter_extensions", errors
            )
        result.append(item)
    return tuple(result)


def _validate_status_bar(raw: object, errors: list[str]) -> tuple[StatusBarContribution, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.status_bar must be an array")
        return ()
    result: list[StatusBarContribution] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        label = f"contributes.status_bar[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _STATUS_BAR_KEYS, label, errors)
        cell_id = _require_str(item.get("id"), f"{label}.id", errors)
        if cell_id is not None:
            if cell_id in seen_ids:
                errors.append(f"{label}.id is a duplicate: '{cell_id}'")
            else:
                seen_ids.add(cell_id)
        cell_label = _require_str(item.get("label"), f"{label}.label", errors)
        handler = _require_str(item.get("handler"), f"{label}.handler", errors)
        tooltip = ""
        if "tooltip" in item:
            tt = _require_str(item.get("tooltip"), f"{label}.tooltip", errors)
            if tt is not None:
                tooltip = tt
        width = 10
        if "width" in item:
            w = item.get("width")
            if not isinstance(w, int) or not (1 <= w <= 40):
                errors.append(f"{label}.width must be an integer 1-40")
            else:
                width = w
        if cell_id is not None and cell_label is not None and handler is not None:
            result.append(
                StatusBarContribution(
                    id=cell_id,
                    label=cell_label,
                    handler=handler,
                    tooltip=tooltip,
                    width=width,
                )
            )
    return tuple(result)


def _validate_schedule(raw: object, errors: list[str]) -> tuple[ScheduleContribution, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.schedule must be an array")
        return ()
    result: list[ScheduleContribution] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        label = f"contributes.schedule[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _SCHEDULE_KEYS, label, errors)
        sched_id = _require_str(item.get("id"), f"{label}.id", errors)
        if sched_id is not None:
            if not sched_id:
                errors.append(f"{label}.id must not be empty")
                sched_id = None
            elif sched_id in seen_ids:
                errors.append(f"{label}.id is a duplicate: '{sched_id}'")
                sched_id = None
            else:
                seen_ids.add(sched_id)
        interval = item.get("interval_seconds")
        interval_ok = isinstance(interval, int) and not isinstance(interval, bool)
        if not interval_ok or not (60 <= int(interval) <= 86400):  # type: ignore[arg-type]
            errors.append(f"{label}.interval_seconds must be an integer 60-86400")
            interval_ok = False
        handler = _require_str(item.get("handler"), f"{label}.handler", errors)
        if handler is not None and not handler:
            errors.append(f"{label}.handler must not be empty")
            handler = None
        description = ""
        if "description" in item:
            desc = _require_str(item.get("description"), f"{label}.description", errors)
            if desc is not None:
                if len(desc) > 200:
                    errors.append(f"{label}.description must be at most 200 characters")
                else:
                    description = desc
        if sched_id is not None and interval_ok and handler is not None:
            result.append(
                ScheduleContribution(
                    id=sched_id,
                    interval_seconds=int(interval),  # type: ignore[arg-type]
                    handler=handler,
                    description=description,
                )
            )
    return tuple(result)


def _validate_file_types(raw: object, errors: list[str]) -> tuple[FileTypeContribution, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.file_types must be an array")
        return ()
    result: list[FileTypeContribution] = []
    for index, item in enumerate(raw):
        label = f"contributes.file_types[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _FILE_TYPE_KEYS, label, errors)
        raw_exts = item.get("extensions")
        extensions: list[str] = []
        if not isinstance(raw_exts, list) or not raw_exts:
            errors.append(f"{label}.extensions must be a non-empty array")
        else:
            for ei, ext in enumerate(raw_exts):
                elabel = f"{label}.extensions[{ei}]"
                if not isinstance(ext, str):
                    errors.append(f"{elabel} must be a string")
                elif not ext.startswith("."):
                    errors.append(f"{elabel} must start with '.' (got '{ext}')")
                elif ext != ext.lower():
                    errors.append(f"{elabel} must be lowercase (got '{ext}')")
                elif not (2 <= len(ext) <= 10):
                    errors.append(f"{elabel} must be 2-10 characters (got '{ext}')")
                else:
                    extensions.append(ext)
        handler = _require_str(item.get("handler"), f"{label}.handler", errors)
        if handler is not None and not handler:
            errors.append(f"{label}.handler must not be empty")
            handler = None
        description = ""
        if "description" in item:
            desc = _require_str(item.get("description"), f"{label}.description", errors)
            if desc is not None:
                if len(desc) > 200:
                    errors.append(f"{label}.description must be at most 200 characters")
                else:
                    description = desc
        if extensions and handler is not None:
            result.append(
                FileTypeContribution(
                    extensions=tuple(extensions),
                    handler=handler,
                    description=description,
                )
            )
    return tuple(result)


def _validate_snippet_params(
    raw: object, label: str, body: str, errors: list[str]
) -> tuple[SnippetParam, ...]:
    if not isinstance(raw, list):
        errors.append(f"{label} must be an array")
        return ()
    result: list[SnippetParam] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        plabel = f"{label}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{plabel} must be an object")
            continue
        _check_unknown_keys(item, _SNIPPET_PARAM_KEYS, plabel, errors)
        name = _require_str(item.get("name"), f"{plabel}.name", errors)
        plabel_label = _require_str(item.get("label"), f"{plabel}.label", errors)
        default = ""
        if "default" in item:
            d = _require_str(item.get("default"), f"{plabel}.default", errors)
            if d is not None:
                default = d
        if name is not None:
            if not name:
                errors.append(f"{plabel}.name must not be empty")
                name = None
            elif name in seen:
                errors.append(f"{plabel}.name is a duplicate: '{name}'")
                name = None
            elif ("{" + name + "}") not in body:
                errors.append(
                    f"{plabel}.name '{name}' does not appear as a {{{name}}} placeholder in body"
                )
                name = None
            else:
                seen.add(name)
        if name is not None and plabel_label is not None:
            result.append(SnippetParam(name=name, label=plabel_label, default=default))
    return tuple(result)


def _validate_snippet_gallery(raw: object, errors: list[str]) -> tuple[SnippetGalleryEntry, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.snippet_gallery must be an array")
        return ()
    result: list[SnippetGalleryEntry] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        label = f"contributes.snippet_gallery[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _SNIPPET_GALLERY_KEYS, label, errors)
        entry_id = _require_str(item.get("id"), f"{label}.id", errors)
        if entry_id is not None:
            if not (1 <= len(entry_id) <= 64):
                errors.append(f"{label}.id must be 1-64 characters")
                entry_id = None
            elif entry_id in seen_ids:
                errors.append(f"{label}.id is a duplicate: '{entry_id}'")
                entry_id = None
            else:
                seen_ids.add(entry_id)
        name = _require_str(item.get("name"), f"{label}.name", errors)
        if name is not None and not (1 <= len(name) <= 80):
            errors.append(f"{label}.name must be 1-80 characters")
            name = None
        body = _require_str(item.get("body"), f"{label}.body", errors)
        if body is not None and not (1 <= len(body) <= 4000):
            errors.append(f"{label}.body must be 1-4000 characters")
            body = None
        description = ""
        if "description" in item:
            desc = _require_str(item.get("description"), f"{label}.description", errors)
            if desc is not None:
                if len(desc) > 300:
                    errors.append(f"{label}.description must be at most 300 characters")
                else:
                    description = desc
        category = ""
        if "category" in item:
            cat = _require_str(item.get("category"), f"{label}.category", errors)
            if cat is not None:
                if len(cat) > 40:
                    errors.append(f"{label}.category must be at most 40 characters")
                else:
                    category = cat
        params: tuple[SnippetParam, ...] = ()
        if "params" in item:
            params = _validate_snippet_params(item["params"], f"{label}.params", body or "", errors)
        if entry_id is not None and name is not None and body is not None:
            result.append(
                SnippetGalleryEntry(
                    id=entry_id,
                    name=name,
                    body=body,
                    description=description,
                    category=category,
                    params=params,
                )
            )
    return tuple(result)


def _validate_requires(raw: object, errors: list[str]) -> tuple[RequiresDependency, ...]:
    if not isinstance(raw, list):
        errors.append("requires must be an array")
        return ()
    result: list[RequiresDependency] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        label = f"requires[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(item, _REQUIRES_KEYS, label, errors)
        dep_id = _require_str(item.get("id"), f"{label}.id", errors)
        if dep_id is not None:
            if not _ID_PATTERN.match(dep_id):
                errors.append(f"{label}.id must be a valid Quillin ID (got '{dep_id}')")
            elif dep_id in seen_ids:
                errors.append(f"{label}.id is a duplicate: '{dep_id}'")
            else:
                seen_ids.add(dep_id)
        min_version = ""
        if "min_version" in item:
            mv = _require_str(item.get("min_version"), f"{label}.min_version", errors)
            if mv is not None:
                if not _VERSION_PATTERN.match(mv):
                    errors.append(f"{label}.min_version must be MAJOR.MINOR.PATCH (got '{mv}')")
                else:
                    min_version = mv
        if dep_id is not None and _ID_PATTERN.match(dep_id):
            result.append(RequiresDependency(id=dep_id, min_version=min_version))
    return tuple(result)


def _validate_categories(raw: object, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(raw, list):
        errors.append("categories must be an array")
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            errors.append(f"categories[{index}] must be a string")
            continue
        if item not in QUILLIN_CATEGORIES:
            errors.append(
                f"categories[{index}] is not a known category: '{item}'"
                f" (valid: {sorted(QUILLIN_CATEGORIES)})"
            )
            continue
        if item in seen:
            errors.append(f"categories[{index}] is a duplicate: '{item}'")
            continue
        seen.add(item)
        result.append(item)
    return tuple(result)


def _validate_net_allowed_hosts(raw: object, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(raw, list):
        errors.append("net_allowed_hosts must be an array")
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            errors.append(f"net_allowed_hosts[{index}] must be a string")
            continue
        if not _HOSTNAME_PATTERN.match(item):
            errors.append(
                f"net_allowed_hosts[{index}] must be a hostname or *.hostname pattern"
                f" (got '{item}')"
            )
            continue
        if item in seen:
            errors.append(f"net_allowed_hosts[{index}] is a duplicate: '{item}'")
            continue
        seen.add(item)
        result.append(item)
    return tuple(result)


def _validate_contributes(
    raw: object, errors: list[str]
) -> tuple[Contributions, list[str], bool, bool]:
    """Return (contributions, contributed_command_ids, any_handler, has_document_events).

    any_handler is True when any command or abbreviation entry uses a Python
    handler (requires main + ui.command).
    has_document_events is True when document_events are declared (requires
    main + document.events capability).
    """

    if not isinstance(raw, dict):
        errors.append("contributes must be an object")
        return Contributions(), [], False, False
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

    abbreviations: tuple[object, ...] = ()
    if "abbreviations" in raw:
        abbreviations, any_abbrev_handler = _validate_abbreviations(raw["abbreviations"], errors)
        any_handler = any_handler or any_abbrev_handler

    smart_triggers: tuple[object, ...] = ()
    if "smart_triggers" in raw:
        smart_triggers = _validate_smart_triggers(raw["smart_triggers"], errors)

    preferences: tuple[object, ...] = ()
    if "preferences" in raw:
        preferences = _validate_preferences(raw["preferences"], errors)

    document_events: tuple[object, ...] = ()
    has_document_events = False
    if "document_events" in raw:
        document_events = _validate_document_events(raw["document_events"], errors)
        has_document_events = bool(document_events)

    status_bar: tuple[StatusBarContribution, ...] = ()
    if "status_bar" in raw:
        status_bar = _validate_status_bar(raw["status_bar"], errors)

    schedule: tuple[ScheduleContribution, ...] = ()
    if "schedule" in raw:
        schedule = _validate_schedule(raw["schedule"], errors)

    file_types: tuple[FileTypeContribution, ...] = ()
    if "file_types" in raw:
        file_types = _validate_file_types(raw["file_types"], errors)

    snippet_gallery: tuple[SnippetGalleryEntry, ...] = ()
    if "snippet_gallery" in raw:
        snippet_gallery = _validate_snippet_gallery(raw["snippet_gallery"], errors)

    contributions = Contributions(
        commands=tuple(commands),
        menus=menus,
        context_menu=context_menu,
        hotkeys=hotkeys,
        sound_pack=sound_pack,
        sound_events=sound_events,
        abbreviations=abbreviations,
        smart_triggers=smart_triggers,
        preferences=preferences,
        document_events=document_events,
        status_bar=status_bar,
        schedule=schedule,
        file_types=file_types,
        snippet_gallery=snippet_gallery,
    )
    return contributions, contributed_ids, any_handler, has_document_events


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
    for index, st in enumerate(contributions.smart_triggers):
        if isinstance(st, dict):
            command = st.get("command")
            if isinstance(command, str):
                _check(command, f"contributes.smart_triggers[{index}].command")


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

    if "categories" in raw:
        _validate_categories(raw.get("categories"), errors)

    if "requires" in raw:
        _validate_requires(raw.get("requires"), errors)

    net_allowed_hosts: tuple[str, ...] = ()
    if "net_allowed_hosts" in raw:
        net_allowed_hosts = _validate_net_allowed_hosts(raw.get("net_allowed_hosts"), errors)

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
    has_document_events = False
    if "contributes" in raw:
        contributions, contributed_ids, any_handler, has_document_events = _validate_contributes(
            raw.get("contributes"), errors
        )
        _validate_command_references(contributions, contributed_ids, builtin_command_ids, errors)

    # docs/quillins.md §15 rule 6: a handler command or abbreviation handler
    # requires an entry module and the ui.command capability.
    if any_handler:
        if main is None:
            errors.append("a command using run.handler requires a top-level 'main' module")
        if CAP_UI_COMMAND not in capabilities:
            errors.append("a command using run.handler requires the 'ui.command' capability")

    # A document_events contribution requires the document.events capability and main.
    if has_document_events:
        if CAP_DOCUMENT_EVENTS not in capabilities:
            errors.append("contributes.document_events requires the 'document.events' capability")
        if main is None:
            errors.append("contributes.document_events requires a top-level 'main' module")

    # A preferences contribution uses per-Quillin storage at runtime, so it should
    # declare at minimum settings.own.read (to display saved values) and ideally
    # settings.own.write (to save changes). Warn so a read-only preferences page
    # is still allowed, but a completely uncapabilited one is an authoring mistake.
    if contributions.preferences:
        has_settings_cap = (
            CAP_SETTINGS_OWN_READ in capabilities or CAP_SETTINGS_OWN_WRITE in capabilities
        )
        if not has_settings_cap:
            errors.append(
                "contributes.preferences should declare 'settings.own.read' and/or"
                " 'settings.own.write' capabilities to read and persist settings"
            )

    # Status bar cells require the ui.status capability.
    if contributions.status_bar:
        if CAP_UI_STATUS not in capabilities:
            errors.append("contributes.status_bar requires the 'ui.status' capability")
        if main is None:
            errors.append("contributes.status_bar requires a top-level 'main' module")

    # A schedule contribution runs a handler on a timer, so it requires the
    # schedule capability and an entry module to host the handler.
    if contributions.schedule:
        if CAP_SCHEDULE not in capabilities:
            errors.append("contributes.schedule requires the 'schedule' capability")
        if main is None:
            errors.append("contributes.schedule requires a top-level 'main' module")

    # File-type handlers are a specialized document.opened, so they reuse the
    # document.events capability and require an entry module.
    if contributions.file_types:
        if CAP_DOCUMENT_EVENTS not in capabilities:
            errors.append("contributes.file_types requires the 'document.events' capability")
        if main is None:
            errors.append("contributes.file_types requires a top-level 'main' module")

    # net_allowed_hosts is only meaningful when the net capability is declared.
    if net_allowed_hosts and CAP_NET not in capabilities:
        errors.append(
            "net_allowed_hosts is declared but the 'net' capability is not;"
            " either add 'net' to capabilities or remove net_allowed_hosts"
        )

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

    contributions, _ids, _handler, _doc_events = _validate_contributes(
        raw.get("contributes", {}), []
    )
    capabilities = _validate_capabilities(raw.get("capabilities", []), [])
    main_value = raw.get("main")
    main = main_value if isinstance(main_value, str) else None
    runtime_raw = raw.get("runtime", RUNTIME_PYTHON)
    runtime = (
        runtime_raw if isinstance(runtime_raw, str) and runtime_raw in RUNTIMES else RUNTIME_PYTHON
    )
    categories = _validate_categories(raw.get("categories", []), [])
    requires = _validate_requires(raw.get("requires", []), [])
    net_allowed_hosts = _validate_net_allowed_hosts(raw.get("net_allowed_hosts", []), [])

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
        categories=categories,
        requires=requires,
        net_allowed_hosts=net_allowed_hosts,
    )
