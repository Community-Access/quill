"""Verbosity token editor dialog (verbosity §13, §18).

Edits the announcement template for one verb. A Simple / Advanced view switch
(a ``wx.RadioBox`` per the §5 locked decision, not a notebook) shares one
template field. Validation and preview run against the verb's own token list via
the pure core (:mod:`quill.core.verbosity.parser`): ``Ctrl+T`` validates and
speaks the summary, ``Ctrl+Shift+P`` previews, and Save is disabled while
blocking errors exist. A11Y-4 hardened: label-then-control, mnemonics,
``apply_modal_ids``, no icon-only buttons.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.parser import render_template, validate
from quill.core.verbosity.preview import BUILTIN_SCENARIOS
from quill.core.verbosity.verbs import VerbSpec
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["VerbosityTokenEditorDialog"]


class VerbosityTokenEditorDialog:
    """Edit and validate one verb's announcement template."""

    def __init__(
        self,
        parent: object,
        verb: VerbSpec,
        *,
        template: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._verb = verb
        self._announce = announce_cb or (lambda _m: None)
        self._result: str | None = None

        self.dialog = wx.Dialog(
            parent,
            title=f"Edit announcement — {verb.human_name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        self._view = wx.RadioBox(
            self.dialog,
            label="&View",
            choices=["Simple", "Advanced"],
            style=wx.RA_SPECIFY_COLS,
        )
        self._view.SetName("Token editor view")
        root.Add(self._view, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self.dialog, label="&Template:"), 0, wx.LEFT | wx.TOP, 8)
        self._template = wx.TextCtrl(self.dialog, value=template, style=wx.TE_MULTILINE)
        self._template.SetName("Announcement template")
        self._template.SetHint("e.g. Line {line} of {total}")
        self._template.SetMinSize(wx.Size(-1, 70))
        root.Add(self._template, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        root.Add(wx.StaticText(self.dialog, label="Available &tokens:"), 0, wx.LEFT | wx.TOP, 8)
        self._tokens = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._tokens.SetName("Available tokens")
        for spec in verb.supported_tokens:
            self._tokens.Append(f"{{{spec.name}}} — {spec.description}")
        self._tokens.SetMinSize(wx.Size(-1, 90))
        root.Add(self._tokens, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        root.Add(wx.StaticText(self.dialog, label="&Review:"), 0, wx.LEFT | wx.TOP, 8)
        self._review = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._review.SetName("Validation and preview")
        self._review.SetMinSize(wx.Size(-1, 80))
        root.Add(self._review, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._validate_btn = wx.Button(self.dialog, label="&Validate (Ctrl+T)")
        self._preview_btn = wx.Button(self.dialog, label="&Preview (Ctrl+Shift+P)")
        self._speak_btn = wx.Button(self.dialog, label="&Speak Current Template")
        self._insert_btn = wx.Button(self.dialog, label="&Insert Token")
        self._save_btn = wx.Button(self.dialog, id=wx.ID_SAVE, label="Sa&ve")
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Cancel")
        for b in (self._validate_btn, self._preview_btn, self._speak_btn, self._insert_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(self._save_btn, 0, wx.RIGHT, 6)
        btns.Add(cancel_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_SAVE,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
        )

        self._validate_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_validate())
        self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_preview())
        self._speak_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_speak())
        self._insert_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_insert())
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._template.Bind(wx.EVT_TEXT, lambda _e: self._refresh_save_state())
        self._refresh_save_state()

    # -- behavior -----------------------------------------------------------

    def _report(self):
        return validate(self._template.GetValue(), self._verb)

    def _refresh_save_state(self) -> None:
        report = self._report()
        self._save_btn.Enable(report.ok)
        self._save_btn.SetToolTip("" if report.ok else f"{len(report.errors)} error — fix to save")

    def _on_validate(self) -> None:
        report = self._report()
        lines = [report.spoken_summary]
        for issue in report.issues:
            prefix = "[X]" if issue.severity == "error" else "[!]"
            lines.append(f"{prefix} {issue.message}")
        if report.ok and not report.issues:
            lines.append("[OK] Template is valid.")
        self._review.SetValue("\n".join(lines))
        self._announce(report.spoken_summary)
        self._refresh_save_state()

    def _sample_values(self) -> dict[str, object]:
        for scenario in BUILTIN_SCENARIOS:
            if scenario.verb_id == self._verb.id:
                return dict(scenario.context)
        return {spec.name: spec.name for spec in self._verb.supported_tokens}

    def _on_preview(self) -> None:
        rendered = render_template(
            self._template.GetValue(), self._sample_values(), self._verb.supported_tokens
        )
        self._review.SetValue(f"Preview: {rendered}")
        self._announce(f"Preview. {rendered}")

    def _on_speak(self) -> None:
        self._announce(f"Current template. {self._template.GetValue()}")

    def _on_insert(self) -> None:
        index = self._tokens.GetSelection()
        if index < 0:
            return
        spec = self._verb.supported_tokens[index]
        self._template.WriteText(f"{{{spec.name}}}")

    def _on_save(self) -> None:
        if not self._report().ok:
            self._announce(f"Save disabled, {len(self._report().errors)} errors.")
            return
        self._result = self._template.GetValue()
        self.dialog.EndModal(wx.ID_SAVE)

    def _on_char_hook(self, event: object) -> None:
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        shift = event.ShiftDown()
        if ctrl and not shift and key == ord("T"):
            self._on_validate()
        elif ctrl and shift and key == ord("P"):
            self._on_preview()
        else:
            event.Skip()

    # -- lifecycle ----------------------------------------------------------

    @property
    def template(self) -> str | None:
        """The saved template, or ``None`` if cancelled."""
        return self._result

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CANCEL)
