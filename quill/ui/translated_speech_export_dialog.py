"""Single-document translated speech export dialog (roadmap §7).

The batch dialog translates a *folder* of documents; this is the focused,
one-document counterpart bound to Tools > Speech > Export to Translated Speech
Audio. It collects only what a single translated export needs — the output format,
the translation backend, and one or more (language, voice) targets — and returns a
:class:`TranslatedSpeechRequest`. The synthesis is run by
``quill.ui.translated_speech_runner`` against the active document's file, writing
``<doc> (<Language>).<ext>`` beside it.

Every control is parented directly on the dialog (the NVDA focus rule, A11Y-SR-2);
the language/voice picker reuses the combo + Add + reorderable list pattern and
``apply_listbox_activation`` (GATE-13) from the batch dialog.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    show_message_box,
)

# Output formats in the order they appear in the format Choice.
_FORMAT_CHOICES = ("mp3", "m4b", "wav")
_FORMAT_INDEX = {fmt: i for i, fmt in enumerate(_FORMAT_CHOICES)}


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
        # The "Open in Audio Studio" button sets this rather than ``_result``
        # so the runner can branch on a single public flag.
        self.open_studio_requested: bool = False
        # Ordered (lang_code, engine, voice_id, display_label).
        self._targets: list[tuple[str, str, str, str]] = []

        self.dialog = wx.Dialog(
            parent,
            title="Export to Translated Speech Audio",
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
        self._provider.SetSelection(0)
        rm_row.Add(self._provider, 0, wx.LEFT, 6)
        root.Add(rm_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Buttons ---
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self.dialog, id=wx.ID_OK, label="&Export")
        cancel = wx.Button(self.dialog, id=wx.ID_CANCEL)
        open_studio = wx.Button(self.dialog, label="Open in Audio &Studio")
        open_studio.SetToolTip(
            "Close this dialog and open the same document in the Audio Studio wizard, "
            "where you can build a chaptered audiobook and publish it."
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
                "Export to Translated Speech Audio",
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
        # Close the dialog and signal the runner to route to the Audio Studio.
        # The button is always reachable — no target list required — so the
        # cross-link works even from an empty dialog.
        self.open_studio_requested = True
        self.dialog.EndModal(self._wx.ID_CANCEL)

    # ------------------------------------------------------------------ public

    def show(
        self, show_modal_dialog: Callable[[object, str], int]
    ) -> TranslatedSpeechRequest | None:
        code = show_modal_dialog(self.dialog, "Export to Translated Speech Audio")
        result = self._result if code == self._wx.ID_OK else None
        # The "Open in Audio Studio" button routes through EndModal(ID_CANCEL) but
        # sets ``open_studio_requested = True`` so the runner can branch on it.
        # The dialog itself is destroyed here, regardless of how the modal closed.
        self.dialog.Destroy()
        return result
