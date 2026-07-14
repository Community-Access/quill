"""Validate Agents dialog (Phase 6 UI) — the agent standards linter, in the app.

A screen-reader-friendly surface over :mod:`quill.tools.agent_lint`. It runs the
same standards rules the CI gate uses on the bundled agents folder by default, or
on any agent file / folder the user picks, and lists each finding (level, file,
message) in an accessible list with a one-line summary.

This is the "if someone edits an agent" feedback loop: edit the Markdown, open
this dialog, see exactly what fails the standard. Linting is fast (small text
files) and runs on the UI thread; no SDKs, no network.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.ai.agent_catalog import bundled_agents_dir
from quill.tools.agent_lint import ERROR, WARNING, Finding, lint_dir, lint_path
from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control


class AgentValidatorDialog:
    """Run the agent standards linter and show findings, accessibly."""

    def __init__(
        self,
        parent: object,
        show_modal_dialog: Callable,
        announce: Callable[[str], None] | None = None,
        initial_path: Path | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._show_modal = show_modal_dialog
        self._announce = announce or (lambda _m: None)
        self._target: Path = initial_path or bundled_agents_dir()

        self.dialog = wx.Dialog(
            parent,
            title="Validate Agents",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(680, 480))
        self._build_ui()
        self._run()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Check agent files against QUILL's authoring standards (the same "
                "rules the build enforces). Validate the built-in agents, or browse "
                "to a file or folder of your own."
            ),
        )
        intro.Wrap(640)
        root.Add(intro, 0, wx.ALL, 12)

        root.Add(wx.StaticText(self.dialog, label="Validating:"), 0, wx.LEFT | wx.TOP, 12)
        self.path_ctrl = wx.TextCtrl(self.dialog, value=str(self._target), style=wx.TE_READONLY)
        self.path_ctrl.SetName("Path being validated")
        root.Add(self.path_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        picks = wx.BoxSizer(wx.HORIZONTAL)
        self.folder_btn = wx.Button(self.dialog, label="Choose &Folder...")
        self.file_btn = wx.Button(self.dialog, label="Choose F&ile...")
        self.builtin_btn = wx.Button(self.dialog, label="&Built-in Agents")
        self.validate_btn = wx.Button(self.dialog, label="&Validate")
        for btn in (self.folder_btn, self.file_btn, self.builtin_btn, self.validate_btn):
            picks.Add(btn, 0, wx.RIGHT, 8)
        root.Add(picks, 0, wx.ALL, 12)

        self.summary = wx.StaticText(self.dialog, label="")
        root.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        root.Add(wx.StaticText(self.dialog, label="Findings:"), 0, wx.LEFT | wx.TOP, 12)
        self.results = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self.results.SetName("Validation findings")
        root.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        self.close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="&Close")
        buttons.Add(self.close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self.validate_btn.SetDefault()

        self.folder_btn.Bind(wx.EVT_BUTTON, self._on_choose_folder)
        self.file_btn.Bind(wx.EVT_BUTTON, self._on_choose_file)
        self.builtin_btn.Bind(wx.EVT_BUTTON, self._on_builtin)
        self.validate_btn.Bind(wx.EVT_BUTTON, lambda _e: self._run())

    # ------------------------------------------------------------------
    # Target selection
    # ------------------------------------------------------------------

    def _set_target(self, path: Path) -> None:
        self._target = path
        self.path_ctrl.SetValue(str(path))
        self._run()

    def _on_choose_folder(self, _event: object) -> None:
        wx = self._wx
        with wx.DirDialog(
            self.dialog, "Choose a folder of agent files", style=wx.DD_DIR_MUST_EXIST
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._set_target(Path(dlg.GetPath()))

    def _on_choose_file(self, _event: object) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Choose an agent file",
            wildcard="Agent files (*.md;*.json)|*.md;*.json",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._set_target(Path(dlg.GetPath()))

    def _on_builtin(self, _event: object) -> None:
        self._set_target(bundled_agents_dir())

    # ------------------------------------------------------------------
    # Run + render
    # ------------------------------------------------------------------

    def _run(self) -> None:
        try:
            findings = lint_path(self._target) if self._target.is_file() else lint_dir(self._target)
        except Exception as exc:  # noqa: BLE001 - never crash the dialog
            findings = [Finding(ERROR, str(self._target), f"could not validate: {exc}")]
        self._render(findings)

    def _render(self, findings: list[Finding]) -> None:
        self.results.Clear()
        errors = sum(1 for f in findings if f.level == ERROR)
        warnings = sum(1 for f in findings if f.level == WARNING)
        for finding in findings:
            name = Path(finding.path).name
            self.results.Append(f"{finding.level.upper()}  {name}: {finding.message}")
        if not findings:
            summary = "All agents pass the standards. No problems found."
        else:
            summary = f"{errors} error(s), {warnings} warning(s)."
        self.summary.SetLabel(summary)
        self._announce(summary)
        if findings:
            self.results.SetSelection(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        self.dialog.CentreOnParent()
        focus_primary_control(self.dialog)
        try:
            self._show_modal(self.dialog)
        finally:
            self.dialog.Destroy()
