"""Podcasts > Import OPML... > import report -- which imported shows'
feeds turned out to be unreachable, viewable and exportable."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.core.counted import plural
from quill.core.podcasts.opml import OpmlValidationResult
from quill.ui.dialog_contract import bind_close_button
from quill.ui.dpi import dip_size
from quill.ui.surface_lifetime import surface_tasks


def summary_sentence(results: list[OpmlValidationResult], skipped: int) -> str:
    """The one-line count at the top of the report, in agreeing words.

    "Updated to a new address" counts only the moves actually made. It used to
    say "154 corrected", for redirects that changed nothing and a lookup that
    never ran (check.md bug 5).
    """
    failed = sum(1 for result in results if not result.ok)
    updated = sum(1 for result in results if result.corrected_url and result.applied)
    return (
        f"{plural(len(results), 'feed')} checked: {len(results) - failed} reachable, "
        f"{failed} unreachable, {updated} updated to a new address, "
        f"{plural(skipped, 'duplicate')} skipped."
    )


def format_report_text(
    results: list[OpmlValidationResult],
    *,
    skipped_duplicates: list[str] | None = None,
    possible_duplicates: list[str] | None = None,
    unusable: list[str] | None = None,
) -> str:
    """The exportable plain-text form of a validation report."""
    failed = [r for r in results if not r.ok]
    updated = [r for r in results if r.corrected_url and r.applied]
    moved = [r for r in results if r.corrected_url and not r.applied]
    skipped = skipped_duplicates or []
    possible = possible_duplicates or []
    broken = unusable or []
    lines = [
        f"OPML import report: {summary_sentence(results, len(skipped))}",
        "",
    ]
    if broken:
        lines.append("Entries that could not be imported at all:")
        for entry in broken:
            lines.append(f"- {entry}")
        lines.append("")
    if updated:
        lines.append("Updated to the feed's new address (the host says it moved for good):")
        for result in updated:
            lines.append(f"- {result.title}, now at {result.corrected_url}")
        lines.append("")
    if moved:
        lines.append(
            "Moved for good, but left alone because Follow permanent feed redirects is off:"
        )
        for result in moved:
            lines.append(f"- {result.title}, now at {result.corrected_url}")
        lines.append("")
    if failed:
        lines.append("Unreachable feeds:")
        for result in failed:
            lines.append(f"- {result.title} ({result.feed_url}): {result.error}")
        lines.append("")
    if skipped:
        lines.append("Skipped as already followed (same feed URL):")
        for entry in skipped:
            lines.append(f"- {entry}")
        lines.append("")
    if possible:
        lines.append(
            "Imported, but share a name with another podcast (different "
            "feeds; two different shows CAN share a name — review these):"
        )
        for entry in possible:
            lines.append(f"- {entry}")
        lines.append("")
    if not results:
        lines.append("No feed checks were completed.")
    elif not failed and not updated and not moved and not skipped and not possible and not broken:
        lines.append("Every checked feed was reachable.")
    return "\n".join(lines).rstrip() + "\n"


class OpmlImportReportDialog:
    """Shows which newly-imported feeds could not be reached, with an
    Export... button to save the report as a text file."""

    TITLE = "OPML Import Report"
    MENU_TITLE = "&Report"

    def __init__(
        self,
        parent: object,
        *,
        results: list[OpmlValidationResult],
        skipped_duplicates: list[str] | None = None,
        possible_duplicates: list[str] | None = None,
        unusable: list[str] | None = None,
        source_opml: str = "",
        announce_cb: Callable[[str], None] | None = None,
        host: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._results = results
        self._skipped_duplicates = skipped_duplicates or []
        self._possible_duplicates = possible_duplicates or []
        self._unusable = unusable or []
        #: The file as it was read, so Save Pruned OPML can write the same
        #: document back minus the dead feeds -- preserving folders, extra
        #: attributes, and anything QUILL does not model, which re-exporting
        #: the library would quietly drop.
        self._source_opml = source_opml
        self._announce = announce_cb or (lambda _m: None)

        failed = [r for r in results if not r.ok]
        self._host = host or SimpleNamespace(frame=parent, _wx=wx, _announce=self._announce)
        self.frame = wx.Frame(parent, title="OPML Import Report")
        self._frame_id = self.frame.GetId()
        self._population_later: Any = None
        self.dialog = self.frame
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 420))
        panel = wx.Panel(self.frame)
        from quill.stability.task_manager import TaskManager

        self._owned_tasks = TaskManager(max_workers=1) if host is None else None
        manager = self._owned_tasks if host is None else host._task_manager
        self._task_manager = surface_tasks(manager, lambda: self.frame)
        self.frame.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(
            panel,
            label=summary_sentence(results, len(self._skipped_duplicates)),
        )
        root.Add(summary, 0, wx.EXPAND | wx.ALL, 10)
        self._summary = summary

        self._list = wx.ListBox(panel)
        self._list.SetName("Import findings: new addresses, failures, and duplicates")
        self._list.SetHelpText(
            "Review feed errors, permanent moves, and duplicate podcasts. "
            "Export Report saves the findings; Save Pruned OPML saves a separate cleaned copy."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        export_btn = wx.Button(panel, label="&Export Report...")
        export_btn.SetHelpText("Save the import report as a text file in the background.")
        prune_btn = wx.Button(panel, label="Save &Pruned OPML...")
        prune_btn.SetHelpText(
            "Save a separate OPML copy without unreachable feeds. The source file is preserved."
        )
        prune_btn.SetName(
            "Save a copy of the OPML file with every unreachable feed removed, "
            "so the list you keep elsewhere can be cleaned up too"
        )
        prune_btn.Enable(bool(self._source_opml) and bool(failed))
        self._prune_btn = prune_btn
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetDefault()
        close_btn.SetHelpText("Hide this report and return to the window that opened it.")
        btn_row.Add(export_btn, 0, wx.RIGHT, 6)
        btn_row.Add(prune_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.frame.SetSizer(outer)
        bind_close_button(self.frame, close_btn, modeless=True)
        export_btn.Bind(wx.EVT_BUTTON, self._on_export)
        prune_btn.Bind(wx.EVT_BUTTON, self._on_prune)
        self._populate()

    def _on_destroy(self, event: Any) -> None:
        if event.GetId() == self._frame_id:
            if self._population_later is not None:
                self._population_later.Stop()
            if self._owned_tasks is not None:
                self._owned_tasks.shutdown(wait=False, cancel_pending=True)
        event.Skip()

    def set_findings(
        self,
        *,
        results: list[OpmlValidationResult],
        skipped_duplicates: list[str],
        possible_duplicates: list[str],
        unusable: list[str],
        source_opml: str,
    ) -> None:
        if self._population_later is not None:
            self._population_later.Stop()
        self._results = results
        self._skipped_duplicates = skipped_duplicates
        self._possible_duplicates = possible_duplicates
        self._unusable = unusable
        self._source_opml = source_opml
        self._summary.SetLabel(summary_sentence(results, len(skipped_duplicates)))
        self._prune_btn.Enable(bool(source_opml) and any(not result.ok for result in results))
        self._list.Clear()
        self._populate()

    def _findings(self) -> Any:
        for result in self._results:
            if result.corrected_url:
                prefix = "Updated" if result.applied else "Moved, left alone"
                yield f"{prefix}: {result.title}, now at {result.corrected_url}"
            elif not result.ok:
                yield f"Unreachable: {result.title} -- {result.error}"
        for entry in self._skipped_duplicates:
            yield f"Skipped duplicate: {entry}"
        for entry in self._possible_duplicates:
            yield f"Same name, different feed (review): {entry}"
        for entry in self._unusable:
            yield f"Could not import: {entry}"

    def _populate(self) -> None:
        from time import perf_counter

        rows = self._findings()

        def advance() -> None:
            self._population_later = None
            deadline = perf_counter() + 0.008
            try:
                for _ in range(32):
                    self._list.Append(next(rows))
                    if perf_counter() >= deadline:
                        break
            except StopIteration:
                if not self._list.GetCount():
                    self._list.Append(
                        "Every checked feed was reachable."
                        if self._results
                        else "No feed checks were completed."
                    )
                self._list.SetSelection(0)
                return
            self._population_later = self._wx.CallLater(1, advance)

        advance()

    def show(self, *, focus: bool = True) -> None:
        from quill.ui.podcasts.peer_window import open_peer

        previous = self._host.__dict__.get("_opml_import_report_window")
        if previous is not None and previous is not self and previous.frame:
            windows = getattr(self._host, "_windows", None)
            if windows is not None:
                windows.unregister(previous.frame)
            previous.frame.Destroy()
            self._host._opml_import_report_window = None
        self.dialog.CentreOnParent()
        open_peer(self._host, "_opml_import_report_window", lambda _host: self, focus=focus)

    def focus_target(self) -> Any:
        return self._list

    def menu_rows(self) -> list[tuple[str, Any]]:
        return [
            ("Export report\tCtrl+S", lambda: self._on_export(None)),
            ("Save pruned OPML\tCtrl+P", lambda: self._on_prune(None)),
        ]

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
        results = list(self._results)
        skipped = list(self._skipped_duplicates)
        possible = list(self._possible_duplicates)
        unusable = list(self._unusable)

        def write(**_kwargs: object) -> None:
            report = format_report_text(
                results,
                skipped_duplicates=skipped,
                possible_duplicates=possible,
                unusable=unusable,
            )
            path.write_text(report, encoding="utf-8")

        self._task_manager.submit(
            "opml-export-report",
            write,
            on_success=lambda _op, _result: self._announce(f"Saved report to {path.name}"),
            on_failure=lambda _op, error: self._announce(f"Could not save the report: {error}"),
        )

    def _on_prune(self, _event: object) -> None:
        """Write the source OPML back without the feeds that did not answer.

        The point of learning that 312 feeds are dead is being able to do
        something about it; this is that something, and it edits the original
        document rather than re-exporting the library, so folders and any
        attributes QUILL does not model survive intact.
        """
        from quill.core.podcasts.opml_import import prune_opml

        wx = self._wx
        dead = [result.feed_url for result in self._results if not result.ok]
        if not dead or not self._source_opml:
            self._announce("There is nothing to prune.")
            return
        with wx.FileDialog(
            self.dialog,
            "Save Pruned OPML",
            defaultFile="subscriptions-pruned.opml",
            wildcard="OPML files (*.opml)|*.opml|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        source = self._source_opml

        def write(**_kwargs: object) -> None:
            path.write_text(prune_opml(source, dead), encoding="utf-8")

        self._task_manager.submit(
            "opml-save-pruned",
            write,
            on_success=lambda _op, _result: self._announce(
                f"Saved {path.name} with {plural(len(dead), 'unreachable feed')} removed"
            ),
            on_failure=lambda _op, error: self._announce(
                f"Could not save the pruned file: {error}"
            ),
        )
