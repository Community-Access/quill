"""AI audio transcription and diarization dialogs for QUILL."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.ai.transcription import SUPPORTED_AUDIO_EXTENSIONS, SUPPORTED_LANGUAGES
from quill.ui.dialog_contract import apply_modal_ids


class AITranscribeDialog:
    """File picker + options dialog for audio transcription.

    Supports:
    - Whisper transcription (OpenAI cloud)
    - Language selection (auto-detect default)
    - Speaker diarization toggle (Deepgram)
    - Max speakers spinner

    Result: the transcript text (or diarized transcript) is offered in
    AITranscriptionResultDialog after completion.
    """

    def __init__(
        self,
        parent: object,
        show_modal_dialog: Callable,
        on_transcribe: Callable[[Path, str | None, bool, bool, int], None],
    ) -> None:
        import wx

        self._wx = wx
        self._show_modal = show_modal_dialog
        self._on_transcribe = on_transcribe

        self.dialog = wx.Dialog(
            parent,
            title="Transcribe Audio File",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(640, 440))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # File picker
        file_box = wx.StaticBox(self.dialog, label="Audio file")
        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        self._file_path_ctrl = wx.TextCtrl(self.dialog)
        self._file_path_ctrl.SetName("Audio file path")
        browse_btn = wx.Button(self.dialog, label="&Browse...")
        file_sizer.Add(self._file_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        file_sizer.Add(browse_btn, 0)
        root.Add(file_sizer, 0, wx.EXPAND | wx.ALL, 8)

        supported_str = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        format_note = wx.StaticText(
            self.dialog,
            label=f"Supported formats: {supported_str}. Maximum file size: 25 MB.",
        )
        format_note.Wrap(600)
        root.Add(format_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Language
        lang_box = wx.StaticBox(self.dialog, label="Language")
        lang_sizer = wx.StaticBoxSizer(lang_box, wx.HORIZONTAL)
        lang_label = wx.StaticText(self.dialog, label="Audio language:")
        lang_names = list(SUPPORTED_LANGUAGES.keys())
        self._lang_choice = wx.Choice(self.dialog, choices=lang_names)
        self._lang_choice.SetSelection(0)  # Auto-detect
        self._lang_choice.SetName("Audio language")
        lang_sizer.Add(lang_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        lang_sizer.Add(self._lang_choice, 1)
        root.Add(lang_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Diarization options
        diar_box = wx.StaticBox(self.dialog, label="Speaker diarization (Deepgram)")
        diar_sizer = wx.StaticBoxSizer(diar_box, wx.VERTICAL)
        self._diarize_cb = wx.CheckBox(
            self.dialog, label="Identify different speakers in the audio"
        )
        self._diarize_cb.SetName("Identify different speakers in the audio")
        diar_sizer.Add(self._diarize_cb, 0, wx.ALL, 4)

        speaker_row = wx.BoxSizer(wx.HORIZONTAL)
        speaker_label = wx.StaticText(self.dialog, label="Maximum speakers:")
        self._max_speakers = wx.SpinCtrl(self.dialog, min=2, max=20, initial=6)
        self._max_speakers.SetName("Maximum speakers")
        self._max_speakers.Enable(False)
        speaker_row.Add(speaker_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        speaker_row.Add(self._max_speakers, 0)
        diar_sizer.Add(speaker_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        root.Add(diar_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Translate option
        self._translate_cb = wx.CheckBox(
            self.dialog, label="Translate audio to English (Whisper translation)"
        )
        self._translate_cb.SetName("Translate audio to English")
        root.Add(self._translate_cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._ok_btn = wx.Button(self.dialog, label="&Transcribe")
        cancel_btn = wx.Button(self.dialog, label="&Cancel")
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._ok_btn.GetId(),
            escape_id=cancel_btn.GetId(),
        )
        btn_row.Add(self._ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._bind_events(browse_btn, cancel_btn)
        self._wx.CallAfter(self._file_path_ctrl.SetFocus)

    def _bind_events(self, browse_btn: object, cancel_btn: object) -> None:
        wx = self._wx
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._diarize_cb.Bind(wx.EVT_CHECKBOX, self._on_diarize_toggle)
        self._translate_cb.Bind(wx.EVT_CHECKBOX, self._on_translate_toggle)
        self._ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(self._wx.ID_CANCEL))

    def _on_browse(self, event: object) -> None:
        wx = self._wx
        ext_list = ";".join(f"*{e}" for e in sorted(SUPPORTED_AUDIO_EXTENSIONS))
        wildcard = f"Audio files ({ext_list})|{ext_list}|All files (*.*)|*.*"
        with wx.FileDialog(
            self.dialog,
            message="Select audio file to transcribe",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._file_path_ctrl.SetValue(dlg.GetPath())

    def _on_diarize_toggle(self, event: object) -> None:
        enabled = self._diarize_cb.GetValue()
        self._max_speakers.Enable(enabled)
        if enabled:
            self._translate_cb.SetValue(False)
            self._translate_cb.Enable(False)
        else:
            self._translate_cb.Enable(True)

    def _on_translate_toggle(self, event: object) -> None:
        if self._translate_cb.GetValue():
            self._diarize_cb.SetValue(False)
            self._diarize_cb.Enable(False)
            self._max_speakers.Enable(False)
        else:
            self._diarize_cb.Enable(True)

    def _on_ok(self, event: object) -> None:
        wx = self._wx
        path_str = self._file_path_ctrl.GetValue().strip()
        if not path_str:
            wx.MessageBox(  # GATE-41-OK: standalone dialog  # MSGBOX-OK: standalone dialog
                "Please select an audio file to transcribe.",
                "No file selected",
                wx.OK | wx.ICON_WARNING,
                self.dialog,
            )
            return
        path = Path(path_str)
        if not path.exists():
            wx.MessageBox(  # GATE-41-OK: standalone dialog  # MSGBOX-OK: standalone dialog
                f"File not found: {path}",
                "File not found",
                wx.OK | wx.ICON_WARNING,
                self.dialog,
            )
            return
        lang_idx = self._lang_choice.GetSelection()
        lang_name = self._lang_choice.GetString(lang_idx)
        lang_code = SUPPORTED_LANGUAGES.get(lang_name, "")
        diarize = self._diarize_cb.GetValue()
        translate = self._translate_cb.GetValue()
        max_speakers = int(self._max_speakers.GetValue()) if diarize else 0
        self.dialog.EndModal(wx.ID_OK)
        self._on_transcribe(path, lang_code or None, translate, diarize, max_speakers)

    def show(self) -> bool:
        """Show modal. Returns True if user clicked Transcribe."""
        result = self._show_modal(self.dialog, "Transcribe Audio")
        wx = self._wx
        return result == wx.ID_OK


class AITranscriptionResultDialog:
    """Shows the finished transcript text with copy/replace/new-doc options."""

    def __init__(
        self,
        parent: object,
        transcript: str,
        file_name: str,
        show_modal_dialog: Callable,
        on_insert: Callable[[str], None] | None = None,
        on_new_document: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._transcript = transcript
        self._file_name = file_name
        self._show_modal = show_modal_dialog
        self._on_insert = on_insert
        self._on_new_document = on_new_document

        self.dialog = wx.Dialog(
            parent,
            title=f"Transcript - {file_name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(760, 560))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        word_count = len(self._transcript.split())
        summary = wx.StaticText(
            self.dialog,
            label=f"Transcript of {self._file_name}: {word_count} words.",
        )
        root.Add(summary, 0, wx.ALL, 8)

        self._text_ctrl = wx.TextCtrl(
            self.dialog,
            value=self._transcript,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.BORDER_SIMPLE,
        )
        self._text_ctrl.SetName("Transcript")
        root.Add(self._text_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label="&Copy to Clipboard")
        self._insert_btn = wx.Button(self.dialog, label="&Insert at Cursor")
        self._new_doc_btn = wx.Button(self.dialog, label="Open as &New Document")
        self._close_btn = wx.Button(self.dialog, label="C&lose")
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._close_btn.GetId(),
            escape_id=self._close_btn.GetId(),
        )
        if self._on_insert is None:
            self._insert_btn.Enable(False)
        if self._on_new_document is None:
            self._new_doc_btn.Enable(False)
        for b in (self._copy_btn, self._insert_btn, self._new_doc_btn, self._close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn_row, 0, wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._bind_events()
        wx.CallAfter(self._text_ctrl.SetFocus)

    def _bind_events(self) -> None:
        wx = self._wx
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._insert_btn.Bind(wx.EVT_BUTTON, self._on_insert_clicked)
        self._new_doc_btn.Bind(wx.EVT_BUTTON, self._on_new_doc)
        self._close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))

    def _on_copy(self, event: object) -> None:
        wx = self._wx
        text = self._text_ctrl.GetValue()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()

    def _on_insert_clicked(self, event: object) -> None:
        if self._on_insert is not None:
            self._on_insert(self._text_ctrl.GetValue())
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_new_doc(self, event: object) -> None:
        if self._on_new_document is not None:
            self._on_new_document(self._text_ctrl.GetValue())
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> None:
        self._show_modal(self.dialog, "Transcription Result")


class AIProgressDialog:
    """Simple non-modal progress indicator for long-running AI operations."""

    def __init__(
        self,
        parent: object,
        title: str,
        message: str,
        on_cancel: Callable[[], None] | None = None,
        status_fn: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_cancel = on_cancel
        # When provided, a "Minimize to status bar" button lets the user dismiss
        # the dialog while the download keeps running, with progress mirrored to
        # the status bar.
        self._status_fn = status_fn
        self._title = title
        self._minimized = False
        # Set only once switch_to_ok() has run -- the caller's reopen-the-hub
        # follow-up. Dismissing the completed dialog via the window's own close
        # box, Alt+F4, or Escape doesn't fire the relabeled button's click event,
        # so _on_dialog_close below is the fallback that still runs it (#kokoro-focus).
        self._completion_on_ok: Callable[[], None] | None = None

        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        self.dialog.SetSize(wx.Size(480, 180))
        root = wx.BoxSizer(wx.VERTICAL)
        self._label = wx.StaticText(self.dialog, label=message)
        self._label.Wrap(440)
        root.Add(self._label, 0, wx.ALL, 12)
        self._gauge = wx.Gauge(self.dialog, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self._gauge.Pulse()
        root.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self._cancel_btn: object = None
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        if status_fn is not None:
            min_btn = wx.Button(self.dialog, label="&Minimize to status bar")
            min_btn.SetName("Minimize to status bar")
            min_btn.Bind(wx.EVT_BUTTON, lambda _e: self._minimize())
            btn_row.Add(min_btn, 0, wx.RIGHT, 8)
        if on_cancel is not None:
            cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="&Cancel")
            cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: on_cancel())
            btn_row.Add(cancel_btn, 0)
            self._cancel_btn = cancel_btn
        btn_row.AddStretchSpacer()
        root.Add(btn_row, 0, wx.EXPAND | wx.BOTTOM, 8)
        self._btn_sizer_item_count = root.GetItemCount()
        self.dialog.SetSizer(root)
        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self.dialog.Bind(wx.EVT_CLOSE, self._on_dialog_close)

    def _on_dialog_close(self, event: object) -> None:
        """Destroy the dialog, running the completion follow-up if one is due.

        Handles the window's own close box, Alt+F4, and (on some platforms)
        Escape -- none of which fire the relabeled OK button's click event, so
        without this the caller's on_ok (e.g. reopening the Download Optional
        Components hub) was silently skipped.
        """
        on_ok = self._completion_on_ok
        self._completion_on_ok = None
        try:
            self.dialog.Destroy()
        except Exception:  # noqa: BLE001
            pass
        if on_ok is not None:
            on_ok()

    def _minimize(self) -> None:
        """Hide the dialog and continue showing progress in the status bar."""
        self._minimized = True
        try:
            self.dialog.Hide()
        except Exception:  # noqa: BLE001
            pass
        if self._status_fn is not None:
            self._status_fn(f"{self._title} continues in the status bar.")

    def update_message(self, message: str) -> None:
        self._wx.CallAfter(self._label.SetLabel, message)

    def set_progress(self, percent: int, message: str | None = None) -> None:
        """Switch the gauge to a determinate value (0-100) and optionally relabel.

        Safe to call from a worker thread; the widget update is marshalled to the
        UI thread. Negative ``percent`` leaves the gauge pulsing (indeterminate).
        """

        def _apply() -> None:
            if message is not None:
                self._label.SetLabel(message)
            if percent < 0:
                self._gauge.Pulse()
            else:
                self._gauge.SetValue(max(0, min(100, int(percent))))

        self._wx.CallAfter(_apply)
        # When minimized, the dialog is hidden, so mirror progress to the status bar.
        if self._minimized and self._status_fn is not None and message is not None:
            pct = f" ({max(0, min(100, int(percent)))}%)" if percent >= 0 else ""
            self._wx.CallAfter(self._status_fn, f"{self._title}: {message}{pct}")

    def switch_to_ok(
        self,
        message: str,
        on_ok: Callable[[], None] | None = None,
    ) -> None:
        """Thread-safe: complete the download — fill gauge, relabel button to OK.

        Replaces the Cancel button (if any) with an OK button that closes the
        dialog and optionally runs *on_ok* (e.g. reopening the voice browser).
        If no cancel button was created, adds a new OK button to the sizer.
        """
        wx = self._wx

        # If the user minimized the dialog, it is hidden — don't pop an OK button
        # they can't see. Report completion on the status bar and close. The
        # caller's on_ok follow-up (which would open another dialog) is skipped
        # so a minimized download never surprises the user with a popup.
        if self._minimized:
            if self._status_fn is not None:
                self._wx.CallAfter(self._status_fn, message)
            self.close()
            return

        self._completion_on_ok = on_ok

        def _apply() -> None:
            self._label.SetLabel(message)
            self._label.Wrap(440)
            self._gauge.SetValue(100)

            def _on_click(_e: object) -> None:
                self._completion_on_ok = None
                try:
                    self.dialog.Destroy()
                except Exception:  # noqa: BLE001
                    pass
                if on_ok is not None:
                    on_ok()

            btn = self._cancel_btn
            if btn is not None:
                btn.SetLabel("&OK")  # type: ignore[attr-defined]
                btn.Unbind(wx.EVT_BUTTON)  # type: ignore[attr-defined]
                btn.Bind(wx.EVT_BUTTON, _on_click)  # type: ignore[attr-defined]
            else:
                ok_btn = wx.Button(self.dialog, id=wx.ID_OK, label="&OK")
                ok_btn.Bind(wx.EVT_BUTTON, _on_click)
                sizer = self.dialog.GetSizer()
                sizer.Add(ok_btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 8)
                sizer.Layout()
                self.dialog.Fit()
            self.dialog.SetTitle(self.dialog.GetTitle() + " — Done")

        wx.CallAfter(_apply)

    def close(self) -> None:
        self._wx.CallAfter(self.dialog.Destroy)

    def show(self) -> None:
        # Center, raise, and focus so the dialog actually presents itself: a
        # screen reader announces it and a sighted user sees it on top, instead
        # of it appearing silently off to the side (or never being perceived).
        try:
            self.dialog.Centre()
        except Exception:  # noqa: BLE001
            pass
        self.dialog.Show()
        try:
            self.dialog.Raise()
            self.dialog.SetFocus()
        except Exception:  # noqa: BLE001
            pass
