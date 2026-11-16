"""GitHub issue forms, to and from the QAF model (GitHub PRD 21.4, GH-R-072).

A form written in QUILL's form language (BFL, read into the QAF model) can be
saved as a GitHub issue form, and a GitHub issue form can be opened as a form
document. Both directions go through the model, beside the SurveyJS and
XLSForm interop:

- :func:`import_github_issue_form`: an issue form's YAML as a model. GitHub's
  five elements map to model fields (markdown to an HTML block, input to text,
  textarea to long text, dropdown to a drop-down or multiple-choice list,
  checkboxes to check boxes). Everything GitHub has that the model does not --
  the issue title prefix, labels, assignees, projects, type, an element's
  ``render``, an id the model cannot spell, per-option required check boxes,
  an explicit ``required: false`` -- is kept under ``extensions.github``
  (BFL's ``@extensions``), so saving back gives it back.
- :func:`export_github_draft` / :func:`export_github_issue_form`: a model as
  an issue form, with one sentence for each thing GitHub's forms cannot hold
  (other field types, conditions, scores, calculations, payments, validation
  limits, pages, other languages). Nothing is left out without being said.

``quill.core.github.template_convert.qaf_to_draft`` is this module's export,
so a SurveyJS or XLSForm file and a BFL document become issue forms the same
way. No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.forms import model as M
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_common import ImportResult, clean, safe_id

__all__ = [
    "GITHUB_EXTENSION",
    "export_github_draft",
    "export_github_issue_form",
    "import_github_issue_form",
]

#: The key under ``extensions`` that holds what only GitHub has.
GITHUB_EXTENSION = "github"

#: Model field types written as a one-line ``input``.
_INPUT_TYPES = frozenset(
    "text number email phone website date time datetime daterange name address currency "
    "post_title user_login user_email".split()
)
#: Model field types written as a ``textarea``.
_LONG_TYPES = frozenset({"textarea", "rich_text", "post_content", "post_excerpt"})
#: Top-level keys the model holds itself; every other one is kept in the extension.
_TOP_HELD = {"name", "description", "body"}
#: Element attributes the model holds itself.
_ATTRS_HELD = {"label", "description", "placeholder", "value", "options", "multiple", "default"}


def _text(value: Any) -> str:
    if isinstance(value, Mapping):  # translated text: take the first language
        value = next(iter(value.values()), "")
    return "" if value is None else str(value)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _option_label(option: Any) -> str:
    return _text(option.get("label")) if isinstance(option, Mapping) else _text(option)


# -- import ---------------------------------------------------------------------------------------


def _import_field(raw: dict[str, Any], taken: set[str], report: list[str]) -> M.Item | None:
    kind = str(raw.get("type") or "")
    attrs = _mapping(raw.get("attributes"))
    validations = _mapping(raw.get("validations"))
    required = bool(validations.get("required"))
    label = _text(attrs.get("label")).strip()
    github_id = raw.get("id")
    keep: dict[str, Any] = {}
    item: dict[str, Any]
    if kind == "markdown":
        ident = safe_id(github_id or "text", taken)
        item = {"id": ident, "type": "html", "props": {"html": _text(attrs.get("value"))}}
    elif kind in ("input", "textarea"):
        ident = safe_id(github_id or label or "question", taken)
        item = {
            "id": ident,
            "type": "text" if kind == "input" else "textarea",
            "label": label,
            "help": _text(attrs.get("description")),
            "placeholder": _text(attrs.get("placeholder")),
            "default": _text(attrs.get("value")) or None,
        }
    elif kind == "dropdown":
        ident = safe_id(github_id or label or "choice", taken)
        options = [_option_label(o) for o in attrs.get("options") or []]
        choices = [
            {"value": M.slug(o) or f"option_{n}", "label": o} for n, o in enumerate(options, 1)
        ]
        item = {
            "id": ident,
            "type": "multiselect" if attrs.get("multiple") else "select",
            "label": label,
            "help": _text(attrs.get("description")),
            "choices": choices,
        }
        default = attrs.get("default")
        if (
            isinstance(default, int)
            and not isinstance(default, bool)
            and 0 <= default < len(choices)
        ):
            item["default"] = choices[default]["value"]
    elif kind == "checkboxes":
        ident = safe_id(github_id or label or "check", taken)
        options = list(attrs.get("options") or [])
        labels = [_option_label(o) for o in options]
        musts = [bool(isinstance(o, Mapping) and o.get("required")) for o in options]
        item = {
            "id": ident,
            "type": "checkbox",
            "label": label,
            "help": _text(attrs.get("description")),
            "choices": [
                {"value": M.slug(o) or f"option_{n}", "label": o} for n, o in enumerate(labels, 1)
            ],
        }
        required = any(musts)
        if required and not all(musts):
            keep["required_options"] = musts
            names = ", ".join(lab for lab, must in zip(labels, musts, strict=True) if must)
            report.append(
                f"{label}: on GitHub only {names} must be checked. The form marks the whole "
                "group required; saving back to GitHub keeps GitHub's rule."
            )
    else:
        report.append(
            f"Field {github_id or label or kind!r}: GitHub has no {kind!r} element; left out."
        )
        return None
    if required and kind != "markdown":
        item["required"] = True
    # What the model cannot hold, kept so a save gives it back.
    if github_id is None and kind != "markdown":
        keep["id"] = None
    elif github_id is not None and str(github_id) != ident:
        keep["id"] = github_id
    if isinstance(raw.get("validations"), Mapping) and dict(raw["validations"]) != (
        {"required": True} if required and kind != "checkboxes" else {}
    ):
        keep["validations"] = dict(raw["validations"])
    extra_attrs = {k: v for k, v in attrs.items() if k not in _ATTRS_HELD}
    if kind == "markdown":
        extra_attrs.pop("value", None)
    if extra_attrs:
        keep["attributes"] = extra_attrs
    extra_keys = {
        k: v for k, v in raw.items() if k not in ("type", "id", "attributes", "validations")
    }
    if extra_keys:
        keep["keys"] = extra_keys
    out = clean(item)
    if keep:
        out["__github"] = keep
    return out


def import_github_issue_form(text: str, *, kind: str = "issue_form") -> ImportResult:
    """An issue (or discussion) form's YAML as a QAF model, with the import report.

    Raises :class:`~quill.core.forms.errors.FormImportError` when the YAML is
    not a form at all.
    """
    from quill.core.github.template_builder import TemplateDraftError, load_draft

    try:
        draft = load_draft(text, kind=kind)
    except TemplateDraftError as exc:
        raise FormImportError(str(exc)) from exc
    report: list[str] = []
    taken: set[str] = set()
    items: list[M.Item] = []
    fields_kept: dict[str, Any] = {}
    for raw in draft.fields:
        item = _import_field(raw, taken, report)
        if item is None:
            continue
        kept = item.pop("__github", None)
        if kept:
            fields_kept[item["id"]] = kept
        items.append(item)
    model: M.Model = {"version": M.MODEL_VERSION, "title": _text(draft.top.get("name"))}
    if draft.top.get("description"):
        model["description"] = _text(draft.top["description"])
    model["pages"] = [{"id": "page_1", "items": items}]
    form_kept = {k: v for k, v in draft.top.items() if k not in _TOP_HELD}
    extension: dict[str, Any] = {}
    if form_kept:
        extension["form"] = form_kept
    if fields_kept:
        extension["fields"] = fields_kept
    if kind != "issue_form":
        extension["kind"] = kind
    if extension:
        model["extensions"] = {GITHUB_EXTENSION: extension}
    if form_kept:
        report.append(
            "Kept for saving back to GitHub: " + ", ".join(sorted(str(k) for k in form_kept)) + "."
        )
    return ImportResult(model, report)


# -- export ---------------------------------------------------------------------------------------


def _kept(model: Mapping[str, Any]) -> dict[str, Any]:
    extensions = model.get("extensions")
    found = extensions.get(GITHUB_EXTENSION) if isinstance(extensions, Mapping) else None
    return dict(found) if isinstance(found, Mapping) else {}


def _apply_kept(made: dict[str, Any], kept: Mapping[str, Any]) -> None:
    """Give an element back what :func:`import_github_issue_form` kept for it."""
    if "id" in kept:
        if kept["id"] is None:
            made.pop("id", None)
        else:
            made["id"] = kept["id"]
    if isinstance(kept.get("validations"), Mapping):
        made["validations"] = dict(kept["validations"])
    if isinstance(kept.get("attributes"), Mapping):
        made.setdefault("attributes", {}).update(kept["attributes"])
    if isinstance(kept.get("keys"), Mapping):
        made.update(kept["keys"])
    musts = kept.get("required_options")
    options = made.get("attributes", {}).get("options")
    if made.get("type") == "checkboxes" and isinstance(musts, list) and isinstance(options, list):
        if len(musts) == len(options):
            for option, must in zip(options, musts, strict=True):
                if isinstance(option, dict):
                    option.pop("required", None)
                    if must:
                        option["required"] = True


def _element(item: Mapping[str, Any], taken: list[str]) -> dict[str, Any] | None:
    from quill.core.github.template_builder import new_field

    kind = str(item.get("type") or "")
    label = _text(item.get("label")).strip() or str(item.get("id") or "")
    required = bool(item.get("required"))
    help_text = _text(item.get("help"))
    choices = [c for c in item.get("choices") or [] if isinstance(c, Mapping)]
    names = [_text(c.get("label")) or _text(c.get("value")) for c in choices]
    default = item.get("default")
    if kind == "html":
        props = _mapping(item.get("props"))
        return new_field("markdown", value=_text(props.get("html")) or help_text or label)
    if kind == "section":
        heading = f"### {label}" if _text(item.get("label")).strip() else ""
        value = "\n\n".join(part for part in (heading, help_text) if part)
        return new_field("markdown", value=value) if value else None
    if kind in _INPUT_TYPES or kind in _LONG_TYPES:
        return new_field(
            "input" if kind in _INPUT_TYPES else "textarea",
            label,
            required=required,
            description=help_text,
            placeholder=_text(item.get("placeholder")),
            value="" if default is None or isinstance(default, (dict, list)) else _text(default),
            taken=taken,
            ident=_github_id(item, taken),
        )
    if kind in ("select", "radio", "multiselect") and names:
        values = [_text(c.get("value")) for c in choices]
        return new_field(
            "dropdown",
            label,
            options=names,
            multiple=kind == "multiselect",
            required=required,
            description=help_text,
            default=values.index(default) if isinstance(default, str) and default in values else -1,
            taken=taken,
            ident=_github_id(item, taken),
        )
    if kind in ("checkbox", "consent"):
        options = names or [label]
        return new_field(
            "checkboxes",
            label,
            options=options,
            required_options=[required] * len(options),
            description=help_text,
            taken=taken,
            ident=_github_id(item, taken),
        )
    return None


def _github_id(item: Mapping[str, Any], taken: list[str]) -> str:
    """The model's id, which GitHub accepts as it is (letters, digits, underscores)."""
    from quill.core.github.template_builder import make_id

    ident = str(item.get("id") or "")
    return ident if ident and ident not in taken else make_id(_text(item.get("label")), taken)


def _losses(item: Mapping[str, Any], label: str) -> list[str]:
    lost: list[str] = []
    if item.get("when"):
        lost.append(f"{label}: its condition is left out; GitHub forms show every field.")
    if item.get("scoring"):
        lost.append(f"{label}: its scoring is left out.")
    if item.get("calculation"):
        lost.append(f"{label}: its calculation is left out.")
    if item.get("validation"):
        lost.append(f"{label}: its limits (such as a length or a range) are left out.")
    if item.get("type") == "radio":
        lost.append(f"{label}: becomes a drop-down list; GitHub forms have no radio buttons.")
    return lost


def export_github_draft(model: Mapping[str, Any]) -> tuple[Any, list[str]]:
    """A QAF model as an issue form draft (``FormDraft``), and what was left out.

    One sentence per thing left out. What :func:`import_github_issue_form`
    kept under ``extensions.github`` comes back: top-level keys, ids, render,
    per-option required check boxes, and anything else GitHub had.
    """
    from quill.core.github.template_builder import FormDraft, new_field

    kept = _kept(model)
    kind = str(kept.get("kind") or "issue_form")
    top: dict[str, Any] = {}
    if kind == "issue_form":
        top["name"] = _text(model.get("title")) or "Converted form"
    description = _text(model.get("description"))
    if description or kind == "issue_form":
        top["description"] = description or "Converted from a QUILL form."
    form_kept = kept.get("form")
    if isinstance(form_kept, Mapping):
        top.update(form_kept)
    draft = FormDraft(top=top, kind=kind)
    fields_kept = kept.get("fields") if isinstance(kept.get("fields"), Mapping) else {}
    report: list[str] = []
    taken: list[str] = []
    for item in M.iter_items(dict(model)):
        kind_name = str(item.get("type") or "")
        if kind_name == "columns":
            continue
        label = _text(item.get("label")).strip() or str(item.get("id") or kind_name)
        made = _element(item, taken)
        if made is None:
            if kind_name != "section":
                name = M.TYPE_NAMES.get(kind_name, kind_name)
                report.append(f"{label}: GitHub forms have no {name} field; left out.")
            continue
        report.extend(_losses(item, label))
        if isinstance(fields_kept, Mapping) and isinstance(
            fields_kept.get(item.get("id")), Mapping
        ):
            _apply_kept(made, fields_kept[item["id"]])
        if made.get("id"):
            taken.append(str(made["id"]))
        draft.fields.append(made)
    pages = model.get("pages") or []
    if len(pages) > 1:
        report.append(f"The form's {len(pages)} pages become one page; GitHub forms have no pages.")
    if model.get("translations"):
        report.append("Only the form's own language is saved; GitHub forms have no translations.")
    if model.get("confirmations") or model.get("notifications") or model.get("payments"):
        report.append("What happens after sending (messages, emails, payments) is left out.")
    if not any(raw.get("type") != "markdown" for raw in draft.fields):
        draft.fields.append(new_field("textarea", "Details", taken=taken))
        report.append("GitHub forms need a question, so a Details box was added.")
    return draft, report


def export_github_issue_form(model: Mapping[str, Any]) -> tuple[str, list[str]]:
    """A QAF model as issue form YAML, and the sentences to say about it.

    The sentences are what was left out, then any of GitHub's own checks that
    the result fails (each prefixed "GitHub will refuse this: "), so a save
    never hides a form GitHub would reject.
    """
    from quill.core.github.template_builder import check, dump_draft

    draft, report = export_github_draft(model)
    for problem in check(draft):
        if problem.severity == "error":
            report.append(f"GitHub will refuse this: {problem.sentence()}")
    return dump_draft(draft), report
