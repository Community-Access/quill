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

import wx

from quill.core.audio.convert import (
    Channels,
    ConversionJob,
    ConversionSpec,
    OnExisting,
    available_output_formats,
    default_destination,
    plan_jobs,
)
from quill.core.audio.dsp import DspOptions, build_dsp_filters, loudness_choices
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


# Advanced-mode choice tables (§6). The first value in each is the neutral
# "keep the preset's / source's setting" sentinel (empty / KEEP) so Advanced only
# overrides what the user deliberately touches; unset controls leave the preset.
_BITRATE_CHOICES: tuple[tuple[str, str], ...] = (
    ("", "Auto (use preset)"),
    ("96", "96 kbps"),
    ("128", "128 kbps"),
    ("192", "192 kbps"),
    ("256", "256 kbps"),
    ("320", "320 kbps"),
)
_RATE_CHOICES: tuple[tuple[str, str], ...] = (
    ("", "Keep source rate"),
    ("48000", "48 kHz"),
    ("44100", "44.1 kHz"),
    ("22050", "22.05 kHz"),
    ("16000", "16 kHz"),
)
_CHANNEL_CHOICES: tuple[tuple[Channels, str], ...] = (
    (Channels.KEEP, "Keep source channels"),
    (Channels.MONO, "Mono (1 channel)"),
    (Channels.STEREO, "Stereo (2 channels)"),
)
_DEPTH_CHOICES: tuple[tuple[str, str], ...] = (
    ("", "Keep source depth"),
    ("16", "16-bit"),
    ("24", "24-bit"),
    ("32", "32-bit float"),
)


def apply_advanced(
    base: ConversionSpec,
    *,
    bitrate_kbps: int | None = None,
    sample_rate: int | None = None,
    channels: Channels | None = None,
    bit_depth: int | None = None,
    dsp: DspOptions | None = None,
) -> ConversionSpec:
    """Layer Advanced overrides onto a preset's *base* spec (pure).

    Every argument is optional: ``None`` (the neutral choice) leaves the preset's
    value untouched, so Advanced only changes what the user explicitly set. The
    DSP toggles compose into ``ConversionSpec.filters`` via
    :func:`build_dsp_filters`, replacing any preset filters when *dsp* is given.
    """
    from dataclasses import replace

    return replace(
        base,
        bitrate_kbps=bitrate_kbps if bitrate_kbps is not None else base.bitrate_kbps,
        sample_rate=sample_rate if sample_rate is not None else base.sample_rate,
        channels=channels if channels is not None else base.channels,
        bit_depth=bit_depth if bit_depth is not None else base.bit_depth,
        filters=build_dsp_filters(dsp) if dsp is not None else base.filters,
    )


def plan_and_run(host: Any, request: ConvertRequest) -> None:
    """Plan jobs from *request* and run the batch off the UI thread (§8).

    Uses the host's ``_run_background_task`` (protected on close) so a long batch
    never owns the window and closing while converting routes through the shared
    confirm. Progress is reported through the task's ``progress(message, current,
    total)`` callback — the shared contract that updates the status bar, the
    **tray tooltip** (so a batch stays reviewable while minimized), and the
    25/50/75 percent milestone announcements. wx-free logic lives in the engine;
    this only marshals progress back via that callback.
    """
    from quill.core.audio.convert import run_conversion_batch
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

    def work(progress: Callable[[str, int, int], None]) -> Any:
        def on_progress(done: int, total_jobs: int, job: ConversionJob) -> None:
            # Route through the task progress callback so the status bar AND the
            # tray tooltip AND the milestone announcements all update together.
            progress(f"Converting {done} of {total_jobs}: {job.source.name}", done, total_jobs)

        return run_conversion_batch(ffmpeg, jobs, on_progress=on_progress)

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


def run_audio_conversion(
    host: Any, *, initial_entries: list[tuple[Path, Path | None]] | None = None
) -> None:
    """Open the Convert Audio dialog and run the chosen conversion (§9.2).

    The single entry point the Studio menu / command binds to. Resolves ffmpeg,
    filters the format list to what it can encode, shows the accessible dialog,
    and hands a runnable request to :func:`plan_and_run`. ``initial_entries``
    pre-seeds the queue (used by URL import to drop the downloaded file in).
    """
    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = find_ffmpeg()
    formats = available_output_formats(ffmpeg)
    dialog = ConvertAudioDialog(host.frame, output_formats=formats, initial_entries=initial_entries)
    try:
        request = dialog.show(host._show_modal_dialog)
    finally:
        # show_modal_dialog only ShowModal()s; the caller owns teardown (A11Y-4).
        dialog.Destroy()
    if request is None:
        host._set_status("Audio conversion cancelled.")
        return
    plan_and_run(host, request)


# yt-dlp reaches arbitrary media hosts; this is the one-time rights + consent
# notice shown before the on-demand install, per §4.6 and the egress audit.
_URL_CONSENT = (
    "Convert from a link uses yt-dlp to download the audio from a web address "
    "(YouTube and many other sites) so QUILL can convert it on your machine.\n\n"
    "The first time, QUILL will download and install the yt-dlp component "
    "(about 3 MB, from PyPI).\n\n"
    "Only download content you have the right to use. QUILL sends no account or "
    "credential to the site. This feature is unavailable in Safe Mode.\n\n"
    "Continue?"
)
_URL_TITLE = "Convert from URL"


def run_url_conversion(host: Any) -> None:
    """Studio > Convert from URL...: download a link's audio, then convert it.

    Prompts for a URL, obtains one-time consent to install yt-dlp on demand,
    downloads the best-audio stream off the UI thread (tray-aware progress), and
    opens the Convert Audio dialog seeded with the downloaded file. Refused in
    Safe Mode. The download/install core is the tested, wx-free
    :mod:`quill.core.audio.url_import`.
    """
    from quill.core.audio.url_import import looks_like_url, url_import_available

    if getattr(host, "_safe_mode", False):
        host._show_message_box("Converting from a link is unavailable in Safe Mode.", _URL_TITLE)
        return

    url = _prompt_for_url(host)
    if not url:
        return
    if not looks_like_url(url):
        host._show_message_box(
            "That does not look like a web address. Paste a full http:// or https:// link.",
            _URL_TITLE,
        )
        return

    if not url_import_available():
        consented = host._show_message_box(_URL_CONSENT, _URL_TITLE, wx.ICON_QUESTION | wx.YES_NO)
        if consented != wx.YES:
            host._set_status("Convert from URL cancelled.")
            return

    _download_then_convert(host, url)


def _prompt_for_url(host: Any) -> str:
    """Ask for a link via the stock text-entry dialog; '' if cancelled."""
    entry = wx.TextEntryDialog(
        host.frame, "Paste a link to convert (YouTube and many other sites):", _URL_TITLE
    )
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return ""
        return entry.GetValue().strip()
    finally:
        entry.Destroy()


def _download_then_convert(host: Any, url: str) -> None:
    """Install-if-needed + download off-thread, then seed the converter (§4.6)."""
    import tempfile

    from quill.core.audio.url_import import ensure_and_download

    dest_dir = Path(tempfile.mkdtemp(prefix="quill-url-import-"))

    def work(progress: Callable[[str, int, int], None]) -> Any:
        return ensure_and_download(
            url,
            dest_dir,
            progress=lambda fraction, message: progress(message, int(fraction * 100), 100),
        )

    def on_success(downloaded: Any) -> None:
        path = Path(downloaded)
        host._set_status(f"Downloaded {path.name}. Choose how to convert it.")
        run_audio_conversion(host, initial_entries=[(path, None)])

    host._run_background_task(
        "Downloading audio from the link",
        work,
        on_success,
        notify_on_success=False,
        notify_on_error=True,
        notification_category="audio",
        protect_on_close=True,
    )


class ConvertAudioDialog(wx.Dialog):
    """A ``wx.Dialog`` for Basic-mode conversion (accessible, house contract).

    A subclass so it owns its keyboard contract and is shown through the host's
    accessible ``_show_modal_dialog`` path (see :func:`run_audio_conversion`).
    """

    def __init__(
        self,
        parent: Any,
        *,
        output_formats: list[str],
        initial_entries: list[tuple[Path, Path | None]] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title=_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.convert_audio",
        )
        self._formats = output_formats or ["wav"]
        # Seed the queue (e.g. a file just downloaded by URL import) so the dialog
        # opens ready to convert it.
        self._entries: list[tuple[Path, Path | None]] = list(initial_entries or [])
        self._build()
        if self._entries:
            self._reload(select=0)

    # -- construction ----------------------------------------------------- #

    def _build(self) -> None:
        from quill.ui.accessible_names import set_accessible_name
        from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label="&Files to convert:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(self, name="Files to convert")
        set_accessible_name(self._list, "Files to convert")
        sizer.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_files_btn = wx.Button(self, label="&Add files...")
        self._add_folder_btn = wx.Button(self, label="Add f&older...")
        self._remove_btn = wx.Button(self, label="&Remove")
        self._recurse = wx.CheckBox(self, label="&Include sub-folders")
        self._recurse.SetValue(True)
        set_accessible_name(self._recurse, "Include sub-folders")
        for widget in (self._add_files_btn, self._add_folder_btn, self._remove_btn, self._recurse):
            add_row.Add(widget, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        sizer.Add(add_row, 0, wx.ALL, 8)

        # Convert to / Preset row.
        sizer.Add(wx.StaticText(self, label="Con&vert to:"), 0, wx.LEFT | wx.TOP, 8)
        self._format = wx.Choice(self, choices=[f.upper() for f in self._formats])
        self._format.SetSelection(0)
        set_accessible_name(self._format, "Convert to format")
        sizer.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        sizer.Add(wx.StaticText(self, label="&Preset:"), 0, wx.LEFT | wx.TOP, 8)
        self._preset_ids = [pid for pid, _label in preset_choices()]
        self._preset = wx.Choice(self, choices=[label for _pid, label in preset_choices()])
        self._preset.SetSelection(max(0, self._preset_ids.index(DEFAULT_PRESET_ID)))
        set_accessible_name(self._preset, "Preset")
        sizer.Add(self._preset, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Destination folder + conflict policy.
        sizer.Add(wx.StaticText(self, label="Output f&older:"), 0, wx.LEFT | wx.TOP, 8)
        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._dest = wx.TextCtrl(self)
        set_accessible_name(self._dest, "Output folder")
        self._browse_btn = wx.Button(self, label="&Browse...")
        dest_row.Add(self._dest, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        dest_row.Add(self._browse_btn, 0)
        sizer.Add(dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        sizer.Add(wx.StaticText(self, label="On &conflict:"), 0, wx.LEFT | wx.TOP, 8)
        self._conflict = wx.Choice(self, choices=[label for _policy, label in _CONFLICT_CHOICES])
        self._conflict.SetSelection(0)
        set_accessible_name(self._conflict, "On conflict")
        sizer.Add(self._conflict, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._advanced = wx.CheckBox(self, label="Advanced o&ptions")
        set_accessible_name(self._advanced, "Advanced options")
        sizer.Add(self._advanced, 0, wx.ALL, 8)
        self._main_sizer = sizer
        self._build_advanced(set_accessible_name)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)

        self._add_files_btn.Bind(wx.EVT_BUTTON, self._on_add_files)
        self._add_folder_btn.Bind(wx.EVT_BUTTON, self._on_add_folder)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self._browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._advanced.Bind(wx.EVT_CHECKBOX, self._on_toggle_advanced)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        apply_listbox_activation(self._list, lambda _e: None)
        # Convert is the affirmative; a real Cancel/Escape button (no trap).
        apply_modal_ids(
            self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL, affirmative_label="Convert"
        )

    def _build_advanced(self, set_accessible_name: Callable[[Any, str], None]) -> None:
        """Build the collapsed Advanced panel (§6): codec knobs + DSP toggles.

        Everything lives on the dialog (never an intermediate panel, per the
        accessible-name contract) inside one sizer we show/hide as a unit. Each
        control's neutral first choice means "leave the preset alone", so an
        untouched Advanced panel changes nothing.
        """
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(self, label="Advanced encoding and processing:"), 0, wx.ALL, 6)

        # z-order-safe row helper (A11Y-Z-ORDER): create the label first, then run
        # the factory so each control is created *after* its label. Call sites must
        # pass a real ``lambda`` (the gate checks for it) — never a pre-made control.
        def labeled(caption: str, make_ctrl: Callable[[], Any]) -> Any:
            box.Add(wx.StaticText(self, label=caption), 0, wx.LEFT | wx.TOP, 6)
            ctrl = make_ctrl()
            box.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
            return ctrl

        def choice(pairs: tuple[tuple[Any, str], ...], name: str) -> wx.Choice:
            ctrl = wx.Choice(self, choices=[label for _value, label in pairs])
            ctrl.SetSelection(0)
            set_accessible_name(ctrl, name)
            return ctrl

        self._adv_bitrate = labeled("Bit &rate:", lambda: choice(_BITRATE_CHOICES, "Bit rate"))
        self._adv_rate = labeled("Sa&mple rate:", lambda: choice(_RATE_CHOICES, "Sample rate"))
        self._adv_channels = labeled("C&hannels:", lambda: choice(_CHANNEL_CHOICES, "Channels"))
        self._adv_depth = labeled("Bit &depth:", lambda: choice(_DEPTH_CHOICES, "Bit depth"))
        self._adv_loudness = labeled(
            "&Loudness:", lambda: choice(tuple(loudness_choices()), "Loudness normalization")
        )

        def new_spin(lo: float, hi: float, inc: float, digits: int, name: str) -> wx.SpinCtrlDouble:
            spin = wx.SpinCtrlDouble(self, min=lo, max=hi, inc=inc)
            spin.SetDigits(digits)
            set_accessible_name(spin, name)
            return spin

        self._adv_gain = labeled(
            "&Gain (dB):", lambda: new_spin(-30.0, 30.0, 0.5, 1, "Gain in decibels")
        )
        self._adv_gain.SetValue(0.0)  # 0 dB = no change
        self._adv_tempo = labeled(
            "&Speed (tempo):", lambda: new_spin(0.5, 2.0, 0.05, 2, "Speed, tempo multiplier")
        )
        self._adv_tempo.SetValue(1.0)  # 1.0x = unchanged; no pitch shift
        self._adv_fade_in = labeled(
            "Fade &in (seconds):", lambda: new_spin(0.0, 10.0, 0.5, 1, "Fade-in seconds")
        )
        self._adv_fade_out = labeled(
            "Fade &out (seconds):", lambda: new_spin(0.0, 10.0, 0.5, 1, "Fade-out seconds")
        )

        self._adv_highpass = wx.CheckBox(self, label="Remove low-frequency r&umble (high-pass)")
        self._adv_trim = wx.CheckBox(self, label="&Trim leading and trailing silence")
        self._adv_compressor = wx.CheckBox(self, label="&Compress dynamics (even out loud/quiet)")
        self._adv_leveler = wx.CheckBox(self, label="Le&vel volume across the file")
        for cb, name in (
            (self._adv_highpass, "Remove low-frequency rumble"),
            (self._adv_trim, "Trim leading and trailing silence"),
            (self._adv_compressor, "Compress dynamics"),
            (self._adv_leveler, "Level volume across the file"),
        ):
            set_accessible_name(cb, name)
            box.Add(cb, 0, wx.LEFT | wx.TOP, 6)

        self._adv_box = box
        self._main_sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._main_sizer.Hide(box, recursive=True)

    def _on_toggle_advanced(self, _event: Any) -> None:
        """Reveal or collapse the Advanced panel, then re-fit and move focus.

        Focus lands on the first revealed control (or back on the checkbox when
        collapsing) so a screen-reader user hears the state change — the reveal
        is announced by the focus move, not a silent resize.
        """
        show = self._advanced.GetValue()
        self._main_sizer.Show(self._adv_box, show, recursive=True)
        self.Layout()
        self.Fit()
        (self._adv_bitrate if show else self._advanced).SetFocus()

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
        with wx.FileDialog(
            self,
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
        with wx.DirDialog(self, message="Add a folder of audio to convert") as picker:
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
        with wx.DirDialog(self, message="Choose an output folder") as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._dest.SetValue(picker.GetPath())

    def _on_list_key(self, event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self._on_remove(event)
            return
        event.Skip()

    # -- collection + show ------------------------------------------------ #

    def _selected_conflict(self) -> OnExisting:
        idx = max(0, self._conflict.GetSelection())
        return _CONFLICT_CHOICES[idx][0]

    def collect(self) -> ConvertRequest | None:
        """Build a :class:`ConvertRequest` from the current widget state."""
        from dataclasses import replace

        fmt = self._formats[max(0, self._format.GetSelection())]
        preset_id = self._preset_ids[max(0, self._preset.GetSelection())]
        dest = self._dest.GetValue().strip()
        if not dest and self._entries:
            dest = str(default_destination(self._entries[0][0]))
        request = build_request(
            self._entries,
            fmt=fmt,
            preset_id=preset_id,
            dest_dir=Path(dest) if dest else Path(),
            recurse=self._recurse.GetValue(),
            on_existing=self._selected_conflict(),
        )
        if request is not None and self._advanced.GetValue():
            request = replace(
                request, spec=apply_advanced(request.spec, **self._collect_advanced())
            )
        return request

    def _choice_value(self, choice: Any, table: tuple[tuple[Any, str], ...]) -> Any:
        """The value paired with a wx.Choice's current selection (index 0 = neutral)."""
        return table[max(0, choice.GetSelection())][0]

    def _collect_advanced(self) -> dict[str, Any]:
        """Read the Advanced controls into keyword args for :func:`apply_advanced`."""
        bitrate = self._choice_value(self._adv_bitrate, _BITRATE_CHOICES)
        rate = self._choice_value(self._adv_rate, _RATE_CHOICES)
        channels = self._choice_value(self._adv_channels, _CHANNEL_CHOICES)
        depth = self._choice_value(self._adv_depth, _DEPTH_CHOICES)
        dsp = DspOptions(
            loudness=self._choice_value(self._adv_loudness, tuple(loudness_choices())),
            gain_db=float(self._adv_gain.GetValue()),
            high_pass=self._adv_highpass.GetValue(),
            trim_silence=self._adv_trim.GetValue(),
            tempo=float(self._adv_tempo.GetValue()),
            compressor=self._adv_compressor.GetValue(),
            leveler=self._adv_leveler.GetValue(),
            fade_in_s=float(self._adv_fade_in.GetValue()),
            fade_out_s=float(self._adv_fade_out.GetValue()),
        )
        return {
            "bitrate_kbps": int(bitrate) if bitrate else None,
            "sample_rate": int(rate) if rate else None,
            "channels": channels if channels is not Channels.KEEP else None,
            "bit_depth": int(depth) if depth else None,
            "dsp": dsp,
        }

    def show(self, show_modal: Callable[[Any, str], int]) -> ConvertRequest | None:
        """Show the dialog via the host's ``_show_modal_dialog`` and collect."""
        if show_modal(self, _TITLE) != wx.ID_OK:  # dialog_button_contract: exempt
            return None
        return self.collect()
