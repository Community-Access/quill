"""Diagnostics on QUILL's main window (qc.md F-08, extracted 2026-10-03).

Save Diagnostics Bundle and Report a Bug: gathering the redacted bundle, the
review of what it holds before anything is written or sent, and where it went.
One lifetime -- a bundle made, reviewed and handed over -- moved whole out of
``MainFrame``; the host contract is unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quill import __version__
from quill.core.diagnostics import build_diagnostics_review_text, write_diagnostics_bundle
from quill.core.paths import app_data_dir
from quill.platform.windows.sr_detect import detect_screen_reader
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class DiagnosticsMixin:
    """Save Diagnostics Bundle and Report a Bug; mixed into MainFrame."""

    def save_diagnostics_bundle(self) -> None:
        wx = self._wx
        include_paths = self._review_diagnostics_export()
        if include_paths is None:
            self._set_status("Diagnostics export cancelled")
            return
        default_name = f"quill-diagnostics-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip"
        with wx.FileDialog(
            self.frame,
            "Save diagnostics bundle",
            wildcard="ZIP archives (*.zip)|*.zip|All files (*.*)|*.*",
            defaultFile=default_name,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save Diagnostics") != wx.ID_OK:
                self._set_status("Diagnostics export cancelled")
                return
            target = Path(dialog.GetPath())

        detection = detect_screen_reader()
        bundle_path = write_diagnostics_bundle(
            target,
            settings=self.settings,
            keymap=self.keymap,
            notifications=self._notifications,
            current_document=self.document,
            include_file_paths=include_paths,
            extra_environment={
                "screen_reader": detection.name,
                "wx_version": self._wx.version(),
                **self._announcement_engine.diagnostics_environment(),
                "bw_rollout": self._bw_diagnostics_snapshot(),
            },
        )
        self._record_notification(f"Saved diagnostics to {bundle_path.name}", "diagnostics")
        self._set_status(f"Saved diagnostics bundle to {bundle_path.name}")

    def report_bug(self) -> None:
        """Help > Get Help from Support... -- QUILL's door to a human.

        The name is the old one because the command id, the palette entry and
        the feature map all carry it; what it does is the family flow in
        :mod:`quill.ui.support_dialog`, which reaches a person who can answer
        instead of filing the reporter's own words into a public repository.

        The menu label is QUILL Lite's, "Get Help from Support...", but its
        access key is L rather than Lite's G: Open User &Guide already owns G
        in QUILL's Help menu, and a duplicate mnemonic makes Windows cycle
        between the two instead of pressing either (GATE-14). The command id
        stays ``help.report_bug`` so a user's rebinding survives; the chord,
        Ctrl+Alt+F2, is the same in both editors. The QUILL AI support ID goes
        in through ``ai_support_facts`` (the shared hosted-AI mixin).
        """
        from quill.ui.support_dialog import open_support_message

        open_support_message(self, source_app="QUILL", app_version=__version__ or "0.0.0")

    #: The menu's name for it. One flow, two names, no second implementation.
    get_help_from_support = report_bug

    def _review_diagnostics_export(self) -> bool | None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Review Diagnostics Export", size=(780, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        include_paths = wx.CheckBox(dialog, label="Include plain file paths in the bundle")
        review_label = wx.StaticText(dialog, label="Diagnostics &review:")
        review = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(review, "Diagnostics review")
        copy_button = wx.Button(dialog, label="Copy Summary")
        continue_button = wx.Button(dialog, id=wx.ID_OK, label="Continue")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")

        def refresh() -> None:
            detection = detect_screen_reader()
            review.SetValue(
                build_diagnostics_review_text(
                    settings=self.settings,
                    keymap=self.keymap,
                    notifications=self._notifications,
                    current_document=self.document,
                    include_file_paths=include_paths.GetValue(),
                    extra_environment={
                        "screen_reader": detection.name,
                        "wx_version": self._wx.version(),
                        **self._announcement_engine.diagnostics_environment(),
                        "bw_rollout": self._bw_diagnostics_snapshot(),
                    },
                )
            )

        include_paths.Bind(wx.EVT_CHECKBOX, lambda _e: refresh())
        copy_button.Bind(
            wx.EVT_BUTTON,
            lambda _e: self._copy_to_clipboard(review.GetValue()),
        )
        continue_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Review what Quill will include before writing the diagnostics zip. "
                    "Nothing leaves your machine from this step."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        root.Add(wx.StaticText(dialog, label="Logs folder"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        logs_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        set_accessible_name(logs_field, "Logs folder")
        logs_field.SetValue(str(app_data_dir() / "logs"))
        root.Add(logs_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dialog, label="Diagnostics folder"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        diagnostics_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        set_accessible_name(diagnostics_field, "Diagnostics folder")
        diagnostics_field.SetValue(str(app_data_dir() / "diagnostics"))
        root.Add(diagnostics_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        root.Add(include_paths, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        root.Add(review_label, 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(review, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(copy_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(continue_button, 0, wx.RIGHT, 6)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        refresh()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "Review Diagnostics Export") != wx.ID_OK:
                return None
            return include_paths.GetValue()
        finally:
            # Destroyed here: the dialog used to outlive the review (found by
            # the A11Y-4 gate once this moved out of main_frame.py under F-08).
            dialog.Destroy()
