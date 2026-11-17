"""New Template > Issue form > From a SurveyJS or XLSForm file (PRD 21.4).

The conversions were built with Phase 12 (``template_convert.qaf_to_draft``,
over the importers QUILL's Forms already had) and had no door: the only way to
reach them was a test. This is the door. It sits in New Template's "Start from"
list, beside the starters, because that is where somebody making an issue form
decides what to start from.

The file is read and converted in the background; the builder then opens on the
result, unsaved, exactly as a starter does, and Save asks before committing.
What did not carry over is said when it opens, never silently dropped.

Split from :mod:`quill.ui.github_workbench_templates` (GATE-11).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["FROM_FILE_LABEL", "start_from_form_file"]

#: The row New Template adds after the starters, for an issue form only.
FROM_FILE_LABEL = "From a SurveyJS or XLSForm file..."


def _pick_file(bench: Any) -> str:
    from quill.ui.dialog_contract import show_modal_dialog

    wx = bench.frame._wx
    with wx.FileDialog(
        bench.frame.frame,
        "Start an Issue Form from a File",
        wildcard=(
            "SurveyJS or XLSForm (*.json;*.xlsx;*.xls)|*.json;*.xlsx;*.xls|"
            "SurveyJS form (*.json)|*.json|XLSForm (*.xlsx;*.xls)|*.xlsx;*.xls"
        ),
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as chooser:
        if show_modal_dialog(chooser, "Start an Issue Form from a File") != wx.ID_OK:
            return ""
        return str(chooser.GetPath())


def _left_out(report: list[str]) -> str:
    if not report:
        return "Everything carried over."
    shown = " ".join(report[:3])
    more = f" And {len(report) - 3} more." if len(report) > 3 else ""
    return f"{len(report)} thing{'' if len(report) == 1 else 's'} did not carry over. {shown}{more}"


def start_from_form_file(bench: Any, repository: str, folder: str) -> None:
    """Choose the file, name the form, convert in the background, open the builder."""
    source = _pick_file(bench)
    if not source:
        return
    name = bench._ask_text(
        "New Template", "File name for the form:", value=Path(source).stem.replace("_", "-")
    )
    stem = name.strip().removesuffix(".yml").removesuffix(".yaml")
    if not stem:
        return
    path = f"{folder}/{stem}.yml"

    def work() -> tuple[str, list[str], Any]:
        from quill.core.github.template_builder import dump_draft
        from quill.core.github.template_convert import form_file_to_draft
        from quill.core.github.template_save import plan_save

        draft, report = form_file_to_draft(source)
        return (
            dump_draft(draft),
            report,
            plan_save(bench._template_repo(repository), repository, path),
        )

    def opened(found: tuple[str, list[str], Any]) -> None:
        text, report, plan = found
        if plan.current_sha:
            bench._say(f"{path} already exists; open it from the Templates list.")
            return
        bench._say(f"Converted {Path(source).name}. {_left_out(report)}")
        bench._open_template_builder("issue_form", repository, path, text, "", plan)

    bench._background(f"convert {Path(source).name}", work, opened)
