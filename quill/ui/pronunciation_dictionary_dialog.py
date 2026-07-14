"""Pronunciation manager — create/edit how QUILL speaks specific words (§4.7.5).

Two keyboard-first ``wx.Dialog`` surfaces backed by the wx-free pronunciation
core (:mod:`quill.core.speech.pronunciation`):

- :class:`PronunciationEntryDialog` — add/edit one term -> spoken-as mapping,
  showing the resulting spoken form so the user sees the effect before saving.
- :class:`PronunciationDictionaryDialog` — manage dictionaries and their entries,
  with an "Enabled for export" toggle that drives which dictionaries apply.

``run_pronunciation_manager(frame)`` is the menu entry point. Corrections made
here take effect everywhere the shared pipeline runs (batch export today; live
read-aloud as that path is wired). All controls are parented directly on the
dialog (NVDA focus rule) and OK/Cancel ids go through ``apply_modal_ids``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.speech.pronunciation import (
    PronunciationDictionary,
    PronunciationEntry,
    delete_dictionary,
    install_starter_dictionary,
    load_dictionaries,
    save_dictionary,
)
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    set_accessible_name,
    show_message_box,
)


class PronunciationEntryDialog:
    """Edit one pronunciation entry (term + how it should be spoken)."""

    def __init__(
        self,
        parent: object,
        entry: PronunciationEntry,
        *,
        on_audition: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_audition = on_audition
        self._result: PronunciationEntry | None = None

        self.dialog = wx.Dialog(parent, title="Pronunciation Entry")
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Word or phrase:"), 0, wx.ALL, 6)
        self._term = wx.TextCtrl(self.dialog, value=entry.term)
        set_accessible_name(self._term, "Word or phrase")
        root.Add(self._term, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # SSML entries keep their markup in `replacement`; the visible field shows
        # the plain fallback (what non-SSML engines speak). Respelling entries show
        # the replacement directly.
        self._mode = entry.mode if entry.mode in ("respelling", "ssml") else "respelling"
        self._ssml_fragment = entry.replacement if self._mode == "ssml" else ""
        spoken_value = entry.plain_fallback if self._mode == "ssml" else entry.replacement

        root.Add(
            wx.StaticText(self.dialog, label="&Spoken as (spell it how it sounds):"), 0, wx.ALL, 6
        )
        self._spoken = wx.TextCtrl(self.dialog, value=spoken_value)
        set_accessible_name(self._spoken, "Spoken as, spell it how it sounds")
        root.Add(self._spoken, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        ssml_row = wx.BoxSizer(wx.HORIZONTAL)
        build = wx.Button(self.dialog, label="Build SS&ML...")
        build.Bind(wx.EVT_BUTTON, self._on_build_ssml)
        self._mode_label = wx.StaticText(self.dialog, label="")
        ssml_row.Add(build, 0, wx.RIGHT, 8)
        ssml_row.Add(self._mode_label, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(ssml_row, 0, wx.LEFT | wx.TOP, 6)

        self._whole = wx.CheckBox(self.dialog, label="Match &whole word only")
        self._whole.SetValue(entry.whole_word)
        root.Add(self._whole, 0, wx.ALL, 6)
        self._case = wx.CheckBox(self.dialog, label="Case &sensitive")
        self._case.SetValue(entry.case_sensitive)
        root.Add(self._case, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self._preview = wx.StaticText(self.dialog, label="")
        root.Add(self._preview, 0, wx.ALL, 6)
        self._term.Bind(wx.EVT_TEXT, lambda _e: self._refresh_preview())
        self._spoken.Bind(wx.EVT_TEXT, lambda _e: self._refresh_preview())

        # Audition: hear the word as the engine says it today vs. with this entry.
        if on_audition is not None:
            hear = wx.BoxSizer(wx.HORIZONTAL)
            orig = wx.Button(self.dialog, label="Play &original")
            corr = wx.Button(self.dialog, label="Play &corrected")
            orig.Bind(wx.EVT_BUTTON, lambda _e: self._audition(self._term.GetValue()))
            corr.Bind(
                wx.EVT_BUTTON,
                lambda _e: self._audition(self._spoken.GetValue().strip() or self._term.GetValue()),
            )
            hear.Add(orig, 0, wx.RIGHT, 6)
            hear.Add(corr, 0)
            root.Add(hear, 0, wx.LEFT | wx.BOTTOM, 6)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self.dialog, id=wx.ID_OK, label="&Save")
        cancel = wx.Button(self.dialog, id=wx.ID_CANCEL)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        btns.AddStretchSpacer()
        btns.Add(ok, 0, wx.RIGHT, 6)
        btns.Add(cancel, 0)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizerAndFit(root)
        self._entry = entry
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        term = self._term.GetValue().strip()
        spoken = self._spoken.GetValue().strip() or term
        if term:
            self._preview.SetLabel(f'"{term}" will be spoken as "{spoken}".')
        else:
            self._preview.SetLabel("Enter a word to add.")
        self._mode_label.SetLabel(
            "SSML (with plain fallback above)" if self._mode == "ssml" else ""
        )

    def _on_build_ssml(self, _evt: object) -> None:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.ssml_builder_dialog import SsmlBuilderDialog

        builder = SsmlBuilderDialog(
            self.dialog,
            term=self._term.GetValue().strip(),
            fragment=self._ssml_fragment,
            fallback=self._spoken.GetValue().strip(),
            on_audition=self._on_audition,
        )
        result = builder.show(show_modal_dialog)
        if result is not None:
            fragment, fallback = result
            self._mode = "ssml"
            self._ssml_fragment = fragment
            self._spoken.SetValue(fallback)
            self._refresh_preview()

    def _audition(self, text: str) -> None:
        if self._on_audition is not None and text.strip():
            self._on_audition(text.strip())

    def _on_ok(self, evt: object) -> None:
        term = self._term.GetValue().strip()
        if not term:
            show_message_box(
                "Enter a word or phrase.",
                "Pronunciation Entry",
                self._wx.OK | self._wx.ICON_ERROR,
                self.dialog,
            )
            return
        fallback = self._spoken.GetValue().strip()
        if self._mode == "ssml":
            self._result = PronunciationEntry(
                term=term,
                replacement=self._ssml_fragment,
                mode="ssml",
                plain_fallback=fallback or term,
                whole_word=self._whole.GetValue(),
                case_sensitive=self._case.GetValue(),
                enabled=self._entry.enabled,
                note=self._entry.note,
            )
        else:
            self._result = PronunciationEntry(
                term=term,
                replacement=fallback,
                whole_word=self._whole.GetValue(),
                case_sensitive=self._case.GetValue(),
                enabled=self._entry.enabled,
                note=self._entry.note,
            )
        evt.Skip()

    def show(self, show_modal_dialog: Any) -> PronunciationEntry | None:
        code = show_modal_dialog(self.dialog, "Pronunciation Entry")
        result = self._result if code == self._wx.ID_OK else None
        self.dialog.Destroy()
        return result


class PronunciationDictionaryDialog:
    """Manage pronunciation dictionaries and their entries."""

    def __init__(
        self,
        parent: object,
        *,
        project_dir: Path | None,
        enabled_ids: set[str],
        on_audition: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._project_dir = project_dir
        self._on_audition = on_audition
        self.dialog = wx.Dialog(
            parent,
            title="Pronunciation Dictionaries",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(640, 480))

        # Load a working copy; enabled flag is seeded from the saved selection.
        self._dicts: list[PronunciationDictionary] = load_dictionaries(project_dir)
        if enabled_ids:
            for d in self._dicts:
                d.enabled = d.id in enabled_ids
        self._deleted: list[PronunciationDictionary] = []

        root = wx.BoxSizer(wx.VERTICAL)
        cols = wx.BoxSizer(wx.HORIZONTAL)

        # Left: dictionaries
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self.dialog, label="&Dictionaries:"), 0, wx.BOTTOM, 4)
        self._dict_list = wx.ListBox(self.dialog, choices=[])
        set_accessible_name(self._dict_list, "Dictionaries")
        self._dict_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select_dict())
        left.Add(self._dict_list, 1, wx.EXPAND)
        self._enabled = wx.CheckBox(self.dialog, label="&Enabled for export")
        self._enabled.Bind(wx.EVT_CHECKBOX, self._on_toggle_enabled)
        left.Add(self._enabled, 0, wx.TOP, 4)
        d_btns = wx.BoxSizer(wx.HORIZONTAL)
        for lbl, handler in (
            ("&New...", self._on_new_dict),
            ("De&lete", self._on_delete_dict),
            ("Restore S&tarter", self._on_restore_starter),
        ):
            b = wx.Button(self.dialog, label=lbl)
            b.Bind(wx.EVT_BUTTON, handler)
            d_btns.Add(b, 0, wx.RIGHT, 4)
        left.Add(d_btns, 0, wx.TOP, 4)
        cols.Add(left, 1, wx.EXPAND | wx.ALL, 6)

        # Right: entries
        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self.dialog, label="&Words in this dictionary:"), 0, wx.BOTTOM, 4)
        self._entry_list = wx.ListBox(self.dialog, choices=[])
        set_accessible_name(self._entry_list, "Words in this dictionary")
        apply_listbox_activation(self._entry_list, lambda _e: self._on_edit_entry(None))
        right.Add(self._entry_list, 1, wx.EXPAND)
        e_btns = wx.BoxSizer(wx.HORIZONTAL)
        for lbl, handler in (
            ("&Add...", self._on_add_entry),
            ("&Edit...", self._on_edit_entry),
            ("&Remove", self._on_remove_entry),
        ):
            b = wx.Button(self.dialog, label=lbl)
            b.Bind(wx.EVT_BUTTON, handler)
            e_btns.Add(b, 0, wx.RIGHT, 4)
        right.Add(e_btns, 0, wx.TOP, 4)
        cols.Add(right, 1, wx.EXPAND | wx.ALL, 6)

        root.Add(cols, 1, wx.EXPAND)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self.dialog, id=wx.ID_OK, label="Save && &Close")
        cancel = wx.Button(self.dialog, id=wx.ID_CANCEL)
        btns.AddStretchSpacer()
        btns.Add(ok, 0, wx.RIGHT, 6)
        btns.Add(cancel, 0)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)
        self._refresh_dict_list()

    # -- rendering -------------------------------------------------------- #

    def _dict_label(self, d: PronunciationDictionary) -> str:
        scope = "project" if d.scope == "project" else "global"
        engine = d.engine or "all engines"
        state = "on" if d.enabled else "off"
        return f"{d.name or d.id} ({scope}, {engine}) [{state}]"

    def _refresh_dict_list(self) -> None:
        sel = self._dict_list.GetSelection()
        self._dict_list.Set([self._dict_label(d) for d in self._dicts])
        if self._dicts:
            self._dict_list.SetSelection(min(max(sel, 0), len(self._dicts) - 1))
        self._on_select_dict()

    def _selected_dict(self) -> PronunciationDictionary | None:
        idx = self._dict_list.GetSelection()
        if 0 <= idx < len(self._dicts):
            return self._dicts[idx]
        return None

    def _on_select_dict(self) -> None:
        d = self._selected_dict()
        self._enabled.SetValue(bool(d and d.enabled))
        self._entry_list.Set(
            [f"{e.term} -> {e.replacement or e.term}" for e in d.entries] if d else []
        )

    def _selected_entry_index(self) -> int:
        return self._entry_list.GetSelection()

    # -- dictionary actions ---------------------------------------------- #

    def _on_toggle_enabled(self, _evt: object) -> None:
        d = self._selected_dict()
        if d is not None:
            d.enabled = self._enabled.GetValue()
            self._refresh_dict_list()

    def _on_new_dict(self, _evt: object) -> None:
        wx = self._wx
        dlg = wx.TextEntryDialog(self.dialog, "Name for the new dictionary:", "New Dictionary")
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.GetValue().strip()
        finally:
            dlg.Destroy()
        if not name:
            return
        new_id = _slugify(name) or f"dict{len(self._dicts) + 1}"
        existing = {d.id for d in self._dicts}
        while new_id in existing:
            new_id += "_1"
        self._dicts.append(
            PronunciationDictionary(id=new_id, name=name, scope="global", enabled=True)
        )
        self._refresh_dict_list()
        self._dict_list.SetSelection(len(self._dicts) - 1)
        self._on_select_dict()

    def _on_delete_dict(self, _evt: object) -> None:
        d = self._selected_dict()
        if d is None:
            return
        self._deleted.append(d)
        self._dicts.remove(d)
        self._refresh_dict_list()

    def _on_restore_starter(self, _evt: object) -> None:
        install_starter_dictionary(overwrite=False)
        self._dicts = load_dictionaries(self._project_dir)
        self._refresh_dict_list()

    # -- entry actions ---------------------------------------------------- #

    def _require_dict(self) -> PronunciationDictionary | None:
        d = self._selected_dict()
        if d is None:
            show_message_box(
                "Select or create a dictionary first.",
                "Pronunciation Dictionaries",
                self._wx.OK | self._wx.ICON_INFORMATION,
                self.dialog,
            )
        return d

    def _on_add_entry(self, _evt: object) -> None:
        d = self._require_dict()
        if d is None:
            return
        from quill.ui.dialog_contract import show_modal_dialog

        editor = PronunciationEntryDialog(
            self.dialog, PronunciationEntry(), on_audition=self._on_audition
        )
        result = editor.show(show_modal_dialog)
        if result is not None:
            d.entries.append(result)
            self._on_select_dict()

    def _on_edit_entry(self, _evt: object) -> None:
        d = self._selected_dict()
        idx = self._selected_entry_index()
        if d is None or not (0 <= idx < len(d.entries)):
            return
        from quill.ui.dialog_contract import show_modal_dialog

        editor = PronunciationEntryDialog(
            self.dialog, d.entries[idx], on_audition=self._on_audition
        )
        result = editor.show(show_modal_dialog)
        if result is not None:
            d.entries[idx] = result
            self._on_select_dict()
            self._entry_list.SetSelection(idx)

    def _on_remove_entry(self, _evt: object) -> None:
        d = self._selected_dict()
        idx = self._selected_entry_index()
        if d is None or not (0 <= idx < len(d.entries)):
            return
        del d.entries[idx]
        self._on_select_dict()

    # -- save ------------------------------------------------------------- #

    def enabled_ids(self) -> list[str]:
        return [d.id for d in self._dicts if d.enabled]

    def save_all(self) -> list[str]:
        """Persist all changes; return the names of any that failed to save.

        The user closed with OK expecting their edits saved, so a per-dictionary
        write failure must be surfaced (see ``show``) rather than silently losing
        their pronunciation changes.
        """
        failures: list[str] = []
        for d in self._deleted:
            try:
                delete_dictionary(d, self._project_dir)
            except OSError:
                failures.append(getattr(d, "name", getattr(d, "id", "a dictionary")))
        for d in self._dicts:
            try:
                save_dictionary(d, self._project_dir if d.scope == "project" else None)
            except (OSError, ValueError):
                failures.append(getattr(d, "name", getattr(d, "id", "a dictionary")))
        return failures

    def show(self, show_modal_dialog: Any) -> bool:
        code = show_modal_dialog(self.dialog, "Pronunciation Dictionaries")
        saved = code == self._wx.ID_OK
        if saved:
            failures = self.save_all()
            if failures:
                show_message_box(
                    "Some pronunciation dictionaries could not be saved:\n"
                    + "\n".join(f"  - {name}" for name in failures)
                    + "\n\nYour changes to those may be lost. Check the folder "
                    "permissions and try again.",
                    "Pronunciation Dictionaries",
                    self._wx.OK | self._wx.ICON_WARNING,
                    self.dialog,
                )
        ids = self.enabled_ids()
        self.dialog.Destroy()
        self._saved_enabled_ids = ids
        return saved


def _slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.strip().lower()).strip("_")


def _make_auditioner(frame: Any) -> Any:
    """Return ``audition(text)`` that speaks *text* with the user's current voice.

    Synthesizes off the UI thread via the same engine the batch/read-aloud paths
    use (so Kokoro reuses its cached model) and plays through the frame's preview
    player. Failures are swallowed to a status message — never a crash.
    """
    import tempfile

    s = frame.settings

    def audition(text: str) -> None:
        engine = (s.read_aloud_engine or "sapi5").strip().lower()
        voice = {
            "kokoro": s.read_aloud_kokoro_voice,
            "dectalk": s.read_aloud_dectalk_voice,
            "espeak": s.read_aloud_espeak_voice,
        }.get(engine, s.read_aloud_voice)
        if engine == "piper" and s.read_aloud_piper_model:
            voice = Path(s.read_aloud_piper_model).stem

        def work(_progress: Any) -> object:
            from quill.core.speech.document_speech import SynthesisSpec, make_synthesizer

            synth = make_synthesizer(
                SynthesisSpec(
                    engine=engine,
                    voice=voice or "",
                    rate=int(s.read_aloud_rate),
                    speed=float(s.read_aloud_kokoro_speed),
                )
            )
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
                wav = Path(fh.name)
            synth(text, wav)
            frame._play_preview_asset(wav)
            return None

        frame._run_background_task(
            "Auditioning pronunciation", work, lambda _r: frame._set_status("Audition finished")
        )

    return audition


def run_pronunciation_manager(frame: Any) -> None:
    """Tools > Speech > Manage Pronunciations entry point."""
    s = frame.settings
    project_dir = None
    doc_path = getattr(frame, "_active_document_path", lambda: None)()
    if isinstance(doc_path, (str, Path)) and str(doc_path):
        parent = Path(doc_path).parent
        if parent.is_dir():
            project_dir = parent
    enabled_ids = set(getattr(s, "pronunciation_enabled_dictionary_ids", []) or [])
    dialog = PronunciationDictionaryDialog(
        frame.frame,
        project_dir=project_dir,
        enabled_ids=enabled_ids,
        on_audition=_make_auditioner(frame),
    )
    if dialog.show(frame._show_modal_dialog):
        from quill.core.settings import save_settings

        s.pronunciation_enabled_dictionary_ids = list(dialog._saved_enabled_ids)
        try:
            save_settings(s)
        except Exception:  # noqa: BLE001 - best-effort persistence
            pass
        frame._set_status("Pronunciation dictionaries saved")
