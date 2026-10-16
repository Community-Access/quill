"""Dictation Settings' cloud providers: the Speech Providers button, the engine
rows for providers that are set up, and the consent before one is chosen (D-31).

A mixin of :class:`~quill.ui.windows_dictation_dialog.WindowsDictationDialog`,
kept apart so that module stays under its 600-line cap (GATE-11). Shared by
every window that shows Dictation Settings -- QUILL, QUILL Lite, QUILL
Transcribe and Quill Inkwell -- so all four reach the same page and store.

Nothing here is saved before the dialog's OK: the providers' plain fields and
the consents wait in the dialog's pending ``_more`` choices like every other
More Dictation Settings value. (Secrets are the exception, by design: Save on
the Speech Providers page puts them in Windows Credential Manager at once.)
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.windows_dictation.cloud.registry import (
    CONSENT_SETTING,
    FIELDS_SETTING,
    engine_rows,
    provider_for_engine,
)

__all__ = ["CloudProvidersMixin"]


class CloudProvidersMixin:
    """Needs ``engine``, ``_engine_ids``, ``_engine_row``, ``_settings``,
    ``_more`` and ``_announce`` on the dialog."""

    def _pending(self, name: str) -> dict[str, Any]:
        value = self._more.get(name, getattr(self._settings, name, {}) or {})  # type: ignore[attr-defined]
        return dict(value) if isinstance(value, dict) else {}

    def _with_cloud_rows(self, rows: list[tuple[str, str]], saved: str) -> list[tuple[str, str]]:
        """*rows* plus every cloud provider that is set up (and *saved*, if it
        names one that is not)."""
        source = {FIELDS_SETTING: self._pending(FIELDS_SETTING)}
        known = {engine_id for engine_id, _label in rows}
        extra = [row for row in engine_rows(source, saved) if row[0] not in known]
        return rows + extra

    def _make_speech_providers_button(self, parent: Any) -> Any:
        button = wx.Button(parent, label="Speech Pro&viders...")
        button.SetHelpText(
            "Use a speech service you already have an account with: Microsoft Azure, "
            "Google Cloud, Amazon, Deepgram, AssemblyAI, Speechmatics, ElevenLabs, "
            "Gladia, Rev.ai, Groq, Mistral or IBM Watson. Enter what it needs and test "
            "it there, then choose it as the speech engine. Optional: the built-in "
            "engines need no account and never send anything anywhere."
        )
        button.Bind(wx.EVT_BUTTON, lambda _e: self.open_speech_providers())
        return button

    def open_speech_providers(self) -> None:
        """The Speech Providers page; its plain fields wait for this window's OK."""
        from quill.core.windows_dictation.engines import engine_choices
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.speech_providers_dialog import SpeechProvidersDialog

        dialog = SpeechProvidersDialog(self, self._pending(FIELDS_SETTING), self._announce)  # type: ignore[attr-defined]
        try:
            show_modal_dialog(dialog, "Speech Providers")
            self._more[FIELDS_SETTING] = dialog.stored()  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()
        row = self.engine.GetSelection()  # type: ignore[attr-defined]
        current = self._engine_ids[row] if 0 <= row < len(self._engine_ids) else ""  # type: ignore[attr-defined]
        rows = self._with_cloud_rows(engine_choices(current), current)
        self._engine_ids = [engine_id for engine_id, _label in rows]
        self.engine.Set([label for _id, label in rows])  # type: ignore[attr-defined]
        if current in self._engine_ids:
            self.engine.SetSelection(self._engine_ids.index(current))  # type: ignore[attr-defined]
            self._engine_row = self.engine.GetSelection()

    def _agree_to_cloud(self, engine: str) -> bool:
        """Choosing a cloud provider asks first, from its own facts. ``True`` when
        it may be used (already agreed, or agreed now); No is the default."""
        from quill.core.windows_dictation.cloud.consent import consent_text, consented
        from quill.core.windows_dictation.cloud.credentials import values_for
        from quill.ui.dialog_contract import show_message_box

        provider = provider_for_engine(engine)
        if provider is None:
            return True
        consents = self._pending(CONSENT_SETTING)
        if consented(provider, consents):
            return True
        values = values_for(provider, self._pending(FIELDS_SETTING).get(provider.id, {}))
        answer = show_message_box(
            consent_text(provider, values),
            "Use a Speech Provider",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            self._announce(f"{provider.name} was not chosen. Nothing was sent.")  # type: ignore[attr-defined]
            return False
        consents[provider.id] = provider.consent_version
        self._more[CONSENT_SETTING] = consents  # type: ignore[attr-defined]
        return True
