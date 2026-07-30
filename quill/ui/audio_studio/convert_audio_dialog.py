"""Universal Audio Converter dialog + orchestration (#1255 v1, Basic mode).

A screen-reader-first ``wx.Dialog`` for building a mixed file/folder conversion
queue, choosing an output format + preset + destination folder, and running the
conversion **off the UI thread** with multiple workers, a determinate progress
dialog, cancellation, and a spoken summary. The heavy lifting is the tested,
wx-free ``quill.core.audio.convert`` engine; this module is thin UI + wiring.

Mirrors the house dialog contract (``play_queue_dialog`` / the guided pickers):
every control is parented on the dialog and named, the queue is a sanctioned
reorderable ``wx.ListBox`` (never a ``CheckListBox``), Delete removes a row,
rows carry state tags in words, and ``apply_modal_ids`` backs a real Convert /
Cancel pair (WCAG 2.1.2). Basic mode only in v1; Advanced DSP + the standalone
app frame layer on this later without changing the engine.

The request-building (:func:`build_request`) and the plan/run orchestration
(:func:`plan_and_run`) are wx-free and unit-tested; the dialog is a thin shell
that collects widgets into a :class:`ConvertRequest` and hands it off.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.audio.convert import (
    ConversionSpec,
    OnExisting,
    available_output_formats,
    default_destination,
    plan_jobs,
)
from quill.core.audio.presets import DEFAULT_PRESET_ID, preset_choices, preset_spec

_TITLE = "Convert Audio"

# On-conflict choices offered in the dialog: (OnExisting, spoken label).
_CONFLICT_CHOICES: tuple[tuple[OnExisting, str], ...] = (
    (OnExisting.RENAME, "Rename (auto-number) — never overwrites"),
    (OnExisting.SKIP, "Skip files that already exist"),
    (OnExisting.OVERWRITE, "Overwrite existing files"),
)

# File-open wildcard for "Add files" — audio + video containers (§3).
_ADD_WILDCARD = (
    "Audio and video files|*.mp3;*.wav;*.flac;*.ogg;*.oga;*.opus;*.m4a;*.m4b;*.aac;"
    "*.wma;*.aiff;*.aif;*.alac;*.ape;*.wv;*.mka;*.amr;*.3gp;*.caf;"
    "*.mp4;*.m4v;*.mkv;*.mov;*.webm;*.avi;*.flv;*.wmv|All files (*.*)|*.*"
)


@dataclass(frozen=True, slots=True)
class ConvertRequest:
    """The resolved user choices from the dialog, ready for :func:`plan_and_run`.

    ``queue`` is the list of ``(entry, root)`` pairs plan_jobs expects: a file
    (root ``None``) or a folder (root = itself, for source-tree mirroring).
    """

    queue: list[tuple[Path, Path | None]]
    dest_dir: Path
    spec: ConversionSpec
    recurse: bool
    on_existing: OnExisting
    flatten: bool = False


def build_request(
    entries: list[tuple[Path, Path | None]],
    *,
    fmt: str,
    preset_id: str,
    dest_dir: Path,
    recurse: bool,
    on_existing: OnExisting,
    flatten: bool = False,
) -> ConvertRequest | None:
    """Assemble a :class:`ConvertRequest` from raw dialog values (pure).

    Returns ``None`` when the request is not runnable (no inputs or no
    destination), so the caller can report a friendly "nothing to convert"
    rather than start an empty run. The preset supplies the base spec; the
    chosen output format overrides the preset's format.
    """
    if not entries or str(dest_dir).strip() in ("", "."):
        return None
    from dataclasses import replace

    spec = replace(preset_spec(preset_id), fmt=fmt.strip().lower())
    return ConvertRequest(
        queue=list(entries),
        dest_dir=Path(dest_dir),
        spec=spec,
        recurse=recurse,
        on_existing=on_existing,
        flatten=flatten,
    )


def plan_and_run(host: Any, request: ConvertRequest) -> None:
    """Plan jobs from *request* and run the batch off the UI thread (§8).

    Uses the host's ``_run_background_task`` (protected on close) so a long batch
    never owns the window and closing while converting routes through the shared
    confirm. Progress feeds the status bar; the final summary is spoken. wx-free
    logic lives in the engine; this only marshals progress back via the host.
    """
    from quill.core.audio.convert import (
        CancelToken,
        run_conversion_batch,
    )
    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        host._show_message_box(
            "Audio conversion needs FFmpeg. Install it from Help > Download Optional Components.",
            _TITLE,
        )
        return

    jobs, skipped = plan_jobs(
        request.queue,
        request.dest_dir,
        request.spec,
        recurse=request.recurse,
        on_existing=request.on_existing,
        flatten=request.flatten,
    )
    if not jobs:
        host._set_status("Nothing to convert.")
        host._announce("Nothing to convert.")
        return

    total = len(jobs)
    cancel = CancelToken()

    def work(progress: Any) -> Any:
        def on_progress(done: int, total_jobs: int, _job: Any) -> None:
            pct = int(done * 100 / total_jobs) if total_jobs else 100
            host._wx.CallAfter(host._set_status, f"Converting {done}/{total_jobs} ({pct}%)")
            if (
                progress is not None
                and hasattr(progress, "is_cancelled")
                and progress.is_cancelled()
            ):
                cancel.cancel()

        return run_conversion_batch(ffmpeg, jobs, on_progress=on_progress, cancel=cancel)

    def on_success(result: Any) -> None:
        summary = result.summary(total)
        host._set_status(summary)
        host._announce(summary)

    host._run_background_task(
        f"Converting {total} file(s)",
        work,
        on_success,
        notify_on_success=True,
        notify_on_error=True,
        notification_category="audio",
        protect_on_close=True,
    )


def run_audio_conversion(host: Any) -> None:
    """Open the Convert Audio dialog and run the chosen conversion (§9.2).

    The single entry point the Studio menu / command binds to. Resolves ffmpeg,
    filters the format list to what it can encode, shows the accessible dialog,
    and hands a runnable request to :func:`plan_and_run`.
    """
    import wx

    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = find_ffmpeg()
    formats = available_output_formats(ffmpeg)
    dialog = ConvertAudioDialog(host.frame, wx, output_formats=formats)
    try:
        request = dialog.show(host._show_modal_dialog)
    finally:
        # show_modal_dialog only ShowModal()s; the caller owns teardown (A11Y-4).
        dialog.dialog.Destroy()
    if request is None:
        host._set_status("Audio conversion cancelled.")
        return
    plan_and_run(host, request)


class ConvertAudioDialog:
    """Wraps a ``wx.Dialog`` for Basic-mode conversion (thin, accessible shell).

    Composed rather than subclassed so the widget wiring is injectable/testable
    with a fake ``wx``; the real dialog is built in :meth:`_build`.
    """

    def __init__(self, parent: Any, wx: Any, *, output_formats: list[str]) -> None:
        self._wx = wx
        self._parent = parent
        self._formats = output_formats or ["wav"]
        # The queue: (entry path, mirror root or None).
        self._entries: list[tuple[Path, Path | None]] = []
        self.dialog: Any = None
        self._build()

    # -- construction ----------------------------------------------------- #

    def _build(self) -> None:
        wx = self._wx
        from quill.ui.accessible_names import set_accessible_name
        from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

        dlg = wx.Dialog(
            self._parent,
            title=_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.convert_audio",
        )
        self.dialog = dlg
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(dlg, label="&Files to convert:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(dlg, name="Files to convert")
        set_accessible_name(self._list, "Files to convert")
        sizer.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_files_btn = wx.Button(dlg, label="&Add files...")
        self._add_folder_btn = wx.Button(dlg, label="Add f&older...")
        self._remove_btn = wx.Button(dlg, label="&Remove")
        self._recurse = wx.CheckBox(dlg, label="&Include sub-folders")
        self._recurse.SetValue(True)
        set_accessible_name(self._recurse, "Include sub-folders")
        for widget in (self._add_files_btn, self._add_folder_btn, self._remove_btn, self._recurse):
            add_row.Add(widget, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        sizer.Add(add_row, 0, wx.ALL, 8)

        # Convert to / Preset row.
        sizer.Add(wx.StaticText(dlg, label="Con&vert to:"), 0, wx.LEFT | wx.TOP, 8)
        self._format = wx.Choice(dlg, choices=[f.upper() for f in self._formats])
        self._format.SetSelection(0)
        set_accessible_name(self._format, "Convert to format")
        sizer.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        sizer.Add(wx.StaticText(dlg, label="&Preset:"), 0, wx.LEFT | wx.TOP, 8)
        self._preset_ids = [pid for pid, _label in preset_choices()]
        self._preset = wx.Choice(dlg, choices=[label for _pid, label in preset_choices()])
        self._preset.SetSelection(max(0, self._preset_ids.index(DEFAULT_PRESET_ID)))
        set_accessible_name(self._preset, "Preset")
        sizer.Add(self._preset, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Destination folder + conflict policy.
        sizer.Add(wx.StaticText(dlg, label="Output f&older:"), 0, wx.LEFT | wx.TOP, 8)
        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._dest = wx.TextCtrl(dlg)
        set_accessible_name(self._dest, "Output folder")
        self._browse_btn = wx.Button(dlg, label="&Browse...")
        dest_row.Add(self._dest, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        dest_row.Add(self._browse_btn, 0)
        sizer.Add(dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        sizer.Add(wx.StaticText(dlg, label="On &conflict:"), 0, wx.LEFT | wx.TOP, 8)
        self._conflict = wx.Choice(dlg, choices=[label for _policy, label in _CONFLICT_CHOICES])
        self._conflict.SetSelection(0)
        set_accessible_name(self._conflict, "On conflict")
        sizer.Add(self._conflict, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        buttons = dlg.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        dlg.SetSizerAndFit(sizer)

        self._add_files_btn.Bind(wx.EVT_BUTTON, self._on_add_files)
        self._add_folder_btn.Bind(wx.EVT_BUTTON, self._on_add_folder)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self._browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        apply_listbox_activation(self._list, lambda _e: None)
        # Convert is the affirmative; a real Cancel/Escape button (no trap).
        apply_modal_ids(
            dlg, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL, affirmative_label="Convert"
        )

    # -- row + queue helpers ---------------------------------------------- #

    def _row_label(self, entry: Path, root: Path | None) -> str:
        """A spoken row: a folder says how it will be scanned; a file its origin."""
        if root is not None and entry.is_dir():
            scope = "recursive" if self._recurse.GetValue() else "top level only"
            return f"{entry.name} (folder, {scope}) -- {entry}"
        return f"{entry.name} -- {entry}"

    def _reload(self, *, select: int | None = None) -> None:
        self._list.Clear()
        for entry, root in self._entries:
            self._list.Append(self._row_label(entry, root))
        if self._entries:
            target = 0 if select is None else max(0, min(select, len(self._entries) - 1))
            self._list.SetSelection(target)
        else:
            self._add_files_btn.SetFocus()

    def _append(self, entry: Path, root: Path | None) -> None:
        resolved = entry.resolve()
        if any(e.resolve() == resolved for e, _r in self._entries):
            return  # de-dup in the queue view; plan_jobs de-dups the expansion too
        self._entries.append((entry, root))

    # -- events ----------------------------------------------------------- #

    def _on_add_files(self, event: Any) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            message="Add files to convert",
            wildcard=_ADD_WILDCARD,
            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            for path in picker.GetPaths():
                self._append(Path(path), None)
        self._reload(select=len(self._entries) - 1)

    def _on_add_folder(self, event: Any) -> None:
        wx = self._wx
        with wx.DirDialog(self.dialog, message="Add a folder of audio to convert") as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            folder = Path(picker.GetPath())
            self._append(folder, folder)
            if not self._dest.GetValue().strip():
                self._dest.SetValue(str(default_destination(folder)))
        self._reload(select=len(self._entries) - 1)

    def _on_remove(self, event: Any) -> None:
        sel = self._list.GetSelection()
        if 0 <= sel < len(self._entries):
            del self._entries[sel]
            self._reload(select=sel)

    def _on_browse(self, event: Any) -> None:
        wx = self._wx
        with wx.DirDialog(self.dialog, message="Choose an output folder") as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._dest.SetValue(picker.GetPath())

    def _on_list_key(self, event: Any) -> None:
        if event.GetKeyCode() == self._wx.WXK_DELETE:
            self._on_remove(event)
            return
        event.Skip()

    # -- collection + show ------------------------------------------------ #

    def _selected_conflict(self) -> OnExisting:
        idx = max(0, self._conflict.GetSelection())
        return _CONFLICT_CHOICES[idx][0]

    def collect(self) -> ConvertRequest | None:
        """Build a :class:`ConvertRequest` from the current widget state."""
        fmt = self._formats[max(0, self._format.GetSelection())]
        preset_id = self._preset_ids[max(0, self._preset.GetSelection())]
        dest = self._dest.GetValue().strip()
        if not dest and self._entries:
            dest = str(default_destination(self._entries[0][0]))
        return build_request(
            self._entries,
            fmt=fmt,
            preset_id=preset_id,
            dest_dir=Path(dest) if dest else Path(),
            recurse=self._recurse.GetValue(),
            on_existing=self._selected_conflict(),
        )

    def show(self, show_modal: Callable[[Any, str], int]) -> ConvertRequest | None:
        """Show the dialog via the host's ``_show_modal_dialog`` and collect."""
        if show_modal(self.dialog, _TITLE) != self._wx.ID_OK:  # dialog_button_contract: exempt
            return None
        return self.collect()
