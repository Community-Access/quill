"""File > Export List in the GitHub Workbench (PRD 22.7), and what it leaves out (GX11).

The list as it is shown -- its columns, its filter, its rows -- written as an
Excel workbook, a CSV file or a Markdown table by the Workbench family's
shared writer (:mod:`quill.core.workbench.export`). Moved out of
:mod:`quill.ui.github_workbench_actions` (GATE-11) when security alert lists
began passing their cells through :func:`quill.core.github.alert_export.safe_rows`
first, so a token GitHub quoted in an alert's text never reaches the file.
The outcome is said once: how many rows, which hidden columns were left out,
and how many values were held back as tokens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["export_list"]


def export_list(bench: Any) -> None:
    """Ask where, write the list as shown, and say what was written."""
    from quill.core.github.alert_export import safe_rows
    from quill.core.workbench.export import EXPORT_WILDCARD, export_rows, hidden_columns_sentence

    frame = bench.frame
    if frame is None or not frame.rows:
        bench._say("There is nothing in the list to export.")
        return
    wx = frame._wx
    style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    with wx.FileDialog(frame.frame, "Export List", wildcard=EXPORT_WILDCARD, style=style) as box:
        if show_modal_dialog(box, "Export List") != wx.ID_OK:
            return
        path = Path(box.GetPath())
    node = frame.node(frame.current)
    columns = tuple(bench.columns(node))
    heading = [name.replace("_", " ").capitalize() for name in columns]
    shown = [[str(cell) for cell in bench.cells(row, columns)] for row in frame.rows]
    cells = safe_rows(node.loader, shown)
    try:
        count = export_rows(path, heading, cells)
    except OSError as exc:
        bench._say(f"Could not export the list: {exc}")
        return
    every = [str(n).replace("_", " ").capitalize() for n in getattr(node, "columns", ()) or ()]
    said = [f"Exported {count} {'row' if count == 1 else 'rows'} to {path.name}."]
    said.append(hidden_columns_sentence(heading, every))
    held = sum(
        a != b for was, now in zip(shown, cells, strict=True) for a, b in zip(was, now, strict=True)
    )
    if held:
        said.append(f"Held back: {held} {'value' if held == 1 else 'values'} like a token.")
    bench._say(" ".join(part for part in said if part))
    opener = getattr(bench, "_open_document", None)
    if (
        path.suffix.lower() == ".md"
        and callable(opener)
        and bench._confirm("Export List", f"Open {path.name} in the editor, as a table?")
    ):
        opener(path)
