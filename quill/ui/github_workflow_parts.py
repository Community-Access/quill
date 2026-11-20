"""The forms inside the workflow editor: a trigger, an input, a step, permissions (PRD 22.1).

Each pair of functions here is one form's fields (``*_fields``) and how its
answers become YAML values (``*_from``), so the forms are tested without a
window. The windows are :mod:`quill.ui.github_workflow_editor_dialog`'s; the
form itself is :class:`quill.ui.github_authoring_form.FieldsDialog`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.actions_yaml import scalar, scalar_text
from quill.core.github.workflow_authoring import (
    EVENT_WORDS,
    FILTER_KEYS,
    INPUT_TYPES,
    PERMISSION_LEVELS,
    PERMISSION_SCOPES,
    pairs_text,
    parse_pairs,
    schedule_crons,
)
from quill.ui.github_authoring_form import Field

__all__ = [
    "EVENT_CHOICES",
    "FILTER_LABELS",
    "PERMISSION_MODES",
    "filters_fields",
    "filters_from",
    "input_fields",
    "input_from",
    "inputs_settings",
    "permissions_fields",
    "permissions_from",
    "schedule_fields",
    "schedule_from",
    "split_list",
    "step_fields",
    "step_from",
]

#: Add Trigger's list: (row, event); "" asks for the event's name.
EVENT_CHOICES: tuple[tuple[str, str], ...] = (
    *((f"{words} ({event})", event) for event, words in EVENT_WORDS.items()),
    ("Another event, by its name...", ""),
)

FILTER_LABELS: dict[str, str] = {
    "branches": "Branches:",
    "branches-ignore": "Branches to ignore:",
    "tags": "Tags:",
    "tags-ignore": "Tags to ignore:",
    "paths": "Paths:",
    "paths-ignore": "Paths to ignore:",
    "types": "Activity types:",
}

#: The permissions form's first choice, and what each writes.
PERMISSION_MODES: tuple[tuple[str, Any], ...] = (
    ("Not set: the repository's default for GITHUB_TOKEN", None),
    ("Read everything (read-all)", "read-all"),
    ("Write everything (write-all)", "write-all"),
    ("None at all", {}),
    ("Chosen scope by scope, below", "scopes"),
)
_NOT_LISTED = "not listed"


def split_list(text: str) -> list[str]:
    """ "main, release/*" or one per line, as a list; blanks dropped."""
    return [part.strip() for part in text.replace("\n", ",").split(",") if part.strip()]


def _listed(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return "" if value is None else str(value)


# -- a push, pull request or other event's filters --------------------------------------


def filters_fields(event: str, settings: Any) -> list[Field]:
    current = settings if isinstance(settings, dict) else {}
    keys = FILTER_KEYS if event in ("push", "pull_request", "pull_request_target") else ("types",)
    return [
        Field(
            key,
            FILTER_LABELS[key],
            _listed(current.get(key)),
            f"{FILTER_LABELS[key].rstrip(':')} for {event}, separated by commas; empty for any. "
            "Patterns such as release/** and !docs/** work as on GitHub.",
        )
        for key in keys
    ]


def filters_from(values: Mapping[str, Any], settings: Any) -> Any:
    """The trigger's settings; keys the form does not show are kept; empty is ``None``."""
    kept = dict(settings) if isinstance(settings, dict) else {}
    for key in FILTER_KEYS:
        if key not in values:
            continue
        listed = split_list(str(values[key]))
        if listed:
            kept[key] = listed
        else:
            kept.pop(key, None)
    return kept or None


# -- a schedule ---------------------------------------------------------------------------


def schedule_fields(settings: Any) -> list[Field]:
    return [
        Field(
            "crons",
            "Times, one cron line each:",
            "\n".join(schedule_crons(settings)),
            "Five fields: minute, hour, day of month, month, day of week, in UTC. "
            "30 5 * * 1 is 05:30 every Monday.",
            "multiline",
        )
    ]


def schedule_from(values: Mapping[str, Any]) -> list[dict[str, str]]:
    lines = str(values.get("crons", "")).replace("\r\n", "\n").split("\n")
    return [{"cron": line.strip()} for line in lines if line.strip()]


# -- a workflow_dispatch input --------------------------------------------------------------


def input_fields(name: str, spec: Mapping[str, Any]) -> list[Field]:
    return [
        Field("name", "Input name:", name, "What the workflow calls it: inputs.<name>."),
        Field("description", "Description:", spec.get("description", ""), "Shown beside it."),
        Field(
            "type",
            "Type:",
            str(spec.get("type", "string")),
            "String, yes or no (boolean), a choice, a number, or an environment.",
            "choice",
            INPUT_TYPES,
        ),
        Field(
            "required", "Required", spec.get("required") is True, "Must be given to run.", "check"
        ),
        Field("default", "Default:", scalar_text(spec.get("default")), "Its value when not given."),
        Field(
            "options",
            "Options, for a choice:",
            _listed(spec.get("options")),
            "The choices, separated by commas.",
        ),
    ]


def input_from(values: Mapping[str, Any], spec: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    kept = dict(spec)
    for key in ("description", "default"):
        text = str(values.get(key, "")).strip()
        if text:
            kept[key] = scalar(text) if key == "default" else text
        else:
            kept.pop(key, None)
    kept["type"] = str(values.get("type") or "string")
    if values.get("required"):
        kept["required"] = True
    else:
        kept.pop("required", None)
    options = split_list(str(values.get("options", "")))
    if kept["type"] == "choice":
        kept["options"] = options
    else:
        kept.pop("options", None)
    return str(values.get("name", "")).strip(), kept


def inputs_settings(settings: Any, inputs: Mapping[str, dict[str, Any]]) -> Any:
    """A dispatch trigger's settings with *inputs*; no inputs and nothing else is ``None``."""
    kept = dict(settings) if isinstance(settings, dict) else {}
    if inputs:
        kept["inputs"] = dict(inputs)
    else:
        kept.pop("inputs", None)
    return kept or None


# -- a step ------------------------------------------------------------------------------


def step_fields(step: Mapping[str, Any]) -> list[Field]:
    return [
        Field("name", "Step name:", step.get("name", ""), "What the log calls this step."),
        Field(
            "uses",
            "Action it uses:",
            step.get("uses", ""),
            "owner/action@version, such as actions/checkout@v4. Leave empty to run commands.",
        ),
        Field(
            "run",
            "Commands it runs:",
            step.get("run", ""),
            "Shell commands, one per line. Leave empty when it uses an action.",
            "multiline",
        ),
        Field(
            "with",
            "Action inputs (with), one name: value per line:",
            pairs_text(step.get("with")),
            "The action's inputs, such as fetch-depth: 0.",
            "multiline",
        ),
        Field(
            "env",
            "Environment variables, one NAME: value per line:",
            pairs_text(step.get("env")),
            "Variables for this step only.",
            "multiline",
        ),
        Field(
            "if",
            "Only if:",
            step.get("if", ""),
            "A condition, such as github.ref == 'refs/heads/main'.",
        ),
        Field("id", "Step id:", step.get("id", ""), "Lets later steps read its outputs."),
        Field(
            "working-directory",
            "Working directory:",
            step.get("working-directory", ""),
            "Where its commands run; empty for the repository's root.",
        ),
        Field(
            "shell",
            "Shell:",
            step.get("shell", ""),
            "bash, pwsh, python and so on; empty for the default.",
        ),
    ]


def step_from(values: Mapping[str, Any], step: Mapping[str, Any]) -> dict[str, Any]:
    """The step with the form's answers; keys it does not show are kept, in order."""
    kept = dict(step)
    for key in ("name", "uses", "run", "if", "id", "working-directory", "shell"):
        text = str(values.get(key, ""))
        text = text if key == "run" else text.strip()
        if text.strip():
            kept[key] = text.replace("\r\n", "\n")
        else:
            kept.pop(key, None)
    for key in ("with", "env"):
        pairs = parse_pairs(str(values.get(key, "")))
        if pairs:
            kept[key] = pairs
        else:
            kept.pop(key, None)
    return kept


# -- permissions ---------------------------------------------------------------------------


def permissions_fields(value: Any) -> list[Field]:
    if value is None:
        mode = PERMISSION_MODES[0][0]
    elif value in ("read-all", "write-all"):
        mode = PERMISSION_MODES[1 if value == "read-all" else 2][0]
    elif value == {}:
        mode = PERMISSION_MODES[3][0]
    else:
        mode = PERMISSION_MODES[4][0]
    levels = value if isinstance(value, dict) else {}
    fields = [
        Field(
            "mode",
            "Permissions:",
            mode,
            "What GITHUB_TOKEN may do. Choose scope by scope to give each only what it needs.",
            "choice",
            tuple(label for label, _v in PERMISSION_MODES),
        )
    ]
    for scope in PERMISSION_SCOPES:
        fields.append(
            Field(
                scope,
                f"{scope}:",
                str(levels.get(scope, _NOT_LISTED)),
                f"The {scope} permission. Not listed means none when any scope is chosen.",
                "choice",
                (_NOT_LISTED, *PERMISSION_LEVELS),
            )
        )
    return fields


def permissions_from(values: Mapping[str, Any]) -> Any:
    """``None`` (not set), ``"read-all"``, ``"write-all"``, ``{}`` or scopes with levels."""
    chosen = dict(PERMISSION_MODES).get(str(values.get("mode", "")))
    if chosen != "scopes":
        return chosen
    return {
        scope: str(values[scope])
        for scope in PERMISSION_SCOPES
        if str(values.get(scope, _NOT_LISTED)) != _NOT_LISTED
    }
