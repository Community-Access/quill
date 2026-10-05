"""Convert File on QUILL's main window (qc.md F-08, extracted 2026-10-03).

One operation from start to finish: the file and format chooser, the engine
choice between Pandoc and MarkItDown, the offer to fetch Pandoc when it is
missing, the conversion on the task pool, and the remembered folder and format
for next time. It was a contiguous block of ``MainFrame``; the host contract is
unchanged (``self.settings``, ``self._wx``, ``self._task_manager``,
``self._announce``).
"""

from __future__ import annotations

from pathlib import Path

from quill.core.external_tools import copyable_install_command, get_external_tool_status
from quill.core.settings import save_settings
from quill.io.pandoc import PandocConversionError, PandocUnavailableError, convert_file_with_pandoc


class ConvertFileMixin:
    """File > Convert File, and the Pandoc offer it can lead to; mixed into MainFrame."""

    def _convert_file_default_output_dir(self) -> str:
        """Best initial output folder for the Convert File dialog.

        Priority: the folder remembered from the last conversion, then the
        general file-dialog default directory.
        """

        remembered = getattr(self.settings, "convert_file_last_output_dir", "")
        if remembered and Path(remembered).is_dir():
            return remembered
        return self._file_dialog_default_dir()

    def _remember_convert_file_choices(self, output_dir: Path, output_token: str) -> None:
        """Persist the Convert File output folder and format for next time."""

        self.settings.convert_file_last_output_dir = str(output_dir)
        self.settings.convert_file_last_format = output_token
        save_settings(self.settings)

    def _offer_pandoc_download(self, feature: str) -> bool:
        """When a feature needs Pandoc and it isn't present, offer the on-demand
        download (footprint unbundle). Returns True if the user started it.

        On Windows QUILL fetches the official pinned build; elsewhere it points
        the user at their package manager. Either way the conversion is retried
        by the user once Pandoc is ready.
        """
        wx = self._wx
        from quill.core.pandoc_install import pandoc_install_supported

        if pandoc_install_supported():
            result = self._show_message_box(
                (
                    f"{feature} needs Pandoc, which is downloaded on demand to keep "
                    "QUILL's install small. Download the official Pandoc build now "
                    "(about 45 MB)? It is verified and installed automatically."
                ),
                feature,
                wx.ICON_INFORMATION | wx.YES_NO,
            )
            if result == wx.YES:
                self.download_pandoc()
                return True
            # Declining must not look like the command silently did nothing
            # (#798 review): leave a status explaining why it stopped.
            self._set_status(f"{feature} needs Pandoc; nothing was done.")
            return False
        result = self._show_message_box(
            (
                f"{feature} needs Pandoc. Install it with your package manager "
                "(for example: brew install pandoc), then try again. Copy the "
                "install command now?"
            ),
            feature,
            wx.ICON_INFORMATION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result == wx.YES and self._copy_to_clipboard(copyable_install_command("pandoc")):
            self._set_status("Copied Pandoc install command")
        else:
            self._set_status(f"{feature} needs Pandoc; nothing was done.")
        return False

    #: Sources MarkItDown can read and the Markdown-ish outputs it can produce.
    _MARKITDOWN_SOURCE_SUFFIXES = frozenset({".docx", ".pptx", ".xlsx", ".xls", ".pdf"})
    _MARKITDOWN_OUTPUT_TOKENS = frozenset({"gfm", "commonmark", "markdown", "plain"})

    @classmethod
    def _markitdown_convert_applies(cls, request: object) -> bool:
        """Whether the MarkItDown engine can honestly serve this conversion.

        MarkItDown is a one-way reader: Office/PDF in, Markdown out. Anything
        else must go to Pandoc, and the caller says so instead of silently
        substituting an engine the user did not pick.
        """
        source = Path(getattr(request, "source_path", ""))
        token = str(getattr(request, "output_token", ""))
        return (
            source.suffix.lower() in cls._MARKITDOWN_SOURCE_SUFFIXES
            and token in cls._MARKITDOWN_OUTPUT_TOKENS
        )

    def convert_file(self) -> None:
        """File > Convert File: convert any document to another format via Pandoc."""

        wx = self._wx
        status = get_external_tool_status("pandoc")
        if not status.installed:
            if self._offer_pandoc_download("Convert File"):
                # Download runs in the background; the user re-runs Convert File
                # once Pandoc is ready (the status announcement tells them so).
                return
            self._set_status("Convert File unavailable until Pandoc is installed")
            return

        from quill.core import convert_formats
        from quill.ui.convert_file_dialog import ConvertFileDialog

        dialog = ConvertFileDialog(
            self.frame,
            default_output_dir=self._convert_file_default_output_dir(),
            default_format=getattr(self.settings, "convert_file_last_format", "gfm") or "gfm",
            show_modal_fn=self._show_modal_dialog,
        )
        request = dialog.prompt()
        if request is None:
            self._set_status("Convert File cancelled")
            return

        target = request.output_path
        if target.exists():
            confirm = self._show_message_box(
                f"{target.name} already exists in that folder. Replace it?",
                "Convert File",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            if confirm != wx.YES:
                self._set_status("Convert File cancelled (file already exists)")
                return

        # Braille sources take QUILL's own path: Pandoc has no braille reader,
        # but the auto-detecting back-translation (braille_detect) does exactly
        # this job -- detect the code, back-translate, write the chosen format.
        if request.source_path.suffix.lower() in convert_formats.BRAILLE_INPUT_SUFFIXES:
            self._convert_brf_file_request(request, target)
            return

        engine = getattr(request, "engine", "auto")
        if engine == "markitdown" and not self._markitdown_convert_applies(request):
            proceed = self._show_message_box(
                "MarkItDown reads Word, PowerPoint, Excel, or PDF into Markdown "
                "or plain text only. Convert with Pandoc instead?",
                "Convert File",
                wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
            )
            if proceed != wx.YES:
                self._set_status("Convert File cancelled")
                return
            engine = "pandoc"

        if engine == "markitdown":
            self._set_status(f"Converting {request.source_path.name} with MarkItDown...")
            try:
                from quill.io.markitdown_bridge import convert_with_markitdown

                text = convert_with_markitdown(request.source_path)
                with target.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            except (ImportError, ValueError, RuntimeError, OSError) as error:
                self._show_message_box(
                    f"Conversion failed: {error}",
                    "Convert File",
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Conversion failed")
                return
        else:
            from_format = convert_formats.reader_for_path(str(request.source_path))
            self._set_status(
                f"Converting {request.source_path.name} to "
                f"{convert_formats.label_for(request.output_token)}..."
            )
            try:
                convert_file_with_pandoc(
                    request.source_path,
                    target,
                    from_format=from_format,
                    to_format=request.output_token,
                    tool_status=status,
                    resolve_writer=False,
                )
            except (PandocUnavailableError, PandocConversionError, ValueError) as error:
                self._show_message_box(
                    f"Conversion failed: {error}",
                    "Convert File",
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Conversion failed")
                return

        self._remember_convert_file_choices(request.output_dir, request.output_token)
        self._record_recent(target)
        self._announce(f"Converted to {target.name}")

        if request.action == "open":
            self.open_file(path=target)
            self._set_status(f"Converted and opened {target.name}")
            return

        # Convert File (save) action: offer to open the result when it is a
        # text format QUILL can edit; binary outputs just land on disk.
        if convert_formats.is_text_output(request.output_token):
            if (
                self._show_message_box(
                    f"Conversion complete. Open {target.name} now?",
                    "Convert File",
                    wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
                )
                == wx.YES
            ):
                self.open_file(path=target)
        self._set_status(f"Converted to {target}")

    # Backwards-compatible alias: the External Tools dialog re-opens the
    # conversion UI after a successful Pandoc install.
    def open_pandoc_wizard(self) -> None:
        self.convert_file()
