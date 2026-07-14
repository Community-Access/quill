"""Audio Studio wizard — the document-narration journey pages.

Four pages: what to read (folder + types + filters), who reads it (engine,
voice, pace, round-robin rotation, translated editions), how chapters work
(mode, headings, the transition sounder, gaps), and output (format, existing-
file policy, mastering and diagnostics). Together they collect every field of
the classic Batch Export dialog — nothing is lost in the rebrand.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.i18n import _
from quill.ui.audio_studio.pages_base import StudioPage, set_accessible_name
from quill.ui.audio_studio.request import (
    ALL_EXTENSIONS,
    EXISTING_POLICIES,
    EXTENSION_GROUPS,
    FORMAT_CHOICES,
    FORMAT_INDEX,
    MODE_CHOICES,
    MODE_INDEX,
    BatchSpeechRequest,
)
from quill.ui.dialog_contract import apply_listbox_activation

# (label, engine_id) pairs, mirroring the Speech Hub's engine list.
EngineOptions = list[tuple[str, str]]
# engine_id -> [(voice_label, voice_id), ...]
VoicesFor = Callable[[str], list[tuple[str, str]]]


class DocSourcePage(StudioPage):
    """What should I read? Folder, file types, discovery filters, live count."""

    def __init__(
        self,
        parent: wx.Window,
        defaults: BatchSpeechRequest,
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            "audio_studio.doc_source",
            _("What should I read?"),
            _("Pick the folder of documents and which file types to include."),
        )
        self._announce_cb = announce
        self._count_generation = 0
        self.add_label(_("&Source folder (documents to convert):"))
        row = wx.BoxSizer(wx.HORIZONTAL)
        # A ComboBox lets the user pick from a recent-folders MRU
        # without retyping the path. Choices are seeded from the
        # Audio Studio's source-folder MRU on init; the Browse button
        # populates ``SetValue`` so the new path is offered on the next
        # launch. The current request's source is added as the first
        # non-duplicate choice so the default always shows.
        self._seed_source_choices(defaults.source_folder)
        self.source = wx.ComboBox(
            self,
            value=str(defaults.source_folder),
            choices=self._source_choices,
            style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
        )
        self.source.SetName(_("Source folder"))
        browse = wx.Button(self, label=_("B&rowse..."))
        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        row.Add(self.source, 1, wx.EXPAND | wx.RIGHT, 6)
        row.Add(browse, 0)
        self.sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.recursive = wx.CheckBox(self, label=_("Include su&bfolders"))
        self.recursive.SetValue(defaults.recursive)
        self.sizer.Add(self.recursive, 0, wx.LEFT | wx.TOP, 12)

        self.add_label(_("File &types to include:"))
        self.ext_boxes: list[tuple[wx.CheckBox, str]] = []
        ext_row = wx.BoxSizer(wx.HORIZONTAL)
        for text, ext in ALL_EXTENSIONS:
            cb = wx.CheckBox(self, label=_(text))
            cb.SetValue(ext in defaults.extensions)
            ext_row.Add(cb, 0, wx.RIGHT, 10)
            self.ext_boxes.append((cb, ext))
        self.sizer.Add(ext_row, 0, wx.LEFT | wx.TOP, 12)

        self.add_label(_("Only incl&ude files matching (globs, ; or , separated; blank = all):"))
        self.include = wx.TextCtrl(self, value=defaults.include_glob)
        self.include.SetName(_("Include files matching"))
        self.sizer.Add(self.include, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        self.add_label(_("E&xclude files matching (globs, ; or , separated):"))
        self.exclude = wx.TextCtrl(self, value=defaults.exclude_glob)
        self.exclude.SetName(_("Exclude files matching"))
        self.sizer.Add(self.exclude, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        size_row = wx.BoxSizer(wx.HORIZONTAL)
        size_row.Add(
            wx.StaticText(self, label=_("Skip files lar&ger than (MB, 0 = no limit):")),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self.max_mb = wx.SpinCtrl(
            self, min=0, max=4096, initial=max(0, defaults.max_file_bytes // (1024 * 1024))
        )
        set_accessible_name(self.max_mb, _("Skip files larger than (MB)"))
        size_row.Add(self.max_mb, 0, wx.LEFT, 6)
        self.sizer.Add(size_row, 0, wx.LEFT | wx.TOP, 12)

        count_row = wx.BoxSizer(wx.HORIZONTAL)
        count_btn = wx.Button(self, label=_("Coun&t documents"))
        count_btn.Bind(wx.EVT_BUTTON, lambda _e: self.start_count())
        self._count_label = wx.StaticText(
            self,
            label=_("Press Count documents to preview the run."),
            name="audio_studio.doc_count",
        )
        count_row.Add(count_btn, 0, wx.RIGHT, 8)
        count_row.Add(self._count_label, 1, wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(count_row, 0, wx.EXPAND | wx.LEFT | wx.TOP, 12)

    def _seed_source_choices(self, current: str) -> None:
        """Populate ``self._source_choices`` from the MRU plus the current value.

        The current value always appears first; the MRU follows in most-
        recently-used order. The ComboBox's dropdown is then a one-keystroke
        list of recent folders, which is what the screen-reader user wants
        for the second run.
        """
        try:
            from quill.core.recent import recent_audio_source_folders

            mru = [str(p) for p in recent_audio_source_folders()]
        except Exception:  # noqa: BLE001 - MRU read is best-effort
            mru = []
        seen: set[str] = set()
        ordered: list[str] = []
        if current:
            ordered.append(str(current))
            seen.add(str(current))
        for entry in mru:
            if entry in seen:
                continue
            seen.add(entry)
            ordered.append(entry)
        self._source_choices = ordered

    def _on_browse(self, _evt: wx.Event) -> None:
        with wx.DirDialog(self, _("Choose the folder of documents to convert")) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native folder picker
                self.source.SetValue(dlg.GetPath())
                # Reseed the dropdown so the freshly-picked folder is
                # offered on the next run without waiting for settings.
                self._seed_source_choices(dlg.GetPath())
                self.source.SetItems(self._source_choices)
                self.source.SetValue(dlg.GetPath())
                self.start_count()

    def on_shown(self, req: BatchSpeechRequest) -> None:
        self.start_count()

    def start_count(self) -> None:
        """Count matching documents and words off the UI thread; announce when settled."""
        import threading

        folder_text = self.source.GetValue().strip()
        extensions = self.selected_extensions()
        if not folder_text or not Path(folder_text).is_dir() or not extensions:
            return
        self._count_generation += 1
        generation = self._count_generation
        include = self.include.GetValue().strip()
        exclude = self.exclude.GetValue().strip()
        recursive = self.recursive.GetValue()
        max_bytes = int(self.max_mb.GetValue()) * 1024 * 1024
        self._count_label.SetLabel(_("Counting..."))

        def work() -> None:
            from quill.core.speech.batch_export import count_document_words, discover_files

            try:
                files = discover_files(
                    Path(folder_text),
                    list(extensions),
                    recursive,
                    include_glob=include,
                    exclude_glob=exclude,
                    max_file_bytes=max_bytes,
                )
                words = sum(count_document_words(f) for f in files)
            except Exception:  # noqa: BLE001 - a broken folder just shows no count
                return
            message = _("{count} document(s) found, about {words:,} words.").format(
                count=len(files), words=words
            )

            def apply() -> None:
                # A newer count superseded this one while it was running.
                if generation != self._count_generation or not self:
                    return
                self._count_label.SetLabel(message)
                if self._announce_cb is not None and self.IsShown():
                    self._announce_cb(str(message))

            wx.CallAfter(apply)

        threading.Thread(target=work, name="audio-studio-count", daemon=True).start()

    def selected_extensions(self) -> tuple[str, ...]:
        exts: list[str] = []
        for cb, ext in self.ext_boxes:
            if cb.GetValue():
                exts.extend(EXTENSION_GROUPS.get(ext, (ext,)))
        return tuple(exts)

    def collect(self, req: BatchSpeechRequest) -> None:
        req.source_folder = Path(self.source.GetValue().strip())
        req.recursive = self.recursive.GetValue()
        req.extensions = self.selected_extensions()
        req.include_glob = self.include.GetValue().strip()
        req.exclude_glob = self.exclude.GetValue().strip()
        req.max_file_bytes = int(self.max_mb.GetValue()) * 1024 * 1024

    def is_valid(self) -> tuple[bool, str]:
        text = self.source.GetValue().strip()
        if not text or not Path(text).is_dir():
            return False, _("Choose a source folder that exists.")
        if not self.selected_extensions():
            return False, _("Select at least one file type to include.")
        return True, ""


class VoicesPage(StudioPage):
    """Who should read it? Engine, voice, pace, rotation, translated editions."""

    def __init__(
        self,
        parent: wx.Window,
        defaults: BatchSpeechRequest,
        *,
        engine_options: EngineOptions,
        engine_available: dict[str, bool],
        voices_for: VoicesFor,
        on_preview: Callable[[str, str], None],
    ) -> None:
        super().__init__(
            parent,
            "audio_studio.voices",
            _("Who should read it?"),
            _("Choose the voice — or a whole cast — and hear a preview."),
        )
        self._engine_options = engine_options
        self._engine_available = engine_available
        self._voices_for = voices_for
        self._on_preview = on_preview
        self._voice_pairs: list[tuple[str, str]] = []
        # Round-robin rotation: ordered (voice_id, label) for the selected engine.
        self._rr_voices: list[tuple[str, str]] = []
        # Translation targets: ordered (lang_code, engine, voice_id, display_label).
        self._tr_targets: list[tuple[str, str, str, str]] = []

        self.add_label(_("&Engine:"))
        self.engine = wx.Choice(
            self, choices=[self._engine_label(lbl, eid) for lbl, eid in engine_options]
        )
        self.engine.SetName(_("Engine"))
        self.engine.Bind(wx.EVT_CHOICE, lambda _e: self._on_engine_change())
        self.sizer.Add(self.engine, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        self.select_engine(defaults.engine)

        self.add_label(_("&Voice:"))
        voice_row = wx.BoxSizer(wx.HORIZONTAL)
        self.voice = wx.Choice(self, choices=[])
        self.voice.SetName(_("Voice"))
        preview_btn = wx.Button(self, label=_("&Preview voice"))
        preview_btn.Bind(wx.EVT_BUTTON, self._on_preview_click)
        voice_row.Add(self.voice, 1, wx.EXPAND | wx.RIGHT, 6)
        voice_row.Add(preview_btn, 0)
        self.sizer.Add(voice_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        pace_row = wx.BoxSizer(wx.HORIZONTAL)
        pace_row.Add(wx.StaticText(self, label=_("R&ate (WPM):")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.rate = wx.SpinCtrl(self, min=80, max=450, initial=defaults.rate)
        set_accessible_name(self.rate, _("Rate (WPM)"))
        pace_row.Add(self.rate, 0, wx.LEFT | wx.RIGHT, 6)
        pace_row.Add(wx.StaticText(self, label=_("&Kokoro speed:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.speed = wx.SpinCtrlDouble(self, min=0.5, max=2.0, inc=0.05, initial=defaults.speed)
        set_accessible_name(self.speed, _("Kokoro speed"))
        pace_row.Add(self.speed, 0, wx.LEFT, 6)
        self.sizer.Add(pace_row, 0, wx.LEFT | wx.TOP, 12)

        # --- Round-robin voices (optional) ---
        self.add_label(_("Round-&robin voices (each article gets the next voice; optional):"))
        rr_add_row = wx.BoxSizer(wx.HORIZONTAL)
        self.rr_pick = wx.Choice(self, choices=[])
        self.rr_pick.SetName(_("Round-robin voice to add"))
        rr_add = wx.Button(self, label=_("A&dd voice"))
        rr_add.Bind(wx.EVT_BUTTON, lambda _e: self.rr_add())
        rr_add_row.Add(self.rr_pick, 1, wx.EXPAND | wx.RIGHT, 6)
        rr_add_row.Add(rr_add, 0)
        self.sizer.Add(rr_add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        # A dedicated label immediately before the list: a screen reader names a list
        # from its preceding StaticText, so SetName alone leaves it announced unnamed.
        self.add_label(_("Voice o&rder (the rotation; use the buttons below to reorder):"))
        self.rr_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self.rr_list.SetName(_("Round-robin voice order"))
        apply_listbox_activation(self.rr_list, lambda _e: self.rr_pick.SetFocus())
        self.sizer.Add(self.rr_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        rr_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        rr_up = wx.Button(self, label=_("Move U&p"))
        rr_down = wx.Button(self, label=_("Move Dow&n"))
        rr_remove = wx.Button(self, label=_("Re&move"))
        rr_up.Bind(wx.EVT_BUTTON, lambda _e: self.rr_move(-1))
        rr_down.Bind(wx.EVT_BUTTON, lambda _e: self.rr_move(1))
        rr_remove.Bind(wx.EVT_BUTTON, lambda _e: self.rr_remove())
        for btn in (rr_up, rr_down, rr_remove):
            rr_btn_row.Add(btn, 0, wx.RIGHT, 6)
        self.sizer.Add(rr_btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # --- Voice casting (optional; overrides the rotation per section) ---
        self.add_label(
            _(
                "Voice cas&ting (optional): assign a voice to matching chapters."
                " Patterns match the heading title (Chapter *, *interview*) or a"
                " section number (#1). First match wins; others use the rotation."
            )
        )
        cast_add_row = wx.BoxSizer(wx.HORIZONTAL)
        self.cast_pattern = wx.TextCtrl(self)
        self.cast_pattern.SetName(_("Casting pattern (title glob or #number)"))
        self.cast_pattern.SetHint(_("Chapter * or #1"))
        self.cast_pick = wx.Choice(self, choices=[])
        self.cast_pick.SetName(_("Casting voice"))
        cast_add = wx.Button(self, label=_("Add r&ule"))
        cast_add.Bind(wx.EVT_BUTTON, lambda _e: self.cast_add())
        cast_add_row.Add(self.cast_pattern, 1, wx.EXPAND | wx.RIGHT, 6)
        cast_add_row.Add(self.cast_pick, 1, wx.EXPAND | wx.RIGHT, 6)
        cast_add_row.Add(cast_add, 0)
        self.sizer.Add(cast_add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.add_label(_("Casting rules (first match &wins):"))
        self.cast_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self.cast_list.SetName(_("Casting rules"))
        apply_listbox_activation(self.cast_list, lambda _e: self.cast_pattern.SetFocus())
        self.sizer.Add(self.cast_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        cast_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        cast_remove = wx.Button(self, label=_("Remove rule"))
        cast_remove.Bind(wx.EVT_BUTTON, lambda _e: self.cast_remove())
        cast_btn_row.Add(cast_remove, 0)
        self.sizer.Add(cast_btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        # Ordered (pattern, voice_id, display label) rows.
        self._cast_rules: list[tuple[str, str, str]] = []

        # --- Translated editions (optional) ---
        self.add_label(_("Also export in other &languages (translated):"))
        from quill.core.ai.translation import SUPPORTED_LANGUAGES

        self._tr_lang_pairs = sorted(SUPPORTED_LANGUAGES.items())  # (name, code)
        self._tr_voice_opts: list = []
        tr_add_row = wx.BoxSizer(wx.HORIZONTAL)
        self.tr_lang = wx.Choice(self, choices=[name for name, _c in self._tr_lang_pairs])
        self.tr_lang.SetName(_("Translation language"))
        self.tr_lang.Bind(wx.EVT_CHOICE, lambda _e: self.reload_tr_voices())
        self.tr_voice = wx.Choice(self, choices=[])
        self.tr_voice.SetName(_("Translation voice"))
        tr_add = wx.Button(self, label=_("Add lan&guage"))
        tr_add.Bind(wx.EVT_BUTTON, lambda _e: self.tr_add())
        tr_add_row.Add(self.tr_lang, 1, wx.EXPAND | wx.RIGHT, 6)
        tr_add_row.Add(self.tr_voice, 2, wx.EXPAND | wx.RIGHT, 6)
        tr_add_row.Add(tr_add, 0)
        self.sizer.Add(tr_add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.add_label(_("Languages &chosen (translated exports):"))
        self.tr_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self.tr_list.SetName(_("Translation targets"))
        apply_listbox_activation(self.tr_list, lambda _e: self.tr_lang.SetFocus())
        self.sizer.Add(self.tr_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        tr_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        tr_remove = wx.Button(self, label=_("Remove la&nguage"))
        tr_remove.Bind(wx.EVT_BUTTON, lambda _e: self.tr_remove())
        tr_btn_row.Add(tr_remove, 0, wx.RIGHT, 6)
        tr_btn_row.Add(
            wx.StaticText(self, label=_("Trans&late with:")), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.tr_provider = wx.Choice(
            self, choices=[_("AI provider (cloud)"), _("LibreTranslate (local)")]
        )
        self.tr_provider.SetName(_("Translate with"))
        self.tr_provider.SetSelection(1 if defaults.translation_provider == "libretranslate" else 0)
        tr_btn_row.Add(self.tr_provider, 0, wx.LEFT, 6)
        self.sizer.Add(tr_btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.reload_voices(initial_voice=defaults.voice)
        self.seed_rotation(defaults.round_robin_voices)
        self.seed_casting(defaults.casting_rules)
        self.reload_tr_voices()
        self.seed_translations(defaults.translation_targets)

    # -- engine / voice -------------------------------------------------------

    def _engine_label(self, label: str, engine_id: str) -> str:
        if not self._engine_available.get(engine_id, True):
            return _("{engine} (not installed)").format(engine=label)
        return label

    def select_engine(self, engine_id: str) -> None:
        for i, (_lbl, eid) in enumerate(self._engine_options):
            if eid == engine_id:
                self.engine.SetSelection(i)
                return
        self.engine.SetSelection(0)

    def current_engine_id(self) -> str:
        idx = self.engine.GetSelection()
        if 0 <= idx < len(self._engine_options):
            return self._engine_options[idx][1]
        return self._engine_options[0][1] if self._engine_options else "sapi5"

    def reload_voices(self, *, initial_voice: str = "") -> None:
        engine_id = self.current_engine_id()
        self._voice_pairs = self._voices_for(engine_id)
        labels = [lbl for lbl, _vid in self._voice_pairs]
        self.voice.Set(labels)
        self.rr_pick.Set(labels)
        self.cast_pick.Set(labels)
        if labels:
            self.rr_pick.SetSelection(0)
            self.cast_pick.SetSelection(0)
        chosen = 0
        for i, (_lbl, vid) in enumerate(self._voice_pairs):
            if vid == initial_voice:
                chosen = i
                break
        if self._voice_pairs:
            self.voice.SetSelection(chosen)

    def _on_engine_change(self) -> None:
        # Voices are engine-specific, so switching engines clears the rotation
        # and the casting rules (both name voices of the previous engine).
        self.reload_voices()
        self._rr_voices = []
        self._refresh_rr_list()
        self._cast_rules = []
        self._refresh_cast_list()

    def current_voice_id(self) -> str:
        idx = self.voice.GetSelection()
        if 0 <= idx < len(self._voice_pairs):
            return self._voice_pairs[idx][1]
        return ""

    def _on_preview_click(self, _evt: wx.Event) -> None:
        self._on_preview(self.current_engine_id(), self.current_voice_id())

    # -- round-robin rotation --------------------------------------------------

    def seed_rotation(self, voice_ids: tuple[str, ...]) -> None:
        """Pre-fill the rotation from saved ids, mapping each to its current label."""
        by_id = {vid: lbl for lbl, vid in self._voice_pairs}
        self._rr_voices = [(vid, by_id[vid]) for vid in voice_ids if vid in by_id]
        self._refresh_rr_list()

    def _refresh_rr_list(self, *, select: int = -1) -> None:
        self.rr_list.Set([lbl for _vid, lbl in self._rr_voices])
        if self._rr_voices:
            index = select if 0 <= select < len(self._rr_voices) else 0
            self.rr_list.SetSelection(index)

    def _rr_selected_index(self) -> int:
        idx = self.rr_list.GetSelection()
        return idx if 0 <= idx < len(self._rr_voices) else -1

    def rr_add(self) -> None:
        idx = self.rr_pick.GetSelection()
        if not (0 <= idx < len(self._voice_pairs)):
            return
        label, vid = self._voice_pairs[idx]
        if any(existing == vid for existing, _ in self._rr_voices):
            return  # already in the rotation
        self._rr_voices.append((vid, label))
        self._refresh_rr_list(select=len(self._rr_voices) - 1)

    def rr_move(self, delta: int) -> None:
        idx = self._rr_selected_index()
        target = idx + delta
        if idx < 0 or not (0 <= target < len(self._rr_voices)):
            return
        self._rr_voices[idx], self._rr_voices[target] = (
            self._rr_voices[target],
            self._rr_voices[idx],
        )
        self._refresh_rr_list(select=target)

    def rr_remove(self) -> None:
        idx = self._rr_selected_index()
        if idx < 0:
            return
        del self._rr_voices[idx]
        self._refresh_rr_list(select=min(idx, len(self._rr_voices) - 1))

    # -- voice casting -----------------------------------------------------------

    def seed_casting(self, rules: tuple[tuple[str, str], ...]) -> None:
        """Pre-fill the casting rules from saved (pattern, voice id) pairs."""
        by_id = {vid: lbl for lbl, vid in self._voice_pairs}
        self._cast_rules = [
            (pattern, vid, f"{pattern} = {by_id[vid]}")
            for pattern, vid in rules
            if vid in by_id and pattern.strip()
        ]
        self._refresh_cast_list()

    def _refresh_cast_list(self, *, select: int = -1) -> None:
        self.cast_list.Set([label for _p, _v, label in self._cast_rules])
        if self._cast_rules:
            index = select if 0 <= select < len(self._cast_rules) else 0
            self.cast_list.SetSelection(index)

    def cast_add(self) -> None:
        pattern = self.cast_pattern.GetValue().strip()
        idx = self.cast_pick.GetSelection()
        if not pattern or not (0 <= idx < len(self._voice_pairs)):
            return
        label, vid = self._voice_pairs[idx]
        if any(p == pattern for p, _v, _l in self._cast_rules):
            return  # one rule per pattern; remove it to reassign
        self._cast_rules.append((pattern, vid, f"{pattern} = {label}"))
        self._refresh_cast_list(select=len(self._cast_rules) - 1)
        self.cast_pattern.SetValue("")

    def cast_remove(self) -> None:
        idx = self.cast_list.GetSelection()
        if 0 <= idx < len(self._cast_rules):
            del self._cast_rules[idx]
            self._refresh_cast_list(select=min(idx, len(self._cast_rules) - 1))

    # -- translated editions ----------------------------------------------------

    def _current_tr_lang(self) -> tuple[str, str]:
        idx = self.tr_lang.GetSelection()
        return self._tr_lang_pairs[idx] if 0 <= idx < len(self._tr_lang_pairs) else ("", "")

    def reload_tr_voices(self) -> None:
        from quill.core.speech.voice_languages import voices_for_language

        _name, code = self._current_tr_lang()
        # Local tiers first (eSpeak/SAPI), then the premium multilingual cloud voices
        # (OpenAI/Gemini/ElevenLabs) — each needs its provider API key at run time.
        self._tr_voice_opts = voices_for_language(code) if code else []
        self.tr_voice.Set([v.display for v in self._tr_voice_opts])
        if self._tr_voice_opts:
            self.tr_voice.SetSelection(0)

    def _refresh_tr_list(self, *, select: int = -1) -> None:
        self.tr_list.Set([t[3] for t in self._tr_targets])
        if self._tr_targets:
            index = select if 0 <= select < len(self._tr_targets) else 0
            self.tr_list.SetSelection(index)

    def tr_add(self) -> None:
        name, code = self._current_tr_lang()
        vidx = self.tr_voice.GetSelection()
        if not code or not (0 <= vidx < len(self._tr_voice_opts)):
            return
        v = self._tr_voice_opts[vidx]
        if any(t[0] == code and t[2] == v.voice_id for t in self._tr_targets):
            return
        self._tr_targets.append((code, v.engine, v.voice_id, f"{name}: {v.display}"))
        self._refresh_tr_list(select=len(self._tr_targets) - 1)

    def tr_remove(self) -> None:
        idx = self.tr_list.GetSelection()
        if 0 <= idx < len(self._tr_targets):
            del self._tr_targets[idx]
            self._refresh_tr_list(select=min(idx, len(self._tr_targets) - 1))

    def seed_translations(self, targets: tuple[tuple[str, str, str], ...]) -> None:
        from quill.core.ai.translation import LANGUAGE_NAMES

        self._tr_targets = [
            (lang, engine, voice_id, f"{LANGUAGE_NAMES.get(lang, lang)}: {voice_id} — {engine}")
            for lang, engine, voice_id in targets
        ]
        self._refresh_tr_list()

    # -- collect ------------------------------------------------------------------

    def collect(self, req: BatchSpeechRequest) -> None:
        req.engine = self.current_engine_id()
        req.voice = self.current_voice_id()
        req.rate = int(self.rate.GetValue())
        req.speed = float(self.speed.GetValue())
        req.round_robin_voices = tuple(vid for vid, _lbl in self._rr_voices)
        req.casting_rules = tuple((p, v) for p, v, _lbl in self._cast_rules)
        req.translation_targets = tuple((c, e, v) for c, e, v, _ in self._tr_targets)
        req.translation_provider = (
            "libretranslate" if self.tr_provider.GetSelection() == 1 else "ai_assistant"
        )


_HEADING_LEVEL_CHOICES: tuple[tuple[str, int], ...] = (
    ("Every heading starts a chapter", 0),
    ("Level 1 headings only", 1),
    ("Levels 1 and 2", 2),
    ("Levels 1 to 3", 3),
)


class ChaptersPage(StudioPage):
    """How should chapters work? Mode, headings, the transition sounder, gaps."""

    def __init__(
        self,
        parent: wx.Window,
        defaults: BatchSpeechRequest,
        *,
        source_provider: Callable[[], BatchSpeechRequest] | None = None,
    ) -> None:
        super().__init__(
            parent,
            "audio_studio.chapters",
            _("How should chapters work?"),
            _("Shape the chapter structure and the sound between chapters."),
        )
        self._source_provider = source_provider
        self._preview_generation = 0
        self.add_label(_("Chapter &mode:"))
        self.mode = wx.Choice(
            self,
            choices=[_("Single chaptered file"), _("Separate file per article")],
        )
        self.mode.SetName(_("Chapter mode"))
        self.mode.SetSelection(MODE_INDEX.get(defaults.chapter_mode, 0))
        self.sizer.Add(self.mode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        level_row = wx.BoxSizer(wx.HORIZONTAL)
        level_row.Add(
            wx.StaticText(self, label=_("Chapters start at heading le&vel:")),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self.heading_level = wx.Choice(
            self, choices=[_(label) for label, _lvl in _HEADING_LEVEL_CHOICES]
        )
        self.heading_level.SetName(_("Chapters start at heading level"))
        level_index = next(
            (
                i
                for i, (_l, lvl) in enumerate(_HEADING_LEVEL_CHOICES)
                if lvl == defaults.chapter_heading_level
            ),
            0,
        )
        self.heading_level.SetSelection(level_index)
        preview_btn = wx.Button(self, label=_("Preview chapter titles"))
        preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self.start_title_preview())
        level_row.Add(self.heading_level, 0, wx.LEFT | wx.RIGHT, 6)
        level_row.Add(preview_btn, 0)
        self.sizer.Add(level_row, 0, wx.LEFT | wx.TOP, 12)
        self.add_label(_("First chapter titles this choice would produce:"))
        self.title_preview = wx.ListBox(self, style=wx.LB_SINGLE)
        self.title_preview.SetName(_("Chapter title preview"))
        self.title_preview.SetMinSize(wx.Size(-1, 120))
        self.sizer.Add(self.title_preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.speak_headings = wx.CheckBox(self, label=_("Speak each &heading aloud"))
        self.speak_headings.SetValue(defaults.speak_headings)
        self.sizer.Add(self.speak_headings, 0, wx.LEFT | wx.TOP, 12)
        self.combine = wx.CheckBox(self, label=_("&Combine empty headings into the next article"))
        self.combine.SetValue(defaults.combine_headings)
        self.sizer.Add(self.combine, 0, wx.LEFT | wx.TOP, 12)
        self.sound = wx.CheckBox(self, label=_("Play a transition s&ounder between headings"))
        self.sound.SetValue(defaults.sound_enabled)
        self.sizer.Add(self.sound, 0, wx.LEFT | wx.TOP, 12)

        gap_grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        self.sound_volume = self.add_ms_spin(
            gap_grid, _("Sounder &volume (0-100):"), defaults.sound_volume, hi=100
        )
        self.article_gap = self.add_ms_spin(
            gap_grid, _("Pause between &articles (ms):"), defaults.article_gap_ms
        )
        self.sentence_gap = self.add_ms_spin(
            gap_grid, _("Pause between se&ntences (ms):"), defaults.sentence_gap_ms
        )
        self.tail_padding = self.add_ms_spin(
            gap_grid,
            _("Trailing pad per section, anti-cli&pping (ms):"),
            defaults.tail_padding_ms,
        )
        self.sizer.Add(gap_grid, 0, wx.LEFT | wx.TOP, 12)

    def current_heading_level(self) -> int:
        idx = self.heading_level.GetSelection()
        if 0 <= idx < len(_HEADING_LEVEL_CHOICES):
            return _HEADING_LEVEL_CHOICES[idx][1]
        return 0

    def start_title_preview(self) -> None:
        """List the first 20 chapter titles the level choice would carve, off-thread."""
        import threading

        if self._source_provider is None:
            return
        req = self._source_provider()
        if not req.source_folder.is_dir() or not req.extensions:
            self.title_preview.Set([str(_("Choose a source folder first."))])
            return
        self._preview_generation += 1
        generation = self._preview_generation
        max_level = self.current_heading_level()
        combine = self.combine.GetValue()
        self.title_preview.Set([str(_("Reading the documents..."))])

        def work() -> None:
            from quill.core.speech.batch_export import discover_files
            from quill.core.speech.text_polish import preview_chapter_titles

            try:
                files = discover_files(
                    req.source_folder,
                    list(req.extensions),
                    req.recursive,
                    include_glob=req.include_glob,
                    exclude_glob=req.exclude_glob,
                    max_file_bytes=req.max_file_bytes,
                )
                titles = preview_chapter_titles(
                    files, combine_headings=combine, max_heading_level=max_level, limit=20
                )
            except Exception:  # noqa: BLE001 - a broken folder shows an empty preview
                titles = []

            def apply() -> None:
                if generation != self._preview_generation or not self:
                    return
                if titles:
                    self.title_preview.Set([
                        f"{i}. {title}" for i, title in enumerate(titles, start=1)
                    ])
                else:
                    self.title_preview.Set([str(_("No chapters would be produced."))])

            wx.CallAfter(apply)

        threading.Thread(target=work, name="audio-studio-preview", daemon=True).start()

    def collect(self, req: BatchSpeechRequest) -> None:
        idx = self.mode.GetSelection()
        req.chapter_mode = MODE_CHOICES[idx] if 0 <= idx < len(MODE_CHOICES) else "single"
        req.chapter_heading_level = self.current_heading_level()
        req.speak_headings = self.speak_headings.GetValue()
        req.combine_headings = self.combine.GetValue()
        req.sound_enabled = self.sound.GetValue()
        req.sound_volume = int(self.sound_volume.GetValue())
        req.article_gap_ms = int(self.article_gap.GetValue())
        req.sentence_gap_ms = int(self.sentence_gap.GetValue())
        req.tail_padding_ms = int(self.tail_padding.GetValue())


class OutputPage(StudioPage):
    """Where does the audio go? Format, existing-file policy, diagnostics."""

    def __init__(self, parent: wx.Window, defaults: BatchSpeechRequest) -> None:
        super().__init__(
            parent,
            "audio_studio.output",
            _("Output and diagnostics"),
            _("Choose the audio format and what happens to existing files."),
        )
        self.add_label(_("Output &format:"))
        self.format = wx.Choice(
            self,
            choices=[
                _("MP3 (with chapter markers)"),
                _("M4B audiobook (native chapters)"),
                _("WAV"),
            ],
        )
        self.format.SetName(_("Output format"))
        self.format.SetSelection(FORMAT_INDEX.get(defaults.output_format, 0))
        self.sizer.Add(self.format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.add_label(_("If an audio file already e&xists:"))
        self.on_existing = wx.Choice(
            self, choices=[_("Skip (resume)"), _("Overwrite"), _("Rename (keep both)")]
        )
        self.on_existing.SetName(_("If an audio file already exists"))
        policy = "skip" if defaults.skip_existing else defaults.on_existing
        policy_idx = EXISTING_POLICIES.index(policy) if policy in EXISTING_POLICIES else 1
        self.on_existing.SetSelection(policy_idx)
        self.sizer.Add(self.on_existing, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.normalize = wx.CheckBox(self, label=_("Normalize &loudness to audiobook (ACX) level"))
        self.normalize.SetValue(defaults.normalize_loudness)
        self.sizer.Add(self.normalize, 0, wx.LEFT | wx.TOP, 12)
        self.reuse = wx.CheckBox(
            self,
            label=_("Reuse unchan&ged audio from the last run (incremental rebuild)"),
        )
        self.reuse.SetValue(defaults.reuse_unchanged)
        self.sizer.Add(self.reuse, 0, wx.LEFT | wx.TOP, 12)
        self.dry_run = wx.CheckBox(
            self, label=_("Dr&y run: write preview text only (don't synthesize)")
        )
        self.dry_run.SetValue(defaults.dry_run)
        self.sizer.Add(self.dry_run, 0, wx.LEFT | wx.TOP, 12)
        self.save_spoken = wx.CheckBox(
            self, label=_("Save the te&xt sent to speech (one sidecar per document)")
        )
        self.save_spoken.SetValue(defaults.save_spoken_text)
        self.sizer.Add(self.save_spoken, 0, wx.LEFT | wx.TOP, 12)
        self.audition = wx.CheckBox(
            self,
            label=_("A&udition: convert only the first document, so you can judge the result"),
        )
        self.audition.SetValue(defaults.audition)
        self.sizer.Add(self.audition, 0, wx.LEFT | wx.TOP, 12)

        self.add_label(_("&Temporary files folder (blank = system temp):"))
        tmp_row = wx.BoxSizer(wx.HORIZONTAL)
        self.temp_folder = wx.TextCtrl(self, value=defaults.temp_folder)
        self.temp_folder.SetName(_("Temporary files folder"))
        tmp_browse = wx.Button(self, label=_("Browse temp&..."))
        tmp_browse.Bind(wx.EVT_BUTTON, self._on_browse_temp)
        tmp_row.Add(self.temp_folder, 1, wx.EXPAND | wx.RIGHT, 6)
        tmp_row.Add(tmp_browse, 0)
        self.sizer.Add(tmp_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

    def _on_browse_temp(self, _evt: wx.Event) -> None:
        with wx.DirDialog(self, _("Choose a folder for temporary files")) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native folder picker
                self.temp_folder.SetValue(dlg.GetPath())

    def collect(self, req: BatchSpeechRequest) -> None:
        fidx = self.format.GetSelection()
        req.output_format = FORMAT_CHOICES[fidx] if 0 <= fidx < len(FORMAT_CHOICES) else "mp3"
        pidx = self.on_existing.GetSelection()
        req.on_existing = EXISTING_POLICIES[pidx] if 0 <= pidx < 3 else "overwrite"
        req.skip_existing = req.on_existing == "skip"
        req.normalize_loudness = self.normalize.GetValue()
        req.reuse_unchanged = self.reuse.GetValue()
        req.dry_run = self.dry_run.GetValue()
        req.save_spoken_text = self.save_spoken.GetValue()
        req.audition = self.audition.GetValue()
        req.temp_folder = self.temp_folder.GetValue().strip()
