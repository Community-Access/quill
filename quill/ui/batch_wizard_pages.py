"""Batch Conversion wizard pages (issue #262).

A four-page hand-rolled wizard modeled on :mod:`quill.ui.setup_wizard_pages`:

1. ``_IntroPage`` explains what the wizard does. Live Pandoc-version probe
   greys out Start when Pandoc is not detected.
2. ``_FolderPage`` lets the user pick a folder, the recursive toggle, the
   output-layout choice, and the overwrite policy. Defaults come from
   ``Settings`` (``settings.import_export_*``).
3. ``_FormatPage`` lets the user pick direction (import vs export) plus a
   Tier-1 source format, Tier-1 target format, and an optional conversion
   profile.
4. ``_SummaryPage`` shows a human-readable summary and a Start button.

All choices stay on the dialog until Start is clicked; ``build_request``
returns the :class:`BatchRequest` only when validation passes.

Pure UI; pure logic lives in :mod:`quill.core.batch_convert`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import wx

from quill.core import convert_profiles, pandoc_formats
from quill.core.batch_convert import (
    BatchPlan,
    OutputLayout,
    OverwritePolicy,
)
from quill.core.i18n import _, lazy_gettext
from quill.core.settings import Settings
from quill.ui.batch_wizard import BatchRequest
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class _WizardPage(wx.Panel):
    """Base for all batch-wizard page panels."""

    def __init__(self, parent: wx.Window, name: str) -> None:
        super().__init__(parent)
        self.SetName(name)


# ---------------------------------------------------------------------------
# Shared state carried through the wizard
# ---------------------------------------------------------------------------


@dataclass
class _WizardChoices:
    """Mutable container that pages read and write."""

    root: Path
    recursive: bool
    output_layout: OutputLayout
    overwrite: OverwritePolicy
    direction: str  # "import" or "export"
    source_format: str
    target_format: str
    profile: str | None


# ---------------------------------------------------------------------------
# Page 1 - Intro
# ---------------------------------------------------------------------------


class _IntroPage(_WizardPage):
    _PREVIEW = lazy_gettext(
        "The Batch Conversion wizard converts every matching file in a folder\n"
        "you pick, using Pandoc.\n"
        "\n"
        "Supported input formats: Markdown, CommonMark, GitHub-Flavored Markdown,\n"
        "HTML, Word documents, OpenDocument Text, Rich Text Format, plain text,\n"
        "CSV / TSV tables, EPUB books, and LaTeX.\n"
        "\n"
        "Supported output formats: the same set plus PDF (export only).\n"
        "\n"
        "The conversion runs on a background thread. You can keep working in\n"
        "QUILL while it runs, and progress appears in the Status Page\n"
        "(Help menu).\n"
        "\n"
        "Press Next to choose a folder."
    )

    def __init__(
        self, parent: wx.Window, settings: Settings, announce: Callable[[str], None] | None
    ) -> None:
        super().__init__(parent, "Batch Wizard - Intro")
        self._settings = settings
        self._announce = announce

        sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self, label=_("Batch Conversion"), name="batch_wizard.intro_heading"
        )
        heading.SetFont(heading.GetFont().Scaled(1.3).Bold())
        sizer.Add(heading, flag=wx.ALL, border=12)

        sizer.Add(
            wx.StaticText(
                self, label=_("About this wizard:"), name="batch_wizard.intro_about_label"
            ),
            flag=wx.LEFT | wx.RIGHT,
            border=12,
        )

        preview = wx.TextCtrl(
            self,
            value=str(self._PREVIEW),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            name="batch_wizard.intro_preview",
        )
        preview.SetMinSize((-1, 220))
        sizer.Add(preview, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        # Live Pandoc version status. We probe synchronously here because the
        # probe is sub-second; the wizard intro is short enough that the
        # delay is not user-visible.
        version = pandoc_formats.probe_pandoc_version()
        if version:
            status = _("Pandoc detected: {version}").format(version=version)
        else:
            status = _(
                "Pandoc was not detected on this computer. "
                "Install Pandoc 3.x from https://pandoc.org to use batch conversion."
            )
        self._status = wx.StaticText(self, label=status, name="batch_wizard.intro_pandoc_status")
        sizer.Add(self._status, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self.SetSizer(sizer)

    def collect(self, _choices: _WizardChoices) -> None:
        pass

    def pandoc_available(self) -> bool:
        return pandoc_formats.probe_pandoc_version() is not None


# ---------------------------------------------------------------------------
# Page 2 - Folder + options
# ---------------------------------------------------------------------------


_OVERWRITE_LABELS: tuple[tuple[OverwritePolicy, str], ...] = (
    ("ask", "Ask each time"),
    ("never", "Never overwrite"),
    ("always", "Always overwrite"),
)
_OUTPUT_LAYOUT_LABELS: tuple[tuple[OutputLayout, str], ...] = (
    ("subfolder", "Output subfolder per source folder"),
    ("same_folder", "Same folder as source"),
)


class _FolderPage(_WizardPage):
    def __init__(self, parent: wx.Window, settings: Settings) -> None:
        super().__init__(parent, "Batch Wizard - Folder")
        self._settings = settings

        sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self, label=_("Folder and options"), name="batch_wizard.folder_heading"
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        sizer.Add(heading, flag=wx.ALL, border=12)

        # wx.DirPickerCtrl + the surrounding label row, mirroring the
        # _prompt_file_search pattern (main_frame.py:18832).
        picker_row = wx.BoxSizer(wx.HORIZONTAL)
        picker_label = wx.StaticText(
            self, label=_("Source folder:"), name="batch_wizard.folder_label"
        )
        picker_row.Add(picker_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=8)
        default_path = settings.import_export_last_folder or ""
        self._folder_picker = wx.DirPickerCtrl(
            self,
            path=default_path,
            message=_("Choose the folder to convert"),
            style=wx.DIRP_DEFAULT_STYLE | wx.DIRP_DIR_MUST_EXIST,
            name="batch_wizard.folder_picker",
        )
        picker_row.Add(self._folder_picker, proportion=1, flag=wx.EXPAND)
        sizer.Add(picker_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        # Recursive checkbox (issue #262).
        self._recursive = wx.CheckBox(
            self,
            label=_("Include subfolders"),
            name="batch_wizard.recursive_checkbox",
        )
        self._recursive.SetValue(settings.import_export_recursive)
        sizer.Add(self._recursive, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        # Output layout (issue #262: same folder or Output/ subfolder).
        layout_choices = [label for _value, label in _OUTPUT_LAYOUT_LABELS]
        self._output_layout = wx.RadioBox(
            self,
            label=_("Where to put converted files"),
            choices=layout_choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name="batch_wizard.output_layout",
        )
        current_layout = settings.import_export_output_layout
        for idx, (value, _label) in enumerate(_OUTPUT_LAYOUT_LABELS):
            if value == current_layout:
                self._output_layout.SetSelection(idx)
                break
        else:
            self._output_layout.SetSelection(0)
        sizer.Add(self._output_layout, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        # Overwrite (issue #262: never / ask / always).
        overwrite_choices = [label for _value, label in _OVERWRITE_LABELS]
        self._overwrite = wx.RadioBox(
            self,
            label=_("When an output file already exists"),
            choices=overwrite_choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name="batch_wizard.overwrite_policy",
        )
        current_overwrite = settings.import_export_overwrite
        for idx, (value, _label) in enumerate(_OVERWRITE_LABELS):
            if value == current_overwrite:
                self._overwrite.SetSelection(idx)
                break
        else:
            self._overwrite.SetSelection(0)
        sizer.Add(self._overwrite, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        self.SetSizer(sizer)

    def collect(self, choices: _WizardChoices) -> None:
        path_text = self._folder_picker.GetPath().strip()
        choices.root = Path(path_text) if path_text else Path(".")
        choices.recursive = bool(self._recursive.GetValue())
        layout_idx = self._output_layout.GetSelection()
        choices.output_layout = (
            _OUTPUT_LAYOUT_LABELS[layout_idx][0] if layout_idx >= 0 else "subfolder"
        )
        overwrite_idx = self._overwrite.GetSelection()
        choices.overwrite = _OVERWRITE_LABELS[overwrite_idx][0] if overwrite_idx >= 0 else "ask"

    def is_valid(self) -> tuple[bool, str]:
        path_text = self._folder_picker.GetPath().strip()
        if not path_text:
            return False, _("Please choose a folder first.")
        path = Path(path_text)
        if not path.is_dir():
            return False, _("That path is not a folder.")
        return True, ""


# ---------------------------------------------------------------------------
# Page 3 - Format + profile
# ---------------------------------------------------------------------------


class _FormatPage(_WizardPage):
    def __init__(self, parent: wx.Window, settings: Settings) -> None:
        super().__init__(parent, "Batch Wizard - Format")
        self._settings = settings

        sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self, label=_("Format and profile"), name="batch_wizard.format_heading"
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        sizer.Add(heading, flag=wx.ALL, border=12)

        # Direction (import vs export).
        self._direction = wx.RadioBox(
            self,
            label=_("Direction"),
            choices=(
                _("Import into QUILL (convert to Markdown)"),
                _("Export from QUILL (convert from Markdown)"),
            ),
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name="batch_wizard.direction",
        )
        self._direction.SetSelection(1)  # default to export (Markdown is QUILL's native format)
        sizer.Add(self._direction, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        # Source format.
        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_row.Add(
            wx.StaticText(self, label=_("Source format:"), name="batch_wizard.source_label"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=8,
        )
        self._source_choice = wx.Choice(self, name="batch_wizard.source_choice")
        source_row.Add(self._source_choice, proportion=1, flag=wx.EXPAND)
        sizer.Add(source_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        # Target format.
        target_row = wx.BoxSizer(wx.HORIZONTAL)
        target_row.Add(
            wx.StaticText(self, label=_("Target format:"), name="batch_wizard.target_label"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=8,
        )
        self._target_choice = wx.Choice(self, name="batch_wizard.target_choice")
        target_row.Add(self._target_choice, proportion=1, flag=wx.EXPAND)
        sizer.Add(target_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        # Profile picker.
        profile_row = wx.BoxSizer(wx.HORIZONTAL)
        profile_row.Add(
            wx.StaticText(self, label=_("Profile:"), name="batch_wizard.profile_label"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=8,
        )
        self._profile_choice = wx.Choice(self, name="batch_wizard.profile_choice")
        profile_row.Add(self._profile_choice, proportion=1, flag=wx.EXPAND)
        sizer.Add(profile_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        # Populate from the initial direction (export).
        self._populate_format_choices("export")

        self._direction.Bind(wx.EVT_RADIOBOX, self._on_direction_change)
        self.SetSizer(sizer)

    def _populate_format_choices(self, direction: str) -> None:
        formats = pandoc_formats.formats_for_direction(direction)
        # For direction=export the source is QUILL's Markdown; for direction=import
        # the target is QUILL's Markdown.
        self._source_choice.Clear()
        self._target_choice.Clear()
        for fmt in formats:
            if direction == "import":
                # Source = user's file format. Target = QUILL's GFM.
                self._source_choice.Append(fmt.display_name, clientData=fmt.name)
            else:
                # Source = QUILL's GFM. Target = user's chosen output format.
                self._target_choice.Append(fmt.display_name, clientData=fmt.name)
        if direction == "import":
            # Target is fixed to GFM (closest match to QUILL's editor).
            self._gfm_index = 0
            self._target_choice.Append("GitHub-Flavored Markdown", clientData="gfm")
            self._target_choice.SetSelection(0)
            if self._source_choice.GetCount() > 0:
                self._source_choice.SetSelection(0)
        else:
            # Source is fixed to GFM.
            self._source_choice.Append("GitHub-Flavored Markdown", clientData="gfm")
            self._source_choice.SetSelection(0)
            if self._target_choice.GetCount() > 0:
                self._target_choice.SetSelection(0)

        # Profile picker: always present, populated from convert_profiles.PROFILES.
        self._profile_choice.Clear()
        self._profile_choice.Append("(no profile)", clientData=None)
        for profile in convert_profiles.PROFILES:
            self._profile_choice.Append(profile.label, clientData=profile.name)
        self._profile_choice.SetSelection(0)

    def _on_direction_change(self, _event: wx.Event) -> None:
        direction = "import" if self._direction.GetSelection() == 0 else "export"
        self._populate_format_choices(direction)

    def collect(self, choices: _WizardChoices) -> None:
        direction = "import" if self._direction.GetSelection() == 0 else "export"
        choices.direction = direction
        if direction == "import":
            src = self._source_choice.GetClientData(self._source_choice.GetSelection())
            choices.source_format = src if isinstance(src, str) else "markdown"
            choices.target_format = "gfm"
        else:
            choices.source_format = "gfm"
            tgt = self._target_choice.GetClientData(self._target_choice.GetSelection())
            choices.target_format = tgt if isinstance(tgt, str) else "html"
        profile_data = self._profile_choice.GetClientData(self._profile_choice.GetSelection())
        choices.profile = profile_data if isinstance(profile_data, str) else None


# ---------------------------------------------------------------------------
# Page 4 - Summary
# ---------------------------------------------------------------------------


class _SummaryPage(_WizardPage):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, "Batch Wizard - Summary")
        sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self, label=_("Review and start"), name="batch_wizard.summary_heading"
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        sizer.Add(heading, flag=wx.ALL, border=12)

        self._summary_text = wx.TextCtrl(
            self,
            value="",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            name="batch_wizard.summary_text",
        )
        self._summary_text.SetMinSize((-1, 200))
        sizer.Add(self._summary_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        self.SetSizer(sizer)

    def refresh(self, choices: _WizardChoices) -> None:
        source_label = pandoc_formats.get_format(choices.source_format)
        target_label = pandoc_formats.get_format(choices.target_format)
        profile_label = "(no profile)"
        if choices.profile:
            for p in convert_profiles.PROFILES:
                if p.name == choices.profile:
                    profile_label = p.label
                    break
        lines = [
            _("Source folder: {folder}").format(folder=str(choices.root)),
            _("Recurse into subfolders: {value}").format(
                value=_("Yes") if choices.recursive else _("No")
            ),
            _("Direction: {value}").format(
                value=_("Import") if choices.direction == "import" else _("Export")
            ),
            _("Source format: {value}").format(
                value=source_label.display_name if source_label else choices.source_format
            ),
            _("Target format: {value}").format(
                value=target_label.display_name if target_label else choices.target_format
            ),
            _("Profile: {value}").format(value=profile_label),
            _("Output layout: {value}").format(
                value=_("Output subfolder per source folder")
                if choices.output_layout == "subfolder"
                else _("Same folder as source")
            ),
            _("Overwrite: {value}").format(
                value={
                    "ask": _("Ask each time"),
                    "never": _("Never overwrite"),
                    "always": _("Always overwrite"),
                }.get(choices.overwrite, choices.overwrite)
            ),
            "",
            _("Press Start to begin. Progress appears in Help > Status Page."),
        ]
        self._summary_text.SetValue("\n".join(lines))

    def collect(self, _choices: _WizardChoices) -> None:
        pass


# ---------------------------------------------------------------------------
# Host dialog
# ---------------------------------------------------------------------------


_PAGE_TITLES: tuple[str, ...] = (
    "Introduction",
    "Folder and options",
    "Format and profile",
    "Review and start",
)


class BatchWizardDialog(wx.Dialog):
    """The wizard host: a wx.Dialog with stacked page panels and Back/Next/Start/Cancel."""

    _PAGE_COUNT: ClassVar[int] = 4

    def __init__(
        self,
        parent: wx.Window,
        settings: Settings,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, title=str(_("Batch Conversion")), name="batch_wizard.dialog")
        self._settings = settings
        self._announce_cb = announce_cb
        self._current_idx = -1

        # Default choices (will be refined by pages).
        self._choices = _WizardChoices(
            root=Path(settings.import_export_last_folder or "."),
            recursive=settings.import_export_recursive,
            output_layout=settings.import_export_output_layout,
            overwrite=settings.import_export_overwrite,
            direction="export",
            source_format="gfm",
            target_format="html",
            profile=None,
        )

        self._intro = _IntroPage(self, settings, announce_cb)
        self._folder = _FolderPage(self, settings)
        self._format = _FormatPage(self, settings)
        self._summary = _SummaryPage(self)
        self._all_pages = [self._intro, self._folder, self._format, self._summary]

        self._build_ui()
        self._show_page(0)

        self.SetMinSize((620, 540))
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.Bind(wx.EVT_INIT_DIALOG, lambda _e: wx.CallAfter(self._focus_first_page_control))

    # -- navigation ---------------------------------------------------------

    def _build_ui(self) -> None:
        outer = wx.BoxSizer(wx.VERTICAL)

        self._page_container = wx.BoxSizer(wx.VERTICAL)
        for page in self._all_pages:
            self._page_container.Add(page, proportion=1, flag=wx.EXPAND)
            page.Hide()
            page.Disable()
        outer.Add(self._page_container, proportion=1, flag=wx.EXPAND | wx.ALL, border=4)
        outer.Add(wx.StaticLine(self), flag=wx.EXPAND)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        self._progress = wx.StaticText(self, name="batch_wizard.progress_label")
        nav.Add(self._progress, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=8)
        nav.AddStretchSpacer()

        self._back_btn = wx.Button(self, label=_("< Back"), name="batch_wizard.back")
        self._next_btn = wx.Button(self, label=_("Next >"), name="batch_wizard.next")
        self._start_btn = wx.Button(self, wx.ID_OK, label=_("Start"), name="batch_wizard.start")
        self._cancel_btn = wx.Button(
            self, wx.ID_CANCEL, label=_("Cancel"), name="batch_wizard.cancel"
        )

        nav.Add(self._back_btn, flag=wx.LEFT, border=4)
        nav.Add(self._next_btn, flag=wx.LEFT, border=4)
        nav.Add(self._start_btn, flag=wx.LEFT, border=4)
        nav.Add(self._cancel_btn, flag=wx.LEFT | wx.RIGHT, border=8)

        outer.Add(nav, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=8)

        self._back_btn.Bind(wx.EVT_BUTTON, self._on_back)
        self._next_btn.Bind(wx.EVT_BUTTON, self._on_next)
        self._start_btn.Bind(wx.EVT_BUTTON, self._on_start)
        self.Bind(wx.EVT_BUTTON, self._on_dismiss, id=wx.ID_CANCEL)

        self.SetSizer(outer)

    def _show_page(self, idx: int) -> None:
        if 0 <= self._current_idx < len(self._all_pages):
            old = self._all_pages[self._current_idx]
            old.Hide()
            old.Disable()

        self._current_idx = idx
        page = self._all_pages[idx]
        page.Enable()
        page.Show()
        self.Layout()

        total = len(self._all_pages)
        self._progress.SetLabel(_("Step {step} of {total}").format(step=idx + 1, total=total))
        self._back_btn.Enable(idx > 0)
        self._next_btn.Show(idx < total - 1)
        self._start_btn.Show(idx == total - 1)

        title = _PAGE_TITLES[idx] if idx < self._PAGE_COUNT - 1 else "Review and start"
        if self._announce_cb is not None:
            self._announce_cb(f"Step {idx + 1} of {total}: {title}")

    def _focus_first_page_control(self) -> None:
        try:
            self._all_pages[self._current_idx].SetFocus()
        except Exception:  # noqa: BLE001 - safe focus fallback
            _log.exception("Batch wizard failed to set initial focus")

    # -- collect from the current page and validate -------------------------

    def _collect_current(self) -> tuple[bool, str]:
        page = self._all_pages[self._current_idx]
        page.collect(self._choices)
        if isinstance(page, _FolderPage):
            return page.is_valid()
        return True, ""

    def _on_back(self, _event: wx.Event) -> None:
        if self._current_idx <= 0:
            return
        self._collect_current()  # keep choices up to date even when going back
        self._show_page(self._current_idx - 1)

    def _on_next(self, _event: wx.Event) -> None:
        valid, message = self._collect_current()
        if not valid:
            show_message_box(message, _("Please complete this step"), wx.ICON_INFORMATION)
            return
        if self._current_idx >= len(self._all_pages) - 1:
            return
        next_idx = self._current_idx + 1
        # Refresh the summary page right before showing it.
        if next_idx == len(self._all_pages) - 1:
            self._summary.refresh(self._choices)
        # Disable Start on the intro page when Pandoc is missing.
        if self._current_idx == 0 and not self._intro.pandoc_available():
            show_message_box(
                _(
                    "Pandoc was not detected on this computer. "
                    "Install Pandoc 3.x from https://pandoc.org and try again."
                ),
                _("Pandoc not found"),
                wx.ICON_INFORMATION,
            )
            return
        self._show_page(next_idx)

    def _on_start(self, _event: wx.Event) -> None:
        valid, message = self._collect_current()
        if not valid:
            show_message_box(message, _("Please complete this step"), wx.ICON_INFORMATION)
            return
        # Persist the last-used folder for next time. We do not mutate the
        # other settings; the user can change defaults in Preferences.
        try:
            self._settings.import_export_last_folder = str(self._choices.root)
        except Exception:  # noqa: BLE001 - settings persistence is best-effort here
            _log.exception("Failed to remember last batch folder")
        self.EndModal(wx.ID_OK)

    def _on_dismiss(self, _event: wx.Event) -> None:
        self.EndModal(wx.ID_CANCEL)

    # -- output -------------------------------------------------------------

    def build_request(self) -> BatchRequest:
        plan = BatchPlan(
            root=self._choices.root,
            recursive=self._choices.recursive,
            source_format=self._choices.source_format,
            target_format=self._choices.target_format,
            output_layout=self._choices.output_layout,
            overwrite=self._choices.overwrite,
            profile=self._choices.profile,
        )
        return BatchRequest(plan=plan)


__all__ = [
    "BatchWizardDialog",
    "BatchRequest",
]
