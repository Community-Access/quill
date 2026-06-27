"""Batch Speech Export dialog — folder of documents to chaptered audio (§4.2).

A standalone, keyboard-first ``wx.Dialog`` that collects everything the chaptered
document-to-speech pipeline needs: a source folder, the file types to include,
the engine/voice/pace, the output format, and the chapter options (transition
sounder, the inter-article / inter-sentence / trailing pauses, and whether the
heading is spoken). It does **not** run the batch itself — :meth:`show` returns a
:class:`BatchSpeechRequest` (or ``None`` on cancel) and the caller
(``quill.ui.batch_speech_runner.run_batch_export_to_speech``) runs it in the
background.

Per the NVDA focus rule (A11Y-SR-2) every control is parented directly on the
dialog, never on an intermediate layout panel. The dialog is opened only via
``MainFrame._show_modal_dialog`` and wires its OK/Cancel ids through
``apply_modal_ids`` so Escape closes it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    show_message_box,
)

# (label, engine_id) pairs, mirroring the Speech Hub's engine list.
EngineOptions = list[tuple[str, str]]
# engine_id -> [(voice_label, voice_id), ...]
VoicesFor = Callable[[str], list[tuple[str, str]]]


@dataclass(slots=True)
class BatchSpeechRequest:
    """Everything the caller needs to run one chaptered batch export."""

    source_folder: Path
    recursive: bool
    extensions: tuple[str, ...]
    engine: str
    voice: str
    rate: int
    speed: float
    output_format: str  # "wav" | "mp3"
    sound_enabled: bool
    sound_volume: int
    article_gap_ms: int
    sentence_gap_ms: int
    tail_padding_ms: int
    speak_headings: bool
    skip_existing: bool
    # Discovery filters: ;/,-separated globs matched against the file name and the
    # path relative to the source folder; ``max_file_bytes`` of 0 = no size cap.
    include_glob: str = ""
    exclude_glob: str = ""
    max_file_bytes: int = 0
    # What to do when a target audio file already exists.
    on_existing: str = "overwrite"  # skip | overwrite | rename
    # Chapter mode: "single" = one chaptered file per document; "separate" = one
    # audio file per article/heading, into a per-document folder.
    chapter_mode: str = "single"
    # Dry run: write a ``<doc>.preview.txt`` of the exact spoken text (after
    # normalization + pronunciation + polish) for each file, without synthesizing.
    dry_run: bool = False
    preview: bool = False  # internal: a Preview press, not a Start
    # Combine empty headings into the next article (ACB-style) before synthesis.
    combine_headings: bool = False
    # Normalize each output to ACX audiobook loudness (two-pass loudnorm).
    normalize_loudness: bool = False
    # Round-robin voices: ordered voice ids (of the selected engine) cycled one per
    # article/heading. Empty or one voice -> the single `voice` above is used.
    round_robin_voices: tuple[str, ...] = ()
    # Translated audio export (§7): also export each document in these languages.
    # Each target is (language_code, engine, voice_id); the document is translated
    # into the language then synthesized with that voice. Empty = no translation.
    translation_targets: tuple[tuple[str, str, str], ...] = ()
    # Translation backend: "ai_assistant" (configured AI provider) or "libretranslate".
    translation_provider: str = "ai_assistant"
    libretranslate_url: str = "http://localhost:5000"
    # Temporary-files parent folder. Empty = the system temp dir. Each run creates a
    # ``quill-batch-<timestamp>`` subfolder under it for all of its scratch dirs.
    temp_folder: str = ""
    # Save the exact text sent to the engine (after normalization/pronunciation/
    # polish) as a ``<doc>.spoken.txt`` sidecar, in addition to synthesizing.
    save_spoken_text: bool = False
    # Audiobook assembly: when set, combine the produced (or pre-recorded) audio in
    # the source folder into a single chaptered M4B/MP3 with the book tags below.
    make_book: bool = False
    book_title: str = ""
    book_author: str = ""
    book_narrator: str = ""
    book_genre: str = "Audiobook"
    book_year: str = ""
    book_cover_path: str = ""
    book_format: str = "m4b"  # m4b | mp3
    book_output_path: str = ""
    book_acx_normalize: bool = False
    # Pause after synthesis to open the chapter editor (rename/reorder/merge) before
    # the book is built. A folder of pre-recorded audio (no documents) always opens it.
    book_review_chapters: bool = False
    _voice_label: str = field(default="", repr=False)


_ALL_EXTENSIONS: list[tuple[str, str]] = [
    ("&Word (.docx)", ".docx"),
    ("&Markdown (.md)", ".md"),
    ("&HTML (.html, .htm)", ".html"),
    ("Plain &text (.txt)", ".txt"),
]
# .html implies .htm in discovery.
_EXTENSION_GROUPS = {".html": (".html", ".htm")}
# Existing-file policy choices, in the order they appear in the dialog's Choice.
_EXISTING_POLICIES = ("skip", "overwrite", "rename")
# Output formats, in the order they appear in the format Choice control.
_FORMAT_CHOICES = ("mp3", "m4b", "wav")
_FORMAT_INDEX = {fmt: i for i, fmt in enumerate(_FORMAT_CHOICES)}
# Chapter modes, in the order they appear in the mode Choice control.
_MODE_CHOICES = ("single", "separate")
_MODE_INDEX = {mode: i for i, mode in enumerate(_MODE_CHOICES)}
# Audiobook output formats, in the order they appear in the book format Choice.
_BOOK_FORMATS = ("m4b", "mp3")
_BOOK_FORMAT_INDEX = {fmt: i for i, fmt in enumerate(_BOOK_FORMATS)}


class BatchSpeechExportDialog:
    """Configuration dialog for chaptered batch document-to-speech export."""

    def __init__(
        self,
        parent: object,
        *,
        engine_options: EngineOptions,
        engine_available: dict[str, bool],
        voices_for: VoicesFor,
        on_preview: Callable[[BatchSpeechRequest], None],
        defaults: BatchSpeechRequest,
    ) -> None:
        import wx

        self._wx = wx
        self._voices_for = voices_for
        self._on_preview = on_preview
        self._engine_options = engine_options
        self._engine_available = engine_available
        self._result: BatchSpeechRequest | None = None
        # Round-robin rotation: ordered (voice_id, label) for the selected engine.
        self._rr_voices: list[tuple[str, str]] = []
        # Translation targets: ordered (lang_code, engine, voice_id, display_label).
        self._tr_targets: list[tuple[str, str, str, str]] = []

        self.dialog = wx.Dialog(
            parent,
            title="Batch Export to Speech Audio",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(620, 660))

        root = wx.BoxSizer(wx.VERTICAL)

        def label(text: str) -> None:
            root.Add(wx.StaticText(self.dialog, label=text), 0, wx.LEFT | wx.TOP, 8)

        # --- Source folder + recurse ---
        label("&Source folder (documents to convert):")
        src_row = wx.BoxSizer(wx.HORIZONTAL)
        self._source = wx.TextCtrl(self.dialog, value=str(defaults.source_folder))
        browse = wx.Button(self.dialog, label="B&rowse...")
        browse.Bind(wx.EVT_BUTTON, self._on_browse_source)
        src_row.Add(self._source, 1, wx.EXPAND | wx.RIGHT, 6)
        src_row.Add(browse, 0)
        root.Add(src_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._recursive = wx.CheckBox(self.dialog, label="Include su&bfolders")
        self._recursive.SetValue(defaults.recursive)
        root.Add(self._recursive, 0, wx.LEFT | wx.TOP, 8)

        # --- File types ---
        label("File &types to include:")
        self._ext_boxes: list[tuple[wx.CheckBox, str]] = []
        ext_row = wx.BoxSizer(wx.HORIZONTAL)
        for text, ext in _ALL_EXTENSIONS:
            cb = wx.CheckBox(self.dialog, label=text)
            cb.SetValue(ext in defaults.extensions)
            ext_row.Add(cb, 0, wx.RIGHT, 10)
            self._ext_boxes.append((cb, ext))
        root.Add(ext_row, 0, wx.LEFT | wx.TOP, 8)

        # --- Discovery filters (optional) ---
        label("Only incl&ude files matching (globs, ; or , separated; blank = all):")
        self._include = wx.TextCtrl(self.dialog, value=defaults.include_glob)
        root.Add(self._include, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        label("E&xclude files matching (globs, ; or , separated):")
        self._exclude = wx.TextCtrl(self.dialog, value=defaults.exclude_glob)
        root.Add(self._exclude, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Engine / voice / pace ---
        label("&Engine:")
        self._engine = wx.Choice(
            self.dialog, choices=[self._engine_label(lbl, eid) for lbl, eid in engine_options]
        )
        self._engine.Bind(wx.EVT_CHOICE, lambda _e: self._on_engine_change())
        root.Add(self._engine, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._select_engine(defaults.engine)

        label("&Voice:")
        voice_row = wx.BoxSizer(wx.HORIZONTAL)
        self._voice = wx.Choice(self.dialog, choices=[])
        preview_btn = wx.Button(self.dialog, label="&Preview")
        preview_btn.Bind(wx.EVT_BUTTON, self._on_preview_click)
        voice_row.Add(self._voice, 1, wx.EXPAND | wx.RIGHT, 6)
        voice_row.Add(preview_btn, 0)
        root.Add(voice_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        pace_row = wx.BoxSizer(wx.HORIZONTAL)
        pace_row.Add(wx.StaticText(self.dialog, label="R&ate (WPM):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._rate = wx.SpinCtrl(self.dialog, min=80, max=450, initial=defaults.rate)
        self._set_accessible_name(self._rate, "Rate (WPM)")
        pace_row.Add(self._rate, 0, wx.LEFT | wx.RIGHT, 6)
        pace_row.Add(
            wx.StaticText(self.dialog, label="&Kokoro speed:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._speed = wx.SpinCtrlDouble(
            self.dialog, min=0.5, max=2.0, inc=0.05, initial=defaults.speed
        )
        # A SpinCtrlDouble wraps an inner TextCtrl (the focusable edit); the adjacent
        # StaticText and the composite's own name do not reach that inner field, so a
        # screen reader reads it unnamed. _set_accessible_name names the inner edit too.
        self._set_accessible_name(self._speed, "Kokoro speed")
        pace_row.Add(self._speed, 0, wx.LEFT, 6)
        root.Add(pace_row, 0, wx.LEFT | wx.TOP, 8)

        # --- Round-robin voices (optional) ---
        label("Round-&robin voices (each article gets the next voice; optional):")
        rr_add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._rr_pick = wx.Choice(self.dialog, choices=[])
        self._rr_pick.SetName("Round-robin voice to add")
        rr_add = wx.Button(self.dialog, label="A&dd voice")
        rr_add.Bind(wx.EVT_BUTTON, lambda _e: self._on_rr_add())
        rr_add_row.Add(self._rr_pick, 1, wx.EXPAND | wx.RIGHT, 6)
        rr_add_row.Add(rr_add, 0)
        root.Add(rr_add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        # A dedicated label immediately before the list: a screen reader names a list
        # from its preceding StaticText, so SetName alone left it announced unnamed.
        label("Voice o&rder (the rotation; use the buttons below to reorder):")
        self._rr_list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._rr_list.SetName("Round-robin voice order")
        apply_listbox_activation(self._rr_list, lambda _e: self._rr_pick.SetFocus())
        root.Add(self._rr_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        rr_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._rr_up = wx.Button(self.dialog, label="Move U&p")
        self._rr_down = wx.Button(self.dialog, label="Move Dow&n")
        self._rr_remove = wx.Button(self.dialog, label="Re&move")
        self._rr_up.Bind(wx.EVT_BUTTON, lambda _e: self._on_rr_move(-1))
        self._rr_down.Bind(wx.EVT_BUTTON, lambda _e: self._on_rr_move(1))
        self._rr_remove.Bind(wx.EVT_BUTTON, lambda _e: self._on_rr_remove())
        for btn in (self._rr_up, self._rr_down, self._rr_remove):
            rr_btn_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(rr_btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Output format ---
        label("Output &format:")
        self._format = wx.Choice(
            self.dialog,
            choices=[
                "MP3 (with chapter markers)",
                "M4B audiobook (native chapters)",
                "WAV",
            ],
        )
        self._format.SetSelection(_FORMAT_INDEX.get(defaults.output_format, 0))
        root.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Chapter mode ---
        label("Chapter &mode:")
        self._mode = wx.Choice(
            self.dialog,
            choices=["Single chaptered file", "Separate file per article"],
        )
        self._mode.SetSelection(_MODE_INDEX.get(defaults.chapter_mode, 0))
        root.Add(self._mode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Chapter options ---
        label("Chapter options:")
        self._sound = wx.CheckBox(self.dialog, label="Play a transition s&ounder between headings")
        self._sound.SetValue(defaults.sound_enabled)
        root.Add(self._sound, 0, wx.LEFT | wx.TOP, 8)
        self._speak_headings = wx.CheckBox(self.dialog, label="Speak each &heading aloud")
        self._speak_headings.SetValue(defaults.speak_headings)
        root.Add(self._speak_headings, 0, wx.LEFT | wx.TOP, 8)
        self._combine = wx.CheckBox(
            self.dialog, label="&Combine empty headings into the next article"
        )
        self._combine.SetValue(defaults.combine_headings)
        root.Add(self._combine, 0, wx.LEFT | wx.TOP, 8)
        self._normalize = wx.CheckBox(
            self.dialog, label="Normalize &loudness to audiobook (ACX) level"
        )
        self._normalize.SetValue(defaults.normalize_loudness)
        root.Add(self._normalize, 0, wx.LEFT | wx.TOP, 8)
        self._dry_run = wx.CheckBox(
            self.dialog, label="Dr&y run: write preview text only (don't synthesize)"
        )
        self._dry_run.SetValue(defaults.dry_run)
        root.Add(self._dry_run, 0, wx.LEFT | wx.TOP, 8)
        label("If an audio file already e&xists:")
        self._on_existing = wx.Choice(
            self.dialog, choices=["Skip (resume)", "Overwrite", "Rename (keep both)"]
        )
        policy = "skip" if defaults.skip_existing else defaults.on_existing
        policy_idx = _EXISTING_POLICIES.index(policy) if policy in _EXISTING_POLICIES else 1
        self._on_existing.SetSelection(policy_idx)
        root.Add(self._on_existing, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        gap_grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        self._article_gap = self._add_ms_spin(
            gap_grid, "Pause between &articles (ms):", defaults.article_gap_ms
        )
        self._sentence_gap = self._add_ms_spin(
            gap_grid, "Pause between se&ntences (ms):", defaults.sentence_gap_ms
        )
        self._tail_padding = self._add_ms_spin(
            gap_grid, "Trailing pad per section, anti-cli&pping (ms):", defaults.tail_padding_ms
        )
        self._sound_volume = self._add_ms_spin(
            gap_grid, "Sounder &volume (0-100):", defaults.sound_volume, hi=100
        )
        root.Add(gap_grid, 0, wx.LEFT | wx.TOP, 8)

        # --- Translation (also export in other languages) ---
        label("Also export in other &languages (translated):")
        from quill.core.ai.translation import SUPPORTED_LANGUAGES

        self._tr_lang_pairs = sorted(SUPPORTED_LANGUAGES.items())  # (name, code)
        tr_add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._tr_lang = wx.Choice(self.dialog, choices=[name for name, _c in self._tr_lang_pairs])
        self._tr_lang.SetName("Translation language")
        self._tr_lang.Bind(wx.EVT_CHOICE, lambda _e: self._reload_tr_voices())
        self._tr_voice = wx.Choice(self.dialog, choices=[])
        self._tr_voice.SetName("Translation voice")
        tr_add = wx.Button(self.dialog, label="Add lan&guage")
        tr_add.Bind(wx.EVT_BUTTON, lambda _e: self._on_tr_add())
        tr_add_row.Add(self._tr_lang, 1, wx.EXPAND | wx.RIGHT, 6)
        tr_add_row.Add(self._tr_voice, 2, wx.EXPAND | wx.RIGHT, 6)
        tr_add_row.Add(tr_add, 0)
        root.Add(tr_add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        label("Languages &chosen (translated exports):")
        self._tr_list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._tr_list.SetName("Translation targets")
        apply_listbox_activation(self._tr_list, lambda _e: self._tr_lang.SetFocus())
        root.Add(self._tr_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        tr_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        tr_remove = wx.Button(self.dialog, label="Remove la&nguage")
        tr_remove.Bind(wx.EVT_BUTTON, lambda _e: self._on_tr_remove())
        tr_btn_row.Add(tr_remove, 0, wx.RIGHT, 6)
        tr_btn_row.Add(
            wx.StaticText(self.dialog, label="Trans&late with:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._tr_provider = wx.Choice(
            self.dialog, choices=["AI provider (cloud)", "LibreTranslate (local)"]
        )
        self._tr_provider.SetSelection(
            1 if defaults.translation_provider == "libretranslate" else 0
        )
        tr_btn_row.Add(self._tr_provider, 0, wx.LEFT, 6)
        root.Add(tr_btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Temporary files + diagnostics ---
        label("&Temporary files folder (blank = system temp):")
        tmp_row = wx.BoxSizer(wx.HORIZONTAL)
        self._temp_folder = wx.TextCtrl(self.dialog, value=defaults.temp_folder)
        self._temp_folder.SetName("Temporary files folder")
        tmp_browse = wx.Button(self.dialog, label="Browse temp&...")
        tmp_browse.Bind(wx.EVT_BUTTON, self._on_browse_temp)
        tmp_row.Add(self._temp_folder, 1, wx.EXPAND | wx.RIGHT, 6)
        tmp_row.Add(tmp_browse, 0)
        root.Add(tmp_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._save_spoken = wx.CheckBox(
            self.dialog, label="Save the te&xt sent to speech (one sidecar per document)"
        )
        self._save_spoken.SetValue(defaults.save_spoken_text)
        root.Add(self._save_spoken, 0, wx.LEFT | wx.TOP, 8)

        # --- Audiobook assembly (optional) ---
        self._make_book = wx.CheckBox(self.dialog, label="Assemble the results into one audioboo&k")
        self._make_book.SetValue(defaults.make_book)
        self._make_book.Bind(wx.EVT_CHECKBOX, lambda _e: self._sync_book_enabled())
        root.Add(self._make_book, 0, wx.LEFT | wx.TOP, 8)
        book_grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        book_grid.AddGrowableCol(1, 1)
        self._book_title = self._add_book_field(book_grid, "Book ti&tle:", defaults.book_title)
        self._book_author = self._add_book_field(book_grid, "A&uthor:", defaults.book_author)
        self._book_narrator = self._add_book_field(book_grid, "Narra&tor:", defaults.book_narrator)
        self._book_genre = self._add_book_field(book_grid, "Gen&re:", defaults.book_genre)
        self._book_year = self._add_book_field(book_grid, "Yea&r:", defaults.book_year)
        root.Add(book_grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        label("Cover ima&ge (auto-detected from the folder; optional):")
        cover_row = wx.BoxSizer(wx.HORIZONTAL)
        self._book_cover = wx.TextCtrl(self.dialog, value=defaults.book_cover_path)
        self._book_cover.SetName("Cover image")
        cover_browse = wx.Button(self.dialog, label="Browse co&ver...")
        cover_browse.Bind(wx.EVT_BUTTON, self._on_browse_cover)
        cover_row.Add(self._book_cover, 1, wx.EXPAND | wx.RIGHT, 6)
        cover_row.Add(cover_browse, 0)
        root.Add(cover_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        book_fmt_row = wx.BoxSizer(wx.HORIZONTAL)
        book_fmt_row.Add(
            wx.StaticText(self.dialog, label="Book for&mat:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._book_format = wx.Choice(
            self.dialog, choices=["M4B audiobook (native chapters)", "MP3 (with chapter markers)"]
        )
        self._book_format.SetName("Book format")
        self._book_format.SetSelection(_BOOK_FORMAT_INDEX.get(defaults.book_format, 0))
        self._book_format.Bind(wx.EVT_CHOICE, lambda _e: self._sync_book_output_suffix())
        book_fmt_row.Add(self._book_format, 0, wx.LEFT, 6)
        root.Add(book_fmt_row, 0, wx.LEFT | wx.TOP, 8)
        self._book_acx = wx.CheckBox(
            self.dialog, label="Normalize the book to ACX (Audible) lou&dness"
        )
        self._book_acx.SetValue(defaults.book_acx_normalize)
        root.Add(self._book_acx, 0, wx.LEFT | wx.TOP, 8)
        self._book_review = wx.CheckBox(
            self.dialog, label="&Review chapters (rename/reorder/merge) before building"
        )
        self._book_review.SetValue(defaults.book_review_chapters)
        root.Add(self._book_review, 0, wx.LEFT | wx.TOP, 8)
        label("Save the book &as (blank = the source folder):")
        book_out_row = wx.BoxSizer(wx.HORIZONTAL)
        self._book_output = wx.TextCtrl(self.dialog, value=defaults.book_output_path)
        self._book_output.SetName("Save the book as")
        book_out_browse = wx.Button(self.dialog, label="Browse boo&k...")
        book_out_browse.Bind(wx.EVT_BUTTON, self._on_browse_book_output)
        book_out_row.Add(self._book_output, 1, wx.EXPAND | wx.RIGHT, 6)
        book_out_row.Add(book_out_browse, 0)
        root.Add(book_out_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._book_controls = [
            self._book_title,
            self._book_author,
            self._book_narrator,
            self._book_genre,
            self._book_year,
            self._book_cover,
            cover_browse,
            self._book_format,
            self._book_acx,
            self._book_review,
            self._book_output,
            book_out_browse,
        ]

        # --- Buttons (OK = Start) ---
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        start_btn = wx.Button(self.dialog, id=wx.ID_OK, label="&Start")
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL)
        start_btn.Bind(wx.EVT_BUTTON, self._on_start)
        btn_row.AddStretchSpacer()
        btn_row.Add(start_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)
        self.dialog.Fit()
        self._reload_voices(initial_voice=defaults.voice)
        self._seed_rotation(defaults.round_robin_voices)
        self._reload_tr_voices()
        self._seed_translations(defaults.translation_targets)
        self._sync_book_enabled()

    # ------------------------------------------------------------------ helpers

    def _engine_label(self, label: str, engine_id: str) -> str:
        if not self._engine_available.get(engine_id, True):
            return f"{label} (not installed)"
        return label

    def _add_ms_spin(self, grid: object, text: str, value: int, *, hi: int = 10000) -> object:
        wx = self._wx
        grid.Add(wx.StaticText(self.dialog, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
        spin = wx.SpinCtrl(self.dialog, min=0, max=hi, initial=int(value))
        grid.Add(spin, 0)
        return spin

    def _set_accessible_name(self, ctrl: object, name: str) -> None:
        """Set a control's accessible name, reaching the inner edit of composite spinners.

        ``wx.SpinCtrlDouble`` wraps a child ``TextCtrl`` (the focusable edit); that
        inner field is what a screen reader lands on, and the composite's own name does
        not propagate to it, so we name the child too. Plain controls just get a name.
        """
        ctrl.SetName(name)  # type: ignore[attr-defined]
        get_children = getattr(ctrl, "GetChildren", None)
        if not callable(get_children):
            return
        for child in get_children():
            if isinstance(child, self._wx.TextCtrl):
                child.SetName(name)

    def _add_book_field(self, grid: object, text: str, value: str) -> object:
        wx = self._wx
        grid.Add(wx.StaticText(self.dialog, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.TextCtrl(self.dialog, value=value)
        grid.Add(ctrl, 0, wx.EXPAND)
        return ctrl

    def _sync_book_enabled(self) -> None:
        """Enable the book fields only while 'Assemble into one audiobook' is on."""
        on = self._make_book.GetValue()
        for ctrl in self._book_controls:
            ctrl.Enable(on)

    def _current_book_format(self) -> str:
        idx = self._book_format.GetSelection()
        return _BOOK_FORMATS[idx] if 0 <= idx < len(_BOOK_FORMATS) else "m4b"

    def _sync_book_output_suffix(self) -> None:
        text = self._book_output.GetValue().strip()
        if not text:
            return
        path = Path(text)
        if not path.name:
            return
        self._book_output.SetValue(str(path.with_suffix(f".{self._current_book_format()}")))

    def _select_engine(self, engine_id: str) -> None:
        for i, (_lbl, eid) in enumerate(self._engine_options):
            if eid == engine_id:
                self._engine.SetSelection(i)
                return
        self._engine.SetSelection(0)

    def _current_engine_id(self) -> str:
        idx = self._engine.GetSelection()
        if 0 <= idx < len(self._engine_options):
            return self._engine_options[idx][1]
        return self._engine_options[0][1] if self._engine_options else "sapi5"

    def _reload_voices(self, *, initial_voice: str = "") -> None:
        engine_id = self._current_engine_id()
        self._voice_pairs = self._voices_for(engine_id)
        labels = [lbl for lbl, _vid in self._voice_pairs]
        self._voice.Set(labels)
        self._rr_pick.Set(labels)
        if labels:
            self._rr_pick.SetSelection(0)
        target = initial_voice
        chosen = 0
        for i, (_lbl, vid) in enumerate(self._voice_pairs):
            if vid == target:
                chosen = i
                break
        if self._voice_pairs:
            self._voice.SetSelection(chosen)

    def _on_engine_change(self) -> None:
        # Voices are engine-specific, so switching engines clears the rotation.
        self._reload_voices()
        self._rr_voices = []
        self._refresh_rr_list()

    def _current_voice_id(self) -> str:
        idx = self._voice.GetSelection()
        if 0 <= idx < len(self._voice_pairs):
            return self._voice_pairs[idx][1]
        return ""

    # -------------------------------------------------- round-robin voices

    def _seed_rotation(self, voice_ids: tuple[str, ...]) -> None:
        """Pre-fill the rotation from saved ids, mapping each to its current label."""
        by_id = {vid: lbl for lbl, vid in self._voice_pairs}
        self._rr_voices = [(vid, by_id[vid]) for vid in voice_ids if vid in by_id]
        self._refresh_rr_list()

    def _refresh_rr_list(self, *, select: int = -1) -> None:
        self._rr_list.Set([lbl for _vid, lbl in self._rr_voices])
        if self._rr_voices:
            index = select if 0 <= select < len(self._rr_voices) else 0
            self._rr_list.SetSelection(index)

    def _rr_selected_index(self) -> int:
        idx = self._rr_list.GetSelection()
        return idx if 0 <= idx < len(self._rr_voices) else -1

    def _on_rr_add(self) -> None:
        idx = self._rr_pick.GetSelection()
        if not (0 <= idx < len(self._voice_pairs)):
            return
        label, vid = self._voice_pairs[idx]
        if any(existing == vid for existing, _ in self._rr_voices):
            return  # already in the rotation
        self._rr_voices.append((vid, label))
        self._refresh_rr_list(select=len(self._rr_voices) - 1)

    def _on_rr_move(self, delta: int) -> None:
        idx = self._rr_selected_index()
        target = idx + delta
        if idx < 0 or not (0 <= target < len(self._rr_voices)):
            return
        self._rr_voices[idx], self._rr_voices[target] = (
            self._rr_voices[target],
            self._rr_voices[idx],
        )
        self._refresh_rr_list(select=target)

    def _on_rr_remove(self) -> None:
        idx = self._rr_selected_index()
        if idx < 0:
            return
        del self._rr_voices[idx]
        self._refresh_rr_list(select=min(idx, len(self._rr_voices) - 1))

    # -------------------------------------------------- translation targets

    def _current_tr_lang(self) -> tuple[str, str]:
        idx = self._tr_lang.GetSelection()
        return self._tr_lang_pairs[idx] if 0 <= idx < len(self._tr_lang_pairs) else ("", "")

    def _reload_tr_voices(self) -> None:
        from quill.core.speech.voice_languages import voices_for_language

        _name, code = self._current_tr_lang()
        # Local tiers first (eSpeak/SAPI), then the premium multilingual cloud voices
        # (OpenAI/Gemini/ElevenLabs) — each needs its provider API key at run time.
        self._tr_voice_opts = voices_for_language(code) if code else []
        self._tr_voice.Set([v.display for v in self._tr_voice_opts])
        if self._tr_voice_opts:
            self._tr_voice.SetSelection(0)

    def _refresh_tr_list(self, *, select: int = -1) -> None:
        self._tr_list.Set([t[3] for t in self._tr_targets])
        if self._tr_targets:
            index = select if 0 <= select < len(self._tr_targets) else 0
            self._tr_list.SetSelection(index)

    def _on_tr_add(self) -> None:
        name, code = self._current_tr_lang()
        vidx = self._tr_voice.GetSelection()
        if not code or not (0 <= vidx < len(self._tr_voice_opts)):
            return
        v = self._tr_voice_opts[vidx]
        if any(t[0] == code and t[2] == v.voice_id for t in self._tr_targets):
            return
        self._tr_targets.append((code, v.engine, v.voice_id, f"{name}: {v.display}"))
        self._refresh_tr_list(select=len(self._tr_targets) - 1)

    def _on_tr_remove(self) -> None:
        idx = self._tr_list.GetSelection()
        if 0 <= idx < len(self._tr_targets):
            del self._tr_targets[idx]
            self._refresh_tr_list(select=min(idx, len(self._tr_targets) - 1))

    def _seed_translations(self, targets: tuple[tuple[str, str, str], ...]) -> None:
        from quill.core.ai.translation import LANGUAGE_NAMES

        self._tr_targets = [
            (lang, engine, voice_id, f"{LANGUAGE_NAMES.get(lang, lang)}: {voice_id} — {engine}")
            for lang, engine, voice_id in targets
        ]
        self._refresh_tr_list()

    def _collect(self, *, preview: bool) -> BatchSpeechRequest:
        exts: list[str] = []
        for cb, ext in self._ext_boxes:
            if cb.GetValue():
                exts.extend(_EXTENSION_GROUPS.get(ext, (ext,)))
        policy_idx = self._on_existing.GetSelection()
        on_existing = _EXISTING_POLICIES[policy_idx] if 0 <= policy_idx < 3 else "overwrite"
        return BatchSpeechRequest(
            source_folder=Path(self._source.GetValue().strip()),
            recursive=self._recursive.GetValue(),
            extensions=tuple(exts),
            engine=self._current_engine_id(),
            voice=self._current_voice_id(),
            rate=int(self._rate.GetValue()),
            speed=float(self._speed.GetValue()),
            output_format=(
                _FORMAT_CHOICES[self._format.GetSelection()]
                if 0 <= self._format.GetSelection() < len(_FORMAT_CHOICES)
                else "mp3"
            ),
            sound_enabled=self._sound.GetValue(),
            sound_volume=int(self._sound_volume.GetValue()),
            article_gap_ms=int(self._article_gap.GetValue()),
            sentence_gap_ms=int(self._sentence_gap.GetValue()),
            tail_padding_ms=int(self._tail_padding.GetValue()),
            speak_headings=self._speak_headings.GetValue(),
            skip_existing=(on_existing == "skip"),
            include_glob=self._include.GetValue().strip(),
            exclude_glob=self._exclude.GetValue().strip(),
            on_existing=on_existing,
            chapter_mode=(
                _MODE_CHOICES[self._mode.GetSelection()]
                if 0 <= self._mode.GetSelection() < len(_MODE_CHOICES)
                else "single"
            ),
            dry_run=self._dry_run.GetValue(),
            preview=preview,
            combine_headings=self._combine.GetValue(),
            normalize_loudness=self._normalize.GetValue(),
            round_robin_voices=tuple(vid for vid, _lbl in self._rr_voices),
            translation_targets=tuple((c, e, v) for c, e, v, _ in self._tr_targets),
            translation_provider=(
                "libretranslate" if self._tr_provider.GetSelection() == 1 else "ai_assistant"
            ),
            temp_folder=self._temp_folder.GetValue().strip(),
            save_spoken_text=self._save_spoken.GetValue(),
            make_book=self._make_book.GetValue(),
            book_title=self._book_title.GetValue().strip(),
            book_author=self._book_author.GetValue().strip(),
            book_narrator=self._book_narrator.GetValue().strip(),
            book_genre=self._book_genre.GetValue().strip(),
            book_year=self._book_year.GetValue().strip(),
            book_cover_path=self._book_cover.GetValue().strip(),
            book_format=self._current_book_format(),
            book_output_path=self._book_output.GetValue().strip(),
            book_acx_normalize=self._book_acx.GetValue(),
            book_review_chapters=self._book_review.GetValue(),
        )

    # ------------------------------------------------------------------ events

    def _on_browse_source(self, _evt: object) -> None:
        wx = self._wx
        with wx.DirDialog(self.dialog, "Choose the folder of documents to convert") as dlg:
            # Native folder picker owned by this dialog; not a GATE-42 target stem.
            if dlg.ShowModal() == wx.ID_OK:
                self._source.SetValue(dlg.GetPath())

    def _on_browse_temp(self, _evt: object) -> None:
        wx = self._wx
        with wx.DirDialog(self.dialog, "Choose a folder for temporary files") as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native folder picker
                self._temp_folder.SetValue(dlg.GetPath())

    def _on_browse_cover(self, _evt: object) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Choose a cover image",
            wildcard="Images (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native file picker
                self._book_cover.SetValue(dlg.GetPath())

    def _on_browse_book_output(self, _evt: object) -> None:
        wx = self._wx
        fmt = self._current_book_format()
        with wx.FileDialog(
            self.dialog,
            "Save the audiobook as",
            wildcard=f"{fmt.upper()} (*.{fmt})|*.{fmt}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native file picker
                self._book_output.SetValue(str(Path(dlg.GetPath()).with_suffix(f".{fmt}")))

    def _on_preview_click(self, _evt: object) -> None:
        self._on_preview(self._collect(preview=True))

    def _on_start(self, evt: object) -> None:
        req = self._collect(preview=False)
        if not req.source_folder or not req.source_folder.is_dir():
            show_message_box(
                "Choose a source folder that exists.",
                "Batch Export to Speech Audio",
                self._wx.OK | self._wx.ICON_ERROR,
                self.dialog,
            )
            return
        # With audiobook assembly on, an empty file-type set is allowed: the run
        # assembles whatever audio is already in the folder (the pre-recorded case).
        if not req.extensions and not req.make_book:
            show_message_box(
                "Select at least one file type to include.",
                "Batch Export to Speech Audio",
                self._wx.OK | self._wx.ICON_ERROR,
                self.dialog,
            )
            return
        self._result = req
        evt.Skip()  # let ID_OK close the dialog

    # ------------------------------------------------------------------ public

    def show(self, show_modal_dialog: Callable[[object, str], int]) -> BatchSpeechRequest | None:
        """Open the dialog; return the collected request, or ``None`` on cancel."""
        code = show_modal_dialog(self.dialog, "Batch Export to Speech Audio")
        result = self._result if code == self._wx.ID_OK else None
        self.dialog.Destroy()
        return result
