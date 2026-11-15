"""Forms and their entries in the Workbench: QAF first, then Gravity Forms (PRD 13a.5, 13b).

Every form plugin is found by its REST namespace in the site's index, never
guessed (section 12): QUILL Accessible Forms on ``qaf/v1`` (or ``baf/v1``,
its older name), Gravity Forms on ``gf/v2``. A site with neither has a Forms
node that says so. What each reaches is what its API allows (13b.2):

- **QAF:** forms, entries (``qaf/v1/entries?form_id=``) with their status and,
  for a held one, QAF's reason; and Spam and Not Spam through QAF's own
  ``POST qaf/v1/entries/{id}/spam`` and ``.../not-spam``, which tell its spam
  providers and release a held entry's notifications
  (:mod:`quill.core.wordpress.workbench_qaf_spam`).
- **Gravity Forms:** forms (``gf/v2/forms``), entries
  (``gf/v2/entries?form_ids[]=``) with their status (``active``, ``spam``,
  ``trash``), and Spam and Not Spam, sent as the whole entry with the status
  changed (``PUT gf/v2/entries/{id}``), because Gravity Forms replaces an
  entry rather than merging it.

Entries are personal data: they are read only when a Forms or Held as Spam
node is opened, never logged, and leave only to a file the person chooses.
Wx-free.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.core.forms import qaf_site
from quill.core.wordpress import workbench_gravity_search as gravity_search
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_listing import pages_for
from quill.core.wordpress.workbench_qaf_spam import held_reason, mark_entry
from quill.core.wordpress.workbench_rows import WbRow

if TYPE_CHECKING:
    from quill.core.wordpress.workbench_load import SiteContext

__all__ = [
    "GRAVITY_NAMESPACE",
    "GRAVITY_FIELD_TYPES",
    "GravityFieldTypeChange",
    "PLUGIN_NAMES",
    "form_plugins",
    "gravity_replacement_problems",
    "plan_gravity_field_type_change",
    "load_forms",
    "set_entry_spam",
]

GRAVITY_NAMESPACE = "gf/v2"
PLUGIN_NAMES = {"qaf": "QUILL Accessible Forms", "gravity": "Gravity Forms"}
#: The Gravity Forms controls Change a Field Type converts between. Every other family
#: (name, address, list, product, upload, poll, quiz and the rest) is never offered and is
#: sent back untouched. A family joins only with a gf/v2 form recorded from a real site
#: that shows its inputs and settings, and a test converting it (complete.md WP-C).
GRAVITY_FIELD_TYPES = {
    "text": "Single line text",
    "textarea": "Paragraph text",
    "email": "Email address",
    "number": "Number",
    "select": "Drop-down list",
    "radio": "Radio buttons",
    "checkbox": "Checkboxes",
}
_GRAVITY_CHOICE_TYPES = frozenset({"select", "radio", "checkbox"})
_GRAVITY_SINGLE_CHOICE_TYPES = frozenset({"select", "radio"})
_GRAVITY_CHOICE_ONLY = (
    "choices",
    "inputs",
    "enableChoiceValue",
    "enableOtherChoice",
    "enableSelectAll",
    "enablePrice",
    "randomize",
)
_MAX_ENTRIES = 300


@dataclass(frozen=True, slots=True)
class GravityFieldTypeChange:
    """An immutable preview of a type change inside a complete Gravity form."""

    form: dict[str, Any]
    field_id: str
    field_label: str
    old_type: str
    new_type: str
    kept: tuple[str, ...]
    adjusted: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def summary(self) -> str:
        old = GRAVITY_FIELD_TYPES.get(self.old_type, self.old_type)
        new = GRAVITY_FIELD_TYPES.get(self.new_type, self.new_type)
        return f"Change {self.field_label} (field {self.field_id}) from {old} to {new}."

    def review_lines(self) -> list[str]:
        lines = ["Kept: " + (", ".join(self.kept) if self.kept else "the field id") + "."]
        if self.adjusted:
            lines.append("Adjusted: " + "; ".join(self.adjusted) + ".")
        if self.removed:
            lines.append("Cannot carry over: " + ", ".join(self.removed) + ".")
        lines.append("QUILL will send the complete form, preserving its other fields and settings.")
        return lines


def plan_gravity_field_type_change(
    form: Mapping[str, Any], field_id: str, new_type: str
) -> GravityFieldTypeChange:
    """Prepare a common Gravity Forms field conversion without mutating *form*."""
    if new_type not in GRAVITY_FIELD_TYPES:
        raise ValueError(f"{new_type!r} is not a supported Gravity Forms field type.")
    source_fields = form.get("fields")
    if not isinstance(source_fields, list):
        raise ValueError("Gravity Forms did not return a fields list for this form.")
    index = next(
        (
            number
            for number, field in enumerate(source_fields)
            if isinstance(field, dict) and str(field.get("id", "")) == str(field_id)
        ),
        None,
    )
    if index is None:
        raise ValueError(f"Gravity Forms field {field_id} is no longer in this form.")

    original = source_fields[index]
    old_type = str(original.get("type", "text"))
    if old_type not in GRAVITY_FIELD_TYPES:
        raise ValueError(
            f"{original.get('label') or field_id} uses {old_type}, which QUILL does not convert."
        )
    converted_form = deepcopy(dict(form))
    field = converted_form["fields"][index]
    adjusted: list[str] = []
    removed: list[str] = []
    if old_type != new_type:
        field["type"] = new_type
        if new_type in _GRAVITY_CHOICE_TYPES:
            existing_choices = field.get("choices")
            choices = (
                [deepcopy(choice) for choice in existing_choices if isinstance(choice, dict)]
                if isinstance(existing_choices, list)
                else []
            )
            if not choices:
                default = field.get("defaultValue")
                label = str(default).strip() if default not in (None, "") else "Choice 1"
                choices = [
                    {"text": label, "value": str(default or "choice-1"), "isSelected": False}
                ]
                adjusted.append("added a starter choice so the new control can be filled in")
            field["choices"] = choices
            if new_type == "checkbox":
                old_inputs = field.get("inputs")
                old_inputs = old_inputs if isinstance(old_inputs, list) else []
                inputs: list[dict[str, Any]] = []
                for number, choice in enumerate(choices, start=1):
                    old_input = old_inputs[number - 1] if number <= len(old_inputs) else {}
                    item = deepcopy(old_input) if isinstance(old_input, dict) else {}
                    item["id"] = f"{field_id}.{number}"
                    item["label"] = str(
                        choice.get("text") or choice.get("value") or f"Choice {number}"
                    )
                    inputs.append(item)
                field["inputs"] = inputs
            else:
                if "inputs" in field:
                    field.pop("inputs")
                    removed.append("checkbox input records")
            if new_type in _GRAVITY_SINGLE_CHOICE_TYPES:
                selected = [choice for choice in choices if choice.get("isSelected")]
                if len(selected) > 1:
                    keep = selected[0]
                    for choice in choices:
                        choice["isSelected"] = choice is keep
                    adjusted.append(
                        "kept only the first selected default for a single-choice control"
                    )
        else:
            for key in _GRAVITY_CHOICE_ONLY:
                if key in field:
                    field.pop(key)
                    removed.append(key.replace("_", " "))

        default = field.get("defaultValue")
        if isinstance(default, list) and new_type in _GRAVITY_SINGLE_CHOICE_TYPES and default:
            field["defaultValue"] = default[0]
            adjusted.append("kept the first selected default for a single-choice control")
        elif isinstance(default, list) and new_type not in _GRAVITY_CHOICE_TYPES:
            field["defaultValue"] = ", ".join(str(value) for value in default)
            adjusted.append("kept selected values as comma-separated text")
        if (
            old_type == "checkbox"
            and new_type in _GRAVITY_SINGLE_CHOICE_TYPES
            and isinstance(default, str)
        ):
            values = [part.strip() for part in default.split(",") if part.strip()]
            if len(values) > 1:
                field["defaultValue"] = values[0]
                adjusted.append("kept the first selected default for a single-choice control")

    shared = (
        "id",
        "label",
        "description",
        "adminLabel",
        "isRequired",
        "size",
        "cssClass",
        "placeholder",
        "defaultValue",
        "visibility",
        "conditionalLogic",
        "noDuplicates",
        "allowsPrepopulate",
        "inputName",
    )
    kept_fields = [key for key in shared if key in field]
    if new_type in _GRAVITY_CHOICE_TYPES and field.get("choices"):
        kept_fields.append(f"{len(field['choices'])} choices")
    if new_type == "checkbox" and field.get("inputs"):
        kept_fields.append(f"{len(field['inputs'])} checkbox option settings")
    kept = tuple(kept_fields)
    return GravityFieldTypeChange(
        converted_form,
        str(field_id),
        str(original.get("label") or f"Field {field_id}"),
        old_type,
        new_type,
        kept,
        tuple(adjusted),
        tuple(removed),
    )


def gravity_replacement_problems(
    plan: GravityFieldTypeChange, stored: Mapping[str, Any] | None
) -> list[str]:
    """What the form read back after a conversion lacks, as sentences ([] when it matches).

    Gravity Forms replaces the whole form on ``PUT``, so the check reads it again and
    compares field by field: the changed field must have its new type, and every
    other field must come back as it went.
    """
    if not isinstance(stored, Mapping) or not isinstance(stored.get("fields"), list):
        return ["Gravity Forms did not return the form's fields after the change."]
    sent = {str(f.get("id", "")): f for f in plan.form["fields"] if isinstance(f, dict)}
    back = {str(f.get("id", "")): f for f in stored["fields"] if isinstance(f, dict)}
    problems: list[str] = []
    changed = back.get(plan.field_id)
    if changed is None:
        problems.append(f"Field {plan.field_id} is missing from the saved form.")
    elif str(changed.get("type", "")) != plan.new_type:
        problems.append(
            f"Field {plan.field_id} reads back as {changed.get('type') or 'no type'}, "
            f"not {plan.new_type}."
        )
    missing = [key for key in sent if key not in back]
    if missing:
        problems.append("Fields missing after the change: " + ", ".join(missing) + ".")
    for key, field in sent.items():
        if key == plan.field_id or key not in back:
            continue
        if str(back[key].get("type", "")) != str(field.get("type", "")):
            problems.append(f"Field {key} changed type, which QUILL did not ask for.")
    return problems


def form_plugins(ctx: SiteContext) -> tuple[str, ...]:
    """The form plugins this site's REST index shows, QAF first."""
    info = ctx.info
    found: list[str] = []
    if info is not None:
        if any(info.supports(ns) for ns in qaf_site.NAMESPACES):
            found.append("qaf")
        if info.supports(GRAVITY_NAMESPACE):
            found.append("gravity")
    elif qaf_site.supports_qaf(ctx.api):
        found.append("qaf")
    return tuple(found)


def _qaf_ns(ctx: SiteContext) -> str:
    info = ctx.info
    if info is not None:
        return next((ns for ns in qaf_site.NAMESPACES if info.supports(ns)), qaf_site.NAMESPACE)
    return qaf_site.site_namespace(ctx.api) or qaf_site.NAMESPACE


def _answers_sentence(answers: Mapping[str, Any], limit: int = 3) -> str:
    said = []
    for key, value in list(answers.items())[:limit]:
        text = value if isinstance(value, str) else json.dumps(value)
        said.append(f"{key}: {' '.join(str(text).split())[:80]}")
    return "; ".join(said)


def _entry_row(
    ctx: SiteContext,
    plugin: str,
    form_title: str,
    entry_id: int,
    status: str,
    when: str,
    answers: Mapping[str, Any],
    route: str,
    raw: Mapping[str, Any],
) -> WbRow:
    word = {"active": "Received", "spam": "Held as spam", "trash": "Trash"}.get(status, status)
    held = " held as spam" if status == "spam" else ""
    detail = f"{form_title}, {PLUGIN_NAMES[plugin]}, {ctx.name},{held} {friendly_date(when)}."
    if status == "spam" and plugin == "qaf" and held_reason(raw):
        detail += " " + held_reason(raw)
    summary = _answers_sentence(answers)
    return WbRow(
        kind="form_entry",
        site=ctx.name,
        key=str(entry_id),
        cells={
            "form": form_title,
            "plugin": PLUGIN_NAMES[plugin],
            "status": word,
            "when": friendly_date(when) if when else "",
            "what": f"{form_title} entry",
            "from": "",
            "site": ctx.name,
        },
        detail=f"{detail} {summary}".strip(),
        route=route,
        status=status,
        subkind=plugin,
        modified_gmt=when,
        raw=dict(raw),
    )


def _qaf_rows(ctx: SiteContext, which: str) -> list[WbRow]:
    namespace = _qaf_ns(ctx)
    forms = [qaf_site.form_from_payload(r) for r in ctx.api.iter_collection(f"{namespace}/forms")]
    if which == "all":
        return [
            WbRow(
                kind="form",
                site=ctx.name,
                key=str(form.id),
                cells={
                    "form": form.title,
                    "plugin": PLUGIN_NAMES["qaf"],
                    "entries": str(form.entry_count),
                    "status": form.status,
                },
                detail=f"{form.title}, {form.entry_count} responses, {form.status}.",
                route=f"{namespace}/forms/{form.id}",
                status=form.status,
                subkind="qaf",
                raw={"id": form.id, "title": form.title, "status": form.status},
            )
            for form in forms
        ]
    status = "spam" if which == "spam" else "active"
    rows: list[WbRow] = []
    for form in forms:
        params = {"form_id": form.id, "status": status, "orderby": "created_at", "order": "DESC"}
        for raw in ctx.api.iter_collection(f"{namespace}/entries", params, max_pages=3):
            entry = qaf_site.response_from_payload(raw)
            rows.append(
                _entry_row(
                    ctx,
                    "qaf",
                    form.title,
                    entry.id,
                    entry.status,
                    entry.created_at,
                    entry.answers,
                    f"{namespace}/entries/{entry.id}",
                    raw,
                )
            )
    return rows[:_MAX_ENTRIES]


def _gravity_rows(ctx: SiteContext, which: str) -> list[WbRow]:
    raw_forms = ctx.api.get(f"{GRAVITY_NAMESPACE}/forms")
    forms = list(raw_forms.values()) if isinstance(raw_forms, dict) else raw_forms
    forms = [f for f in forms or [] if isinstance(f, dict)]
    titles = {str(f.get("id", "")): str(f.get("title", "") or "Form") for f in forms}
    counts = {str(f.get("id", "")): str(f.get("entries", "") or "") for f in forms}
    if which == "all":
        return [
            WbRow(
                kind="gravity_form",
                site=ctx.name,
                key=form_id,
                cells={
                    "form": title,
                    "plugin": PLUGIN_NAMES["gravity"],
                    "entries": counts.get(form_id, ""),
                    "status": "active",
                },
                detail=f"{title}, a Gravity Forms form.",
                route=f"{GRAVITY_NAMESPACE}/forms/{form_id}",
                subkind="gravity",
                raw={"id": form_id, "title": title},
            )
            for form_id, title in titles.items()
        ]
    status = "spam" if which == "spam" else "active"
    # The Filter Builder's conditions go to the site (workbench_gravity_search).
    scope = gravity_search.current_scope()
    if scope is not None and scope.form:
        titles = {i: t for i, t in titles.items() if scope.form.casefold() in t.casefold()}
    if not titles:
        return []
    searching = scope is not None and scope.active
    entries = gravity_search.read_entries(
        ctx.api,
        f"{GRAVITY_NAMESPACE}/entries",
        list(titles),
        status,
        scope,
        pages_for(3) if searching else 1,
    )
    rows = []
    for entry in entries:
        answers = {k: v for k, v in entry.items() if k[:1].isdigit() and v not in ("", None)}
        rows.append(
            _entry_row(
                ctx,
                "gravity",
                titles.get(str(entry.get("form_id", "")), "Form"),
                int(entry.get("id", 0) or 0),
                str(entry.get("status", "") or "active"),
                str(entry.get("date_created", "") or ""),
                answers,
                f"{GRAVITY_NAMESPACE}/entries/{entry.get('id', 0)}",
                entry,
            )
        )
    return rows if searching else rows[:_MAX_ENTRIES]


def load_forms(ctx: SiteContext, which: str) -> list[WbRow]:
    """``all`` the forms, their ``entries``, or the entries held as ``spam``."""
    plugins = form_plugins(ctx)
    if not plugins:
        raise WordPressApiError(
            f"{ctx.name} has no forms plugin QUILL can read. QUILL Accessible Forms and "
            "Gravity Forms are found by their REST routes; this site lists neither."
        )
    rows: list[WbRow] = []
    if "qaf" in plugins:
        rows += _qaf_rows(ctx, which)
    if "gravity" in plugins:
        rows += _gravity_rows(ctx, which)
    if which != "all":
        rows.sort(key=lambda row: row.modified_gmt, reverse=True)
    return rows


def set_entry_spam(ctx: SiteContext, rows: Sequence[WbRow], spam: bool) -> list[str]:
    """Mark form entries as spam, or not; returns a sentence for each that failed."""
    failed: list[str] = []
    for row in rows:
        try:
            if row.subkind == "gravity":
                body = {**row.raw, "status": "spam" if spam else "active"}
                ctx.api.request("PUT", row.route, json_body=body)
            else:
                mark_entry(ctx.api, row, spam)
        except WordPressApiError as exc:
            failed.append(f"{row.title}: {exc.plain}")
    return failed
