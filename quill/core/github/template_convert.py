"""Convert templates, and check a form's YAML with line numbers (GitHub PRD 21.4).

- :func:`form_to_markdown`: an issue form as a Markdown issue template. It
  loses the structure (required answers, drop-downs, check boxes become plain
  headings), and :func:`markdown_losses` says what first.
- :func:`qaf_to_draft`: a QUILL Forms (QAF) model -- which SurveyJS and
  XLSForm already import into (``quill.core.forms.interop_surveyjs`` and
  ``interop_xlsform``) -- as an issue form, with one report line for each
  field GitHub's forms cannot hold.
- :func:`check_form_text`: the builder's checks, each on the line of the
  YAML it is about, for Check This File (``quill.core.problems.builtin``).

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.template_builder import (
    FormDraft,
    TemplateDraftError,
    check,
    load_draft,
)

__all__ = [
    "check_form_text",
    "form_template_kind",
    "form_file_to_draft",
    "form_to_markdown",
    "markdown_losses",
    "qaf_to_draft",
]


def _attrs(raw: Mapping[str, Any]) -> dict[str, Any]:
    attrs = raw.get("attributes")
    return dict(attrs) if isinstance(attrs, Mapping) else {}


def markdown_losses(draft: FormDraft) -> list[str]:
    """What a Markdown template cannot keep from *draft*, one sentence each."""
    lost: list[str] = []
    for raw in draft.fields:
        label = str(_attrs(raw).get("label") or "")
        kind = raw.get("type")
        if isinstance(raw.get("validations"), Mapping) and raw["validations"].get("required"):
            lost.append(f"{label} will no longer be required.")
        if kind == "dropdown":
            lost.append(f"{label} becomes a heading with its options listed, not a choice.")
        if kind == "checkboxes":
            lost.append(f"{label} becomes a task list nobody is made to check.")
    for key in ("projects", "type"):
        if draft.top.get(key):
            lost.append(f"Markdown templates cannot set {key}.")
    return lost


def form_to_markdown(draft: FormDraft) -> str:
    """The Markdown issue template closest to *draft*."""
    import yaml  # type: ignore[import-untyped]

    front: dict[str, Any] = {
        "name": draft.get("name") or "Issue",
        "about": draft.get("description") or "",
    }
    for key in ("title", "labels", "assignees"):
        if draft.top.get(key):
            front[key] = draft.top[key]
    lines = ["---", yaml.safe_dump(front, sort_keys=False, allow_unicode=True).strip(), "---", ""]
    for raw in draft.fields:
        attrs = _attrs(raw)
        if raw.get("type") == "markdown":
            lines += [str(attrs.get("value") or "").strip(), ""]
            continue
        lines += [f"### {attrs.get('label') or 'Details'}", ""]
        if attrs.get("description"):
            lines += [f"<!-- {attrs['description']} -->", ""]
        raw_options = attrs.get("options")
        options: list[Any] = raw_options if isinstance(raw_options, list) else []
        if raw.get("type") == "checkboxes":
            for option in options:
                text = option.get("label", "") if isinstance(option, Mapping) else option
                lines.append(f"- [ ] {text}")
            lines.append("")
        elif raw.get("type") == "dropdown":
            lines += [f"<!-- One of: {', '.join(str(o) for o in options)} -->", ""]
        elif attrs.get("value"):
            lines += [str(attrs["value"]), ""]
    return "\n".join(lines).rstrip() + "\n"


def qaf_to_draft(model: Mapping[str, Any]) -> tuple[FormDraft, list[str]]:
    """A QAF model as an issue form, and what was left out (one sentence each).

    The one export, :func:`quill.core.forms.interop_github.export_github_draft`,
    which Save As GitHub Issue Form in the Forms commands also uses.
    """
    from quill.core.forms.interop_github import export_github_draft

    draft, report = export_github_draft(model)
    return draft, report


#: Files New Template can start an issue form from (PRD 21.4), by extension.
FORM_FILE_KINDS: dict[str, str] = {".json": "SurveyJS", ".xlsx": "XLSForm", ".xls": "XLSForm"}


def form_file_to_draft(path: str) -> tuple[FormDraft, list[str]]:
    """A SurveyJS (``.json``) or XLSForm (``.xlsx``) file as an issue form.

    Both go through the QUILL Forms model their importers already build
    (``interop_surveyjs`` and ``interop_xlsform``), then :func:`qaf_to_draft`.
    The report is the importer's sentences followed by what the issue form left
    out, so nothing is lost without being said. Raises ``ValueError`` for any
    other kind of file.
    """
    from pathlib import Path

    suffix = Path(path).suffix.lower()
    kind = FORM_FILE_KINDS.get(suffix)
    if kind == "SurveyJS":
        from quill.core.forms.interop_surveyjs import import_surveyjs

        imported = import_surveyjs(Path(path).read_text(encoding="utf-8"))
    elif kind == "XLSForm":
        from quill.core.forms.interop_xlsform import import_xlsform

        imported = import_xlsform(path)
    else:
        raise ValueError("Choose a SurveyJS form (.json) or an XLSForm (.xlsx).")
    draft, left_out = qaf_to_draft(imported.model)
    draft.top["description"] = f"Converted from a {kind} form."
    return draft, [*imported.report, *left_out]


def form_template_kind(path: str) -> str:
    """Whether *path* is an issue form, a discussion form, or neither ("")."""
    parts = [p.casefold() for p in path.replace("\\", "/").split("/")]
    name = parts[-1] if parts else ""
    if not name.endswith((".yml", ".yaml")) or name.startswith("config."):
        return ""
    if len(parts) >= 3 and parts[-3] == ".github":
        if parts[-2] == "issue_template":
            return "issue_form"
        if parts[-2] == "discussion_template":
            return "discussion_form"
    return ""


def _lines(text: str) -> tuple[dict[str, int], list[int]]:
    """``(top-level key -> line, body element lines)``, 1-based."""
    import yaml

    keys: dict[str, int] = {}
    body: list[int] = []
    try:
        node = yaml.compose(text)
    except yaml.YAMLError:
        return keys, body
    if not isinstance(node, yaml.MappingNode):
        return keys, body
    for key_node, value_node in node.value:
        name = str(key_node.value)
        keys[name] = key_node.start_mark.line + 1
        if name == "body" and isinstance(value_node, yaml.SequenceNode):
            body = [element.start_mark.line + 1 for element in value_node.value]
    return keys, body


def check_form_text(text: str, kind: str) -> list[tuple[int, str, str]]:
    """``(line, severity, message)`` for every problem in a form's YAML."""
    try:
        draft = load_draft(text, kind=kind)
    except TemplateDraftError as exc:
        return [(1, "error", str(exc.args[0]) if exc.args else str(exc))]
    keys, body = _lines(text)
    found: list[tuple[int, str, str]] = []
    for problem in check(draft):
        line = keys.get(problem.where.casefold(), keys.get("body", 1))
        if problem.where.startswith("Field "):
            number = problem.where.split()[1]
            index = int(number) - 1 if number.isdigit() else -1
            line = body[index] if 0 <= index < len(body) else line
        elif problem.where in ("Name", "Description", "Labels"):
            line = keys.get(problem.where.casefold(), 1)
        found.append((line, problem.severity, problem.sentence()))
    return found
