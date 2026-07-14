"""AI translation result dialog for QUILL.

Supports two translation providers:
- AI Assistant: uses the configured cloud/local LLM (OpenAI, Claude, Ollama, etc.)
- LibreTranslate: a self-hosted open-source translation engine (local or LAN)
  See https://libretranslate.com / https://github.com/LibreTranslate/LibreTranslate
  Run locally with: pip install libretranslate && libretranslate
  Default local URL: http://localhost:5000
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.ai.translation import LANGUAGE_NAMES, SUPPORTED_LANGUAGES
from quill.ui.dialog_contract import apply_modal_ids

_DEFAULT_LIBRETRANSLATE_URL = "http://localhost:5000"

_LIBRETRANSLATE_HELP = (
    "LibreTranslate is a free, open-source translation engine you can run locally.\n"
    "Run it with: pip install libretranslate && libretranslate\n"
    "Then enter http://localhost:5000 as the URL. No internet required."
)


class AITranslationDialog:
    """Language selection + result dialog for AI translation.

    Workflow:
      1. User picks provider (AI Assistant or LibreTranslate) and target language.
      2. Translation runs in background; result appears in the text area.
      3. Buttons: Copy to Clipboard, Replace Original, Open as New Document, Close.

    The caller supplies *on_translate(text, target_language, provider, libretranslate_url)*
    which dispatches to the appropriate backend.
    """

    def __init__(
        self,
        parent: object,
        initial_text: str,
        source_description: str,
        show_modal_dialog: Callable,
        on_translate: Callable[[str, str, str, str], tuple[str, str]],
        on_replace: Callable[[str], None] | None = None,
        on_new_document: Callable[[str, str], None] | None = None,
        default_libretranslate_url: str = _DEFAULT_LIBRETRANSLATE_URL,
    ) -> None:
        import wx

        self._wx = wx
        self._initial_text = initial_text
        self._source_description = source_description
        self._show_modal = show_modal_dialog
        self._on_translate = on_translate
        self._on_replace = on_replace
        self._on_new_document = on_new_document
        self._default_libretranslate_url = default_libretranslate_url
        self._result_text = ""
        self._detected_source = "unknown"
        self._working = False

        title = f"AI Translate - {source_description}"
        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(800, 620))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # --- Provider section ---
        provider_box = wx.StaticBox(self.dialog, label="Translation provider")
        provider_sizer = wx.StaticBoxSizer(provider_box, wx.VERTICAL)

        self._provider_ai_rb = wx.RadioButton(
            self.dialog,
            label="&AI Assistant (uses your configured AI provider)",
            style=wx.RB_GROUP,
        )
        self._provider_lt_rb = wx.RadioButton(
            self.dialog,
            label="&LibreTranslate (local or self-hosted, no cloud required)",
        )
        self._provider_ai_rb.SetValue(True)
        provider_sizer.Add(self._provider_ai_rb, 0, wx.ALL, 4)
        provider_sizer.Add(self._provider_lt_rb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

        lt_url_row = wx.BoxSizer(wx.HORIZONTAL)
        lt_url_label = wx.StaticText(self.dialog, label="LibreTranslate URL:")
        self._lt_url_ctrl = wx.TextCtrl(
            self.dialog,
            value=self._default_libretranslate_url,
        )
        self._lt_url_ctrl.SetName("LibreTranslate URL")
        self._lt_url_ctrl.Enable(False)
        lt_help_btn = wx.Button(self.dialog, label="?", style=wx.BU_EXACTFIT)
        lt_help_btn.SetToolTip(wx.ToolTip(_LIBRETRANSLATE_HELP))
        lt_help_btn.SetName("LibreTranslate help")
        lt_url_row.Add(lt_url_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        lt_url_row.Add(self._lt_url_ctrl, 1, wx.RIGHT, 4)
        lt_url_row.Add(lt_help_btn, 0)
        provider_sizer.Add(lt_url_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

        lt_note = wx.StaticText(
            self.dialog,
            label=(
                "LibreTranslate can run fully offline on your machine. "
                "Install: pip install libretranslate && libretranslate"
            ),
        )
        lt_note.Wrap(720)
        provider_sizer.Add(lt_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        root.Add(provider_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # --- Language chooser row ---
        lang_row = wx.BoxSizer(wx.HORIZONTAL)
        lang_label = wx.StaticText(self.dialog, label="Translate to:")
        language_names = sorted(SUPPORTED_LANGUAGES.keys())
        self._lang_choice = wx.Choice(self.dialog, choices=language_names)
        default_idx = language_names.index("French") if "French" in language_names else 0
        self._lang_choice.SetSelection(default_idx)
        self._lang_choice.SetName("Target language")
        self._translate_btn = wx.Button(self.dialog, label="&Translate Now")
        lang_row.Add(lang_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        lang_row.Add(self._lang_choice, 0, wx.RIGHT, 16)
        lang_row.Add(self._translate_btn, 0)
        root.Add(lang_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Status line
        self._status_label = wx.StaticText(
            self.dialog,
            label=f"Source: {self._source_description}. Select a language and press Translate Now.",
        )
        self._status_label.Wrap(760)
        root.Add(self._status_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Result text area
        result_label = wx.StaticText(self.dialog, label="Translation:")
        root.Add(result_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._result_text_ctrl = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
        )
        self._result_text_ctrl.SetName("Translation result")
        root.Add(self._result_text_ctrl, 1, wx.EXPAND | wx.ALL, 8)

        # Detected source language label
        self._source_lang_label = wx.StaticText(self.dialog, label="")
        root.Add(self._source_lang_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Action buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label="&Copy to Clipboard")
        self._replace_btn = wx.Button(self.dialog, label="&Replace Original")
        self._new_doc_btn = wx.Button(self.dialog, label="Open as &New Document")
        self._close_btn = wx.Button(self.dialog, label="C&lose")
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._close_btn.GetId(),
            escape_id=self._close_btn.GetId(),
        )
        for b in (self._copy_btn, self._replace_btn, self._new_doc_btn, self._close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        if self._on_replace is None:
            self._replace_btn.Enable(False)
        if self._on_new_document is None:
            self._new_doc_btn.Enable(False)
        self._copy_btn.Enable(False)
        root.Add(btn_row, 0, wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._bind_events(lt_help_btn)
        self._wx.CallAfter(self._lang_choice.SetFocus)

    def _bind_events(self, lt_help_btn: object) -> None:
        wx = self._wx
        self._provider_ai_rb.Bind(wx.EVT_RADIOBUTTON, self._on_provider_change)
        self._provider_lt_rb.Bind(wx.EVT_RADIOBUTTON, self._on_provider_change)
        lt_help_btn.Bind(wx.EVT_BUTTON, self._on_lt_help)
        self._translate_btn.Bind(wx.EVT_BUTTON, self._on_translate_clicked)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._replace_btn.Bind(wx.EVT_BUTTON, self._on_replace_clicked)
        self._new_doc_btn.Bind(wx.EVT_BUTTON, self._on_new_doc)
        self._close_btn.Bind(
            wx.EVT_BUTTON,
            lambda _e: self.dialog.EndModal(wx.ID_CANCEL),
        )

    def _on_provider_change(self, event: object) -> None:
        using_lt = self._provider_lt_rb.GetValue()
        self._lt_url_ctrl.Enable(using_lt)

    def _on_lt_help(self, event: object) -> None:
        wx = self._wx
        wx.MessageBox(  # GATE-41-OK: standalone dialog  # MSGBOX-OK: standalone dialog
            _LIBRETRANSLATE_HELP,
            "About LibreTranslate",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
        )

    def _on_translate_clicked(self, event: object) -> None:
        if self._working:
            return
        self._working = True
        lang_name = self._lang_choice.GetString(self._lang_choice.GetSelection())
        provider = "libretranslate" if self._provider_lt_rb.GetValue() else "ai_assistant"
        lt_url = self._lt_url_ctrl.GetValue().strip() or _DEFAULT_LIBRETRANSLATE_URL
        self._status_label.SetLabel(f"Translating to {lang_name} via {provider}...")
        self._translate_btn.Enable(False)

        def _run() -> None:
            try:
                translated, detected = self._on_translate(
                    self._initial_text, lang_name, provider, lt_url
                )
                self._wx.CallAfter(self._on_done, translated, detected, lang_name)
            except Exception as exc:
                self._wx.CallAfter(self._on_error, str(exc))

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _on_done(self, translated: str, detected: str, lang_name: str) -> None:
        self._result_text = translated
        self._detected_source = detected
        self._result_text_ctrl.SetValue(translated)
        detected_label = (
            LANGUAGE_NAMES.get(detected, detected) if detected != "unknown" else "unknown"
        )
        self._source_lang_label.SetLabel(f"Detected source language: {detected_label}")
        self._status_label.SetLabel(f"Translation to {lang_name} complete.")
        self._copy_btn.Enable(True)
        if self._on_replace is not None:
            self._replace_btn.Enable(True)
        if self._on_new_document is not None:
            self._new_doc_btn.Enable(True)
        self._working = False
        self._translate_btn.Enable(True)
        self._wx.CallAfter(self._result_text_ctrl.SetFocus)

    def _on_error(self, message: str) -> None:
        self._status_label.SetLabel(f"Error: {message}")
        self._working = False
        self._translate_btn.Enable(True)

    def _on_copy(self, event: object) -> None:
        wx = self._wx
        if not self._result_text:
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self._result_text))
            wx.TheClipboard.Close()
        self._status_label.SetLabel("Translation copied to clipboard.")

    def _on_replace_clicked(self, event: object) -> None:
        if self._on_replace is not None and self._result_text:
            self._on_replace(self._result_text)
            self.dialog.EndModal(self._wx.ID_OK)

    def _on_new_doc(self, event: object) -> None:
        if self._on_new_document is not None and self._result_text:
            lang_name = self._lang_choice.GetString(self._lang_choice.GetSelection())
            self._on_new_document(self._result_text, lang_name)
            self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[str, str]:
        """Show modal. Returns (translated_text, detected_source) or ('', '') on close."""
        self._show_modal(self.dialog, "AI Translation")
        result_text, detected_source = self._result_text, self._detected_source
        self.dialog.Destroy()
        return result_text, detected_source
