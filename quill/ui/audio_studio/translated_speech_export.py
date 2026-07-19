"""Export a single document to translated speech audio (Audio Studio).

The batch wizard translates a *folder* of documents; this is the focused,
one-document counterpart bound to the Studio menu's "Export a Document to
Translated Speech...". Unlike QUILL's editor-based version (which exports the
active document tab), the standalone Audio Studio has no open document, so this
opens a file picker, collects the target languages/voices and output format via
:class:`TranslatedSpeechExportDialog`, and runs the *same tested core*
(``batch_speech_runner._export_translations`` / ``_build_translator``) the wizard
uses, writing ``<doc> (<Language>).<ext>`` beside the source.

Shared between the standalone Studio shell and QUILL's embedded Audio Studio:
both hosts expose ``_wx``, ``settings``, ``_show_modal_dialog``,
``_run_background_task``, ``_set_status``, ``_show_message_box``, and ``frame``.

Every control is parented directly on the dialog (the NVDA focus rule); the
language/voice picker reuses the combo + Add + reorderable list pattern and
``apply_listbox_activation``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    set_accessible_name,
    show_message_box,
)

_TITLE = "Export a Document to Translated Speech"

#: Source documents Audio Studio can read for narration (mirrors
#: ``core.speech.batch_export.SUPPORTED_EXTENSIONS``).
_DOC_WILDCARD = (
    "Documents (*.md;*.html;*.htm;*.docx;*.txt)|*.md;*.html;*.htm;*.docx;*.txt"
    "|All files (*.*)|*.*"
)

# Output formats in the order they appear in the format Choice.
_FORMAT_CHOICES = ("mp3", "m4b", "wav")


@dataclass(slots=True)
class TranslatedSpeechRequest:
    """Everything the runner needs to translate-and-synthesize one document."""

    # Each target is (language_code, engine, voice_id).
    targets: tuple[tuple[str, str, str], ...]
    output_format: str = "mp3"
    translation_provider: str = "ai_assistant"  # or "libretranslate"
    libretranslate_url: str = "http://localhost:5000"
    _labels: tuple[str, ...] = field(default=(), repr=False)


class TranslatedSpeechExportDialog:
    """Configuration dialog for a single document's translated audio export."""

    def __init__(self, parent: object, *, document_name: str) -> None:
        import wx

        self._wx = wx
        self._result: TranslatedSpeechRequest | None = None
        # The "Open in the wizard" button sets this rather than ``_result`` so
        # the runner can branch on a single public flag.
        self.open_studio_requested: bool = False
        # Ordered (lang_code, engine, voice_id, display_label).
        self._targets: list[tuple[str, str, str, str]] = []

        self.dialog = wx.Dialog(
            parent,
            title=_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        def label(text: str) -> None:
            root.Add(wx.StaticText(self.dialog, label=text), 0, wx.LEFT | wx.TOP, 8)

        label(f"Translate and speak: {document_name}")

        # --- Output format ---
        label("Output &format:")
        self._format = wx.Choice(
            self.dialog,
            choices=["MP3 (with chapter markers)", "M4B audiobook (native chapters)", "WAV"],
        )
        set_accessible_name(self._format, "Output format")
        self._format.SetSelection(0)
        root.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Language + voice picker ---
        label("Add a target &language and voice:")
        from quill.core.ai.translation import SUPPORTED_LANGUAGES

        self._lang_pairs = sorted(SUPPORTED_LANGUAGES.items())  # (name, code)
        add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._lang = wx.Choice(self.dialog, choices=[name for name, _c in self._lang_pairs])
        self._lang.SetName("Translation language")
        self._lang.Bind(wx.EVT_CHOICE, lambda _e: self._reload_voices())
        self._voice = wx.Choice(self.dialog, choices=[])
        self._voice.SetName("Translation voice")
        add = wx.Button(self.dialog, label="A&dd")
        add.Bind(wx.EVT_BUTTON, lambda _e: self._on_add())
        add_row.Add(self._lang, 1, wx.EXPAND | wx.RIGHT, 6)
        add_row.Add(self._voice, 2, wx.EXPAND | wx.RIGHT, 6)
        add_row.Add(add, 0)
        root.Add(add_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._list.SetName("Languages to export")
        apply_listbox_activation(self._list, lambda _e: self._lang.SetFocus())
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        rm_row = wx.BoxSizer(wx.HORIZONTAL)
        remove = wx.Button(self.dialog, label="Re&move")
        remove.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove())
        rm_row.Add(remove, 0, wx.RIGHT, 6)
        rm_row.Add(
            wx.StaticText(self.dialog, label="Trans&late with:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._provider = wx.Choice(
            self.dialog, choices=["AI provider (cloud)", "LibreTranslate (local)"]
        )
        set_accessible_name(self._provider, "Translate with")
        self._provider.SetSelection(0)
        rm_row.Add(self._provider, 0, wx.LEFT, 6)
        root.Add(rm_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Buttons ---
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self.dialog, id=wx.ID_OK, label="&Export")
        cancel = wx.Button(self.dialog, id=wx.ID_CANCEL)
        open_studio = wx.Button(self.dialog, label="Open in the &Wizard")
        open_studio.SetToolTip(
            "Close this dialog and open the Audio Studio wizard, where you can "
            "build a chaptered audiobook and publish it."
        )
        open_studio.Bind(wx.EVT_BUTTON, self._on_open_studio)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        btn_row.AddStretchSpacer()
        btn_row.Add(ok, 0, wx.RIGHT, 6)
        btn_row.Add(open_studio, 0, wx.RIGHT, 6)
        btn_row.Add(cancel, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)
        self.dialog.Fit()
        if self._lang_pairs:
            self._lang.SetSelection(0)
        self._reload_voices()

    # ------------------------------------------------------------------ helpers

    def _current_lang(self) -> tuple[str, str]:
        idx = self._lang.GetSelection()
        return self._lang_pairs[idx] if 0 <= idx < len(self._lang_pairs) else ("", "")

    def _reload_voices(self) -> None:
        from quill.core.speech.voice_languages import voices_for_language

        _name, code = self._current_lang()
        self._voice_opts = voices_for_language(code) if code else []
        self._voice.Set([v.display for v in self._voice_opts])
        if self._voice_opts:
            self._voice.SetSelection(0)

    def _refresh_list(self, *, select: int = -1) -> None:
        self._list.Set([t[3] for t in self._targets])
        if self._targets:
            index = select if 0 <= select < len(self._targets) else 0
            self._list.SetSelection(index)

    def _on_add(self) -> None:
        name, code = self._current_lang()
        vidx = self._voice.GetSelection()
        if not code or not (0 <= vidx < len(self._voice_opts)):
            return
        v = self._voice_opts[vidx]
        if any(t[0] == code and t[2] == v.voice_id for t in self._targets):
            return  # already added
        self._targets.append((code, v.engine, v.voice_id, f"{name}: {v.display}"))
        self._refresh_list(select=len(self._targets) - 1)

    def _on_remove(self) -> None:
        idx = self._list.GetSelection()
        if 0 <= idx < len(self._targets):
            del self._targets[idx]
            self._refresh_list(select=min(idx, len(self._targets) - 1))

    def _on_ok(self, evt: object) -> None:
        if not self._targets:
            show_message_box(
                "Add at least one target language and voice.",
                _TITLE,
                self._wx.OK | self._wx.ICON_ERROR,
                self.dialog,
            )
            return
        self._result = TranslatedSpeechRequest(
            targets=tuple((c, e, v) for c, e, v, _ in self._targets),
            output_format=(
                _FORMAT_CHOICES[self._format.GetSelection()]
                if 0 <= self._format.GetSelection() < len(_FORMAT_CHOICES)
                else "mp3"
            ),
            translation_provider=(
                "libretranslate" if self._provider.GetSelection() == 1 else "ai_assistant"
            ),
            _labels=tuple(t[3] for t in self._targets),
        )
        evt.Skip()  # let ID_OK close the dialog

    def _on_open_studio(self, _evt: object) -> None:
        # Close the dialog and signal the runner to open the wizard instead. The
        # button is always reachable -- no target list required.
        self.open_studio_requested = True
        self.dialog.EndModal(self._wx.ID_CANCEL)

    # ------------------------------------------------------------------ public

    def show(
        self, show_modal_dialog: Callable[[object, str], int]
    ) -> TranslatedSpeechRequest | None:
        code = show_modal_dialog(self.dialog, _TITLE)
        result = self._result if code == self._wx.ID_OK else None
        self.dialog.Destroy()
        return result


# ---------------------------------------------------------------- runner (host)


def run_translated_speech_export(frame: Any) -> None:
    """Entry point for the Studio menu's "Export a Document to Translated
    Speech...": pick a document, choose languages, and export translated audio
    beside it. *frame* is the host shell (StudioAppFrame or QUILL's Audio Studio
    host)."""
    wx = frame._wx
    with wx.FileDialog(
        frame.frame,
        _TITLE,
        wildcard=_DOC_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dlg:
        if frame._show_modal_dialog(dlg, _TITLE) != wx.ID_OK:  # dialog_button_contract: exempt
            return
        source = Path(dlg.GetPath())

    dialog = TranslatedSpeechExportDialog(frame.frame, document_name=source.name)
    request = dialog.show(frame._show_modal_dialog)
    if dialog.open_studio_requested:
        from quill.ui.batch_speech_runner import run_batch_export_to_speech

        run_batch_export_to_speech(frame)
        return
    if request is None:
        frame._set_status("Translated speech export cancelled")
        return
    _run(frame, request, read_source=source, out_dir=source.parent, stem=source.stem)


def _run(
    frame: Any,
    request: TranslatedSpeechRequest,
    *,
    read_source: Path,
    out_dir: Path,
    stem: str,
) -> None:
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions
    from quill.core.speech.voice_blacklist import load_blacklist, save_blacklist
    from quill.ui.batch_speech_runner import (
        _build_translator,
        _export_translations,
        confirm_cloud_cost,
    )

    s = frame.settings
    suffix = {"mp3": ".mp3", "m4b": ".m4b"}.get(request.output_format, ".wav")
    base_final = out_dir / f"{stem}{suffix}"
    # A req shim carrying just the fields _export_translations / _build_translator read.
    req = SimpleNamespace(
        translation_targets=request.targets,
        translation_provider=request.translation_provider,
        libretranslate_url=request.libretranslate_url,
        rate=int(s.read_aloud_rate),
        speed=float(s.read_aloud_kokoro_speed),
        combine_headings=False,
        source_folder=out_dir,
    )
    for_language = _build_translator(req)
    if for_language is None:
        frame._set_status("No translation targets selected")
        return

    # Cost surfacing: the document character count is known exactly here, so the
    # combined translation + TTS estimate is precise. Confirm before metered work.
    try:
        from quill.core.speech.text_polish import extract_text

        char_count = len(extract_text(read_source))
    except Exception:  # noqa: BLE001 - estimate is best-effort
        char_count = 0
    if not confirm_cloud_cost(
        frame,
        translation_provider=request.translation_provider,
        targets=request.targets,
        char_count=char_count,
    ):
        frame._set_status("Translated speech export cancelled")
        return

    def opts(_sound_path: Path | None = None) -> ChapterAssembleOptions:
        return ChapterAssembleOptions(
            article_gap_ms=int(s.batch_speech_article_gap_ms),
            sound_enabled=False,
            output_format=request.output_format,
            speak_headings=True,
            sentence_gap_ms=int(s.batch_speech_sentence_gap_ms),
            tail_padding_ms=int(s.batch_speech_tail_padding_ms),
            max_chunk_chars=8000,
        )

    voice_blacklist = load_blacklist()

    def work(_progress: Any) -> object:
        chapters = _export_translations(
            frame,
            req,
            read_source,
            base_final,
            suffix,
            None,
            opts,
            for_language,
            voice_blacklist,
        )
        save_blacklist(voice_blacklist)
        return chapters

    def on_success(result: object) -> None:
        count = int(result) if isinstance(result, int) else 0
        langs = len(request.targets)
        frame._set_status(
            f"Translated speech export complete: {langs} language(s), {count} chapter(s)"
        )

    frame._run_background_task(
        f"Translated speech export ({len(request.targets)} language(s))",
        work,
        on_success,
        notify_on_success=True,
        notify_on_error=True,
        notification_category="speech",
        protect_on_close=True,
    )
