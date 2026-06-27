"""File > Convert File dialog.

A standalone, accessible front end over Pandoc that lets the user pick a source
file, an output format, and an output folder, then either write the converted
file to disk ("Convert File", primary) or -- for text formats QUILL can edit --
write it and open it in a new tab ("Convert and Open", secondary).

The dialog is pure UI plumbing: it gathers a :class:`ConvertRequest` and hands
it back to ``MainFrame``, which owns the actual Pandoc call, the overwrite
prompt, and the remembered-settings writes. Keeping the conversion out of here
means the dialog stays testable as a widget and the policy lives in one place.

Format list is hybrid (issue: Convert File): the curated
:data:`quill.core.convert_formats.CURATED_OUTPUTS` is shown by default; ticking
"Show all Pandoc formats" repopulates the choice from a runtime probe of the
installed Pandoc's writers.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import wx

from quill.core import convert_formats
from quill.core.i18n import _
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_log = logging.getLogger(__name__)

# Secondary action return code. wx.ID_OK means "Convert File" (save to disk);
# this distinct code means "Convert and Open in a new tab".
ID_CONVERT_AND_OPEN = wx.ID_APPLY


@dataclass(frozen=True, slots=True)
class ConvertRequest:
    """The user's confirmed Convert File choices."""

    source_path: Path
    output_token: str
    output_dir: Path
    action: str  # "save" or "open"

    @property
    def output_path(self) -> Path:
        """Full destination path = output folder + source stem + format extension."""

        ext = convert_formats.extension_for(self.output_token)
        return self.output_dir / (self.source_path.stem + ext)


class ConvertFileDialog:
    """Modal Convert File dialog. Call :meth:`prompt` to run it."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        default_output_dir: str,
        default_format: str,
        show_modal_fn: Callable[[wx.Dialog, str], int] | None = None,
    ) -> None:
        # Default to the shared accessible modal helper (show_modal_dialog) so
        # the dialog works standalone; MainFrame injects its richer
        # _show_modal_dialog (focus, announce, region tracking) in practice.
        self._show_modal_fn = show_modal_fn or show_modal_dialog
        self._tokens: list[str] = []

        self.dialog = wx.Dialog(
            parent,
            title=_("Convert File"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetName(_("Convert File — choose a source, format, and output folder"))
        self.dialog.SetSize((760, 420))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=_(
                    "Convert a document to another format with Pandoc. Choose a source "
                    "file, an output format, and where to save the result."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        # --- Source file ---
        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_label = wx.StaticText(self.dialog, label=_("&Source file"))
        self.source_field = wx.TextCtrl(self.dialog)
        self.source_field.SetName(_("Source file path"))
        browse_source = wx.Button(self.dialog, label=_("Bro&wse..."))
        source_row.Add(source_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        source_row.Add(self.source_field, 1, wx.RIGHT | wx.EXPAND, 8)
        source_row.Add(browse_source, 0)
        root.Add(source_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        # --- Output format ---
        format_row = wx.BoxSizer(wx.HORIZONTAL)
        format_label = wx.StaticText(self.dialog, label=_("Output &format"))
        self.format_choice = wx.Choice(self.dialog)
        self.format_choice.SetName(_("Output format"))
        format_row.Add(format_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        format_row.Add(self.format_choice, 1, wx.EXPAND)
        root.Add(format_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        self.all_formats_check = wx.CheckBox(self.dialog, label=_("Show &all Pandoc formats"))
        self.all_formats_check.SetName(_("Show all Pandoc formats"))
        root.Add(self.all_formats_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Output folder ---
        out_row = wx.BoxSizer(wx.HORIZONTAL)
        out_label = wx.StaticText(self.dialog, label=_("Output f&older"))
        self.output_field = wx.TextCtrl(self.dialog)
        self.output_field.SetName(_("Output folder path"))
        browse_output = wx.Button(self.dialog, label=_("Br&owse..."))
        out_row.Add(out_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        out_row.Add(self.output_field, 1, wx.RIGHT | wx.EXPAND, 8)
        out_row.Add(browse_output, 0)
        root.Add(out_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        self.validation_text = wx.StaticText(self.dialog, label="")
        self.validation_text.SetName(_("Convert File status"))
        root.Add(self.validation_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        # --- Buttons ---
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.convert_button = wx.Button(self.dialog, id=wx.ID_OK, label=_("&Convert File"))
        self.open_button = wx.Button(
            self.dialog, id=ID_CONVERT_AND_OPEN, label=_("Convert and O&pen")
        )
        cancel_button = wx.Button(self.dialog, id=wx.ID_CANCEL, label=_("Cancel"))
        buttons.AddStretchSpacer(1)
        buttons.Add(self.convert_button, 0, wx.RIGHT, 6)
        buttons.Add(self.open_button, 0, wx.RIGHT, 6)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        # State filled in by submit().
        self._result: ConvertRequest | None = None

        # Initial population and defaults.
        self._populate_formats(default_format)
        if default_output_dir and Path(default_output_dir).is_dir():
            self.output_field.SetValue(default_output_dir)

        browse_source.Bind(wx.EVT_BUTTON, lambda _e: self._browse_source())
        browse_output.Bind(wx.EVT_BUTTON, lambda _e: self._browse_output())
        self.all_formats_check.Bind(wx.EVT_CHECKBOX, lambda _e: self._on_toggle_all_formats())
        self.format_choice.Bind(wx.EVT_CHOICE, lambda _e: self._sync_open_button())
        self.convert_button.Bind(wx.EVT_BUTTON, lambda _e: self._submit("save"))
        self.open_button.Bind(wx.EVT_BUTTON, lambda _e: self._submit("open"))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))

        self._sync_open_button()
        self.source_field.SetFocus()

    # -- population ---------------------------------------------------------

    def _populate_formats(self, select_token: str) -> None:
        """Fill the format choice with the curated or full list, keeping selection."""

        if self.all_formats_check.GetValue():
            tokens = convert_formats.runtime_output_formats()
            if not tokens:
                # Probe failed or Pandoc is gone; fall back to curated.
                tokens = [f.token for f in convert_formats.CURATED_OUTPUTS]
        else:
            tokens = [f.token for f in convert_formats.CURATED_OUTPUTS]

        self._tokens = tokens
        labels = [convert_formats.label_for(t) for t in tokens]
        self.format_choice.Set(labels)
        index = tokens.index(select_token) if select_token in tokens else 0
        if labels:
            self.format_choice.SetSelection(index)
        self._sync_open_button()

    def _current_token(self) -> str | None:
        sel = self.format_choice.GetSelection()
        if 0 <= sel < len(self._tokens):
            return self._tokens[sel]
        return None

    def _sync_open_button(self) -> None:
        """Enable Convert and Open only for text outputs QUILL can edit."""

        token = self._current_token()
        self.open_button.Enable(token is not None and convert_formats.is_text_output(token))

    def _on_toggle_all_formats(self) -> None:
        keep = self._current_token() or "gfm"
        self._populate_formats(keep)

    # -- browse helpers -----------------------------------------------------

    def _browse_source(self) -> None:
        with wx.FileDialog(
            self.dialog,
            _("Choose a file to convert"),
            wildcard=convert_formats.input_wildcard(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dialog:
            if self._show_modal_fn(file_dialog, _("Convert File — Source")) == wx.ID_OK:
                path = file_dialog.GetPath()
                self.source_field.SetValue(path)
                self.validation_text.SetLabel("")
                # Default the output folder to the source folder the first time.
                if not self.output_field.GetValue().strip():
                    self.output_field.SetValue(str(Path(path).parent))

    def _browse_output(self) -> None:
        start = self.output_field.GetValue().strip()
        with wx.DirDialog(
            self.dialog,
            _("Choose an output folder"),
            defaultPath=start if start and Path(start).is_dir() else "",
            style=wx.DD_DEFAULT_STYLE,
        ) as dir_dialog:
            if self._show_modal_fn(dir_dialog, _("Convert File — Output Folder")) == wx.ID_OK:
                self.output_field.SetValue(dir_dialog.GetPath())
                self.validation_text.SetLabel("")

    # -- submit -------------------------------------------------------------

    def _submit(self, action: str) -> None:
        raw_source = self.source_field.GetValue().strip()
        if not raw_source:
            self._fail(_("Choose a source file before converting."), self.source_field)
            return
        source = Path(raw_source)
        if not source.is_file():
            self._fail(_("The selected source file was not found."), self.source_field)
            return

        token = self._current_token()
        if token is None:
            self._fail(_("Choose an output format before converting."), self.format_choice)
            return

        raw_output = self.output_field.GetValue().strip()
        if not raw_output:
            self._fail(_("Choose an output folder before converting."), self.output_field)
            return
        output_dir = Path(raw_output)
        if not output_dir.is_dir():
            self._fail(_("The output folder does not exist."), self.output_field)
            return

        self._result = ConvertRequest(
            source_path=source,
            output_token=token,
            output_dir=output_dir,
            action=action,
        )
        self.dialog.EndModal(wx.ID_OK if action == "save" else ID_CONVERT_AND_OPEN)

    def _fail(self, message: str, focus_target: wx.Window) -> None:
        self.validation_text.SetLabel(message)
        focus_target.SetFocus()

    # -- public -------------------------------------------------------------

    def prompt(self) -> ConvertRequest | None:
        """Show the dialog modally and return the request, or ``None`` if cancelled."""

        try:
            result = self._show_modal_fn(self.dialog, _("Convert File"))
            if result in (wx.ID_OK, ID_CONVERT_AND_OPEN):
                return self._result
            return None
        finally:
            self.dialog.Destroy()


__all__ = ["ConvertFileDialog", "ConvertRequest", "ID_CONVERT_AND_OPEN"]
