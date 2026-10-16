"""Dictation Settings' Test Microphone button, split out of the dialog (GATE-11).

Moved from :mod:`quill.ui.windows_dictation_dialog` on 2026-10-15, when D-1's
command-mode controls and D-22's model recommendation together took that
module past its 600-line cap. The dialog inherits this mixin; nothing about the
button changed: it records four seconds on the chosen microphone off the UI
thread, says how loud it was and what was heard, and is enabled again after.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.windows_dictation.options import level_sentence

__all__ = ["MicrophoneTestMixin"]


class MicrophoneTestMixin:
    """Test Microphone: needs ``engine``, ``microphone``, ``speech_language``,
    ``test_microphone``, ``test_result``, ``_engine_ids``, ``_microphone_names``,
    ``_speech_languages`` and ``_announce`` on the dialog."""

    def _on_test_microphone(self, _event: Any) -> None:
        engine_row = self.engine.GetSelection()
        engine = self._engine_ids[engine_row] if 0 <= engine_row < len(self._engine_ids) else ""
        if engine == "voice_typing":
            self._show_test("Windows voice typing uses its own microphone settings, in Windows.")
            return
        row = self.microphone.GetSelection()
        microphone = self._microphone_names[row] if 0 <= row < len(self._microphone_names) else ""
        from quill.core.windows_dictation.local_recognizer import record_and_hear
        from quill.ui.update_download import thread_submit

        self.test_microphone.Disable()
        self.test_result.SetValue("Recording...")
        # Spoken, not shown: the person has to know when to start talking.
        self._announce("Speak now. Recording for four seconds.")

        language = self._speech_languages[max(0, self.speech_language.GetSelection())]

        def work(**_kwargs: Any) -> tuple[float, str]:
            return record_and_hear(microphone, engine, language=language)

        def done(_name: str, result: Any) -> None:
            peak, heard = result
            sentence = level_sentence(peak)
            if heard:
                sentence += f' It heard: "{heard}".'
            elif engine == "windows" and peak >= 0.02:
                sentence += " Windows speech recognition is tried by dictating."
            wx.CallAfter(self._show_test, sentence)

        def failed(_name: str, error: BaseException) -> None:
            said = str(error.args[0]) if error.args else ""  # the sentence, not the code
            wx.CallAfter(self._show_test, said or "The microphone test could not run.")

        thread_submit("quill-dictation-mic-test", work, on_success=done, on_failure=failed)

    def _show_test(self, sentence: str) -> None:
        if not self:
            return
        self.test_microphone.Enable()
        self.test_result.SetValue(sentence)
        self._announce(sentence)
