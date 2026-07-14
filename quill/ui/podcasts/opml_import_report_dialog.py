"""Podcasts > Import OPML... > import report -- which imported shows'
feeds turned out to be unreachable, viewable and exportable."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts.opml import OpmlValidationResult
from quill.ui.dialog_contract import apply_modal_ids


def format_report_text(
    results: list[OpmlValidationResult],
    *,
    skipped_duplicates: list[str] | None = None,
    possible_duplicates: list[str] | None = None,
) -> str:
    """The exportable plain-text form of a validation report."""
    failed = [r for r in results if not r.ok]
    corrected = [r for r in results if r.corrected_url]
    skipped = skipped_duplicates or []
    possible = possible_duplicates or []
    lines = [
        f"OPML import report: {len(results)} feed(s) checked, "
        f"{len(results) - len(failed)} reachable, {len(failed)} unreachable, "
        f"{len(corrected)} corrected, {len(skipped)} duplicate(s) skipped.",
        "",
    ]
    if corrected:
        lines.append("Corrected feed URLs (found working replacements via iTunes):")
        for result in corrected:
            lines.append(f"- {result.title}: {result.feed_url} -> {result.corrected_url}")
        lines.append("")
    if failed:
        lines.append("Unreachable feeds:")
        for result in failed:
            lines.append(f"- {result.title} ({result.feed_url}): {result.error}")
        lines.append("")
    if skipped:
        lines.append("Skipped as already subscribed (same feed URL):")
        for entry in skipped:
            lines.append(f"- {entry}")
        lines.append("")
    if possible:
        lines.append(
            "Imported, but share a name with another subscription (different "
            "feeds; two different shows CAN share a name — review these):"
        )
        for entry in possible:
            lines.append(f"- {entry}")
        lines.append("")
    if not failed and not corrected and not skipped and not possible:
        lines.append("Every imported feed was reachable.")
    return "\n".join(lines).rstrip() + "\n"


class OpmlImportReportDialog:
    """Shows which newly-imported feeds could not be reached, with an
    Export... button to save the report as a text file."""

    def __init__(
        self,
        parent: object,
        *,
        results: list[OpmlValidationResult],
        skipped_duplicates: list[str] | None = None,
        possible_duplicates: list[str] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._results = results
        self._skipped_duplicates = skipped_duplicates or []
        self._possible_duplicates = possible_duplicates or []
        self._announce = announce_cb or (lambda _m: None)

        failed = [r for r in results if not r.ok]
        corrected = [r for r in results if r.corrected_url]
        self.dialog = wx.Dialog(
            parent,
            title="OPML Import Report",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((560, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(
            self.dialog,
            label=(
                f"{len(results)} feed(s) checked: {len(results) - len(failed)} reachable, "
                f"{len(failed)} unreachable, {len(corrected)} corrected, "
                f"{len(self._skipped_duplicates)} duplicate(s) skipped."
            ),
        )
        root.Add(summary, 0, wx.EXPAND | wx.ALL, 10)

        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Import findings: corrections, failures, and duplicates")
        for result in corrected:
            self._list.Append(
                f"Corrected: {result.title} -- {result.feed_url} -> {result.corrected_url}"
            )
        for result in failed:
            self._list.Append(f"Unreachable: {result.title} -- {result.error}")
        for entry in self._skipped_duplicates:
            self._list.Append(f"Skipped duplicate: {entry}")
        for entry in self._possible_duplicates:
            self._list.Append(f"Same name, different feed (review): {entry}")
        if self._list.GetCount() == 0:
            self._list.Append("Every imported feed was reachable.")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        export_btn = wx.Button(self.dialog, label="&Export Report...")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(export_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        export_btn.Bind(wx.EVT_BUTTON, self._on_export)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL, escape_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "OPML Import Report", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _on_export(self, _event: object) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Export Report",
            defaultFile="opml-import-report.txt",
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        try:
            path.write_text(
                format_report_text(
                    self._results,
                    skipped_duplicates=self._skipped_duplicates,
                    possible_duplicates=self._possible_duplicates,
                ),
                encoding="utf-8",
            )
        except OSError as error:
            self._announce(f"Could not save the report: {error}")
            return
        self._announce(f"Saved report to {path.name}")
