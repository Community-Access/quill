"""Dictation's 2026-10-05 commands, shared by QUILL and QUILL Lite.

The gap plan (dict.md sections 3.5, 3.7 and 3.8) added four commands to
Tools > Dictation in both editors, on the same chords (rule 2):

* **Switch Dictation Language** (Ctrl+Shift+F11): English to Spanish and back,
  without opening Dictation Settings. It is a choice rather than a mode, so it
  is saved, and the next session starts in the last language used. By voice:
  "switch to Spanish", and in Spanish "cambiar a inglés".
* **Live Transcript** (Ctrl+Alt+Shift+PageDown): a new document, written into
  quietly for as long as somebody else talks (``quill/core/windows_dictation/transcript.py``).
  The same key, or Ctrl+F11, stops it.
* **Dictation Context for This Document** (Ctrl+Alt+Shift+PageUp): what this
  document is, for OpenAI and Tidy Dictated Text
  (``quill/core/windows_dictation/contexts.py``).
* **Dictation Status** (Alt+F9, QUILL's Locked Dictation key, which in QUILL now
  answers for live dictation too): what dictation is doing, on demand.

Why each key is the one it is: ``quill/core/lite/commands_dictation.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

__all__ = ["DictationExtrasMixin", "finished_transcript"]

#: The text control attribute that marks a live transcript (preferences.py's
#: ``transcript`` profile, read where the AI window's profile is read).
_PROFILE = "_quill_dictation_profile"


def _shared() -> Any:
    from quill.ui import windows_dictation_commands

    return windows_dictation_commands


def finished_transcript(control: Any) -> None:
    """Dictation stopped: a transcript's document goes back to being a document,
    so Ctrl+F11 there later is ordinary dictation."""
    try:
        if getattr(control, _PROFILE, "") == "transcript":
            setattr(control, _PROFILE, "writing")
    except Exception:  # noqa: BLE001 - a closed control has nothing to reset
        pass


class DictationExtrasMixin:
    """Switch language, live transcripts, document context and status."""

    # -- hooks: QUILL Lite's answers; QUILL overrides them ---------------------- #

    def _dictation_document_path(self) -> Path | None:
        """Where this window's document is saved, or ``None`` while untitled."""
        path = getattr(self, "path", None)
        return Path(path) if path else None

    def _dictation_open_transcript_document(self) -> tuple[Any, Any]:
        """A new, empty, untitled document: ``(its host window, its text control)``."""
        app = self.app  # type: ignore[attr-defined]
        window = app.new_window(app.settings.default_mode)
        return window, window.control

    def _dictation_background_edit(self, control: Any) -> None:
        """A live transcript wrote into *control* while it was not in front.
        QUILL Lite's windows keep themselves in step from their own events."""
        del control

    # -- the family's shared settings (dict.md D-13) ------------------------------ #

    def _dictation_offer_old_model(self, before: str, after: str) -> None:
        """After Dictation Settings saved a switch, offer the old model's files
        (dictation_models_dialog.offer_to_remove_replaced) -- never while
        dictation, or the wake phrase, may still hold the old model."""
        from quill.ui.dictation_models_dialog import offer_to_remove_replaced
        from quill.ui.windows_dictation_commands import dictation_active, dictation_standing_by

        busy = dictation_active() or dictation_standing_by()
        offer_to_remove_replaced(
            self._dictation_parent(),  # type: ignore[attr-defined]
            before,
            after,
            self._dictation_say,  # type: ignore[attr-defined]
            in_use=busy,
        )

    def _dictation_share_settings(self) -> None:
        """Dictation Settings was saved: give the shared fields to the family,
        when "Share dictation settings with every QuillVille program" is on. A write that
        fails is said: this program's copy is saved, the others' is not."""
        from quill.core.windows_dictation.family_store import FamilyDictationError, publish

        try:
            publish(self._dictation_settings(), app=self._dictation_app())  # type: ignore[attr-defined]
        except FamilyDictationError as error:
            self._dictation_say(error.sentence)  # type: ignore[attr-defined]

    def _dictation_take_family(self) -> bool:
        """This program came to the front: take what another program saved.
        Said in the status bar only; the change is the person's own choice,
        made elsewhere, and is not worth interrupting them for."""
        from quill.core.windows_dictation.family_store import adopt

        try:
            changed = adopt(self._dictation_settings(), app=self._dictation_app())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a family file that cannot be read changes nothing
            return False
        if changed:
            self._dictation_save_settings()  # type: ignore[attr-defined]
            self._dictation_status("Dictation settings updated from the family.")  # type: ignore[attr-defined]
        return changed

    # -- the language ----------------------------------------------------------- #

    def cmd_switch_dictation_language(self) -> None:
        """English to Spanish, or Spanish to English, from now on."""
        current = self._dictation_preferences().speech_language  # type: ignore[attr-defined]
        target = "en" if current == "es" else "es"
        controller = _shared()._controller
        if controller is not None and (controller.active or controller.standing_by):
            controller.switch_language(target)
            return
        self._dictation_set_speech_language(target)
        self._dictation_say("Español." if target == "es" else "English.")  # type: ignore[attr-defined]

    def _dictation_set_speech_language(self, language: str) -> None:
        """Save the dictation language, and say if this copy cannot do it."""
        from quill.core.windows_dictation.engines import language_model_problem
        from quill.core.windows_dictation.settings_fields import settle_share

        settings = self._dictation_settings()  # type: ignore[attr-defined]
        settle_share(settings)  # sharing decided before anything changes (D-13)
        settings.windows_dictation_speech_language = "es" if language == "es" else "en"
        self._dictation_save_settings()  # type: ignore[attr-defined]
        self._dictation_share_settings()
        label = "Spanish" if language == "es" else "English"
        self._dictation_status(f"Dictation language: {label}")  # type: ignore[attr-defined]
        problem = language_model_problem(
            str(getattr(settings, "windows_dictation_engine", "")), language
        )
        if problem:
            self._dictation_say(problem)  # type: ignore[attr-defined]

    # -- live transcripts -------------------------------------------------------- #

    def cmd_live_transcript(self) -> None:
        """Start a live transcript in a new document, or stop the one running."""
        controller = self._dictation_controller()  # type: ignore[attr-defined]
        if controller.transcribing:
            controller.stop()  # says how many words it wrote
            return
        if self._dictation_preferences().engine == "voice_typing":  # type: ignore[attr-defined]
            self._dictation_say(  # type: ignore[attr-defined]
                "Live transcripts use QUILL's own speech engines. Choose one in "
                "Dictation Settings first."
            )
            return
        if controller.active:
            controller.stop()
        elif controller.standing_by:
            controller.disarm()
        host, control = self._dictation_open_transcript_document()
        setattr(control, _PROFILE, "transcript")
        host._dictation_target(host, control=control, pin=True, background=True)
        controller.begin_transcript()
        controller.start("Live transcript on, in a new document.")
        if not controller.active:
            finished_transcript(control)
            return
        settings = self._dictation_settings()  # type: ignore[attr-defined]
        if not getattr(settings, "windows_dictation_transcript_told", False):
            # Once, the first time, and always spoken: whatever the on and off
            # announcements are set to, this is not a cue.
            settings.windows_dictation_transcript_told = True
            self._dictation_save_settings()  # type: ignore[attr-defined]
            self._dictation_say("Please record other people only when they have agreed.")  # type: ignore[attr-defined]

    # -- this document's context ---------------------------------------------------- #

    def _dictation_contexts_file(self) -> Path:
        from quill.core.windows_dictation.contexts import contexts_path

        return contexts_path(self._dictation_profile_path())  # type: ignore[attr-defined]

    def _dictation_document_context(self) -> str:
        """What this document is, for OpenAI and Tidy, or ``""``."""
        path = self._dictation_document_path()
        if path is None:
            return str(getattr(self, "_dictation_untitled_context", ""))
        from quill.core.windows_dictation.contexts import load

        return load(self._dictation_contexts_file()).for_document(path)

    def _dictation_keep_context(self, text: str, save_name: str = "") -> None:
        from quill.core.windows_dictation.contexts import load, save

        store = load(self._dictation_contexts_file())
        if save_name:
            store.save_as(save_name, text)
        path = self._dictation_document_path()
        if path is None:
            self._dictation_untitled_context = " ".join(text.split())
        else:
            store.set_for_document(path, text)
        try:
            save(self._dictation_contexts_file(), store)
        except OSError as error:
            self._dictation_say(f"The dictation context could not be saved: {error}")  # type: ignore[attr-defined]

    def cmd_dictation_context(self) -> None:
        """Say what this document is: a formal letter, notes to a friend..."""
        from quill.core.windows_dictation.contexts import load
        from quill.ui.dictation_context_dialog import DictationContextDialog

        store = load(self._dictation_contexts_file())
        dialog = DictationContextDialog(
            self._dictation_parent(),  # type: ignore[attr-defined]
            self._dictation_document_context(),
            store.choices(),
            engine=self._dictation_preferences().engine,  # type: ignore[attr-defined]
        )
        try:
            answer = self._dictation_run_modal(dialog, "Dictation Context")  # type: ignore[attr-defined]
            text, name = dialog.values()
        finally:
            dialog.Destroy()
        if answer != wx.ID_OK:
            return
        self._dictation_keep_context(text, name)
        self._dictation_say(  # type: ignore[attr-defined]
            "Dictation context saved for this document."
            if text.strip()
            else "This document has no dictation context now."
        )

    def _dictation_use_context_by_name(self, words: tuple[str, ...]) -> str:
        """Voice: "dictation context formal letter". What to say about it."""
        from quill.core.windows_dictation.contexts import load
        from quill.core.windows_dictation.targets import match_names

        choices = load(self._dictation_contexts_file()).choices()
        said = " ".join(words)
        found = match_names(list(choices), words)
        if not found:
            return f"No saved context called {said}."
        if len(found) > 1:
            return f"{len(found)} contexts match {said}: " + ", ".join(found) + "."
        self._dictation_keep_context(choices[found[0]])
        return f"Dictation context: {found[0]}."

    # -- Dictate Anywhere ------------------------------------------------------------ #

    def _dictation_start_anywhere(self) -> None:
        """More Dictation Settings, Dictate in Other Programs: hand this editor's
        dictation settings to Quill Inkwell and start it (dict.md 3.9)."""
        from quill.core.app_launcher import launch_app
        from quill.core.paths import app_data_dir
        from quill.core.windows_dictation.anywhere import write_handoff

        try:
            write_handoff(app_data_dir(), self._dictation_settings())  # type: ignore[attr-defined]
        except OSError as error:
            self._dictation_say(f"Quill Inkwell could not be given your settings: {error}")  # type: ignore[attr-defined]
            return
        if self._dictation_hand_to_transcribe():
            return
        if not launch_app("inkwell", extra_args=("--dictate-anywhere",)):
            self._dictation_say(  # type: ignore[attr-defined]
                "Quill Inkwell is not installed with this copy. Install it from "
                "the QuillVille family to dictate into other programs."
            )
            return
        self._dictation_say(  # type: ignore[attr-defined]
            "Quill Inkwell is starting with your dictation settings. Choose the "
            "Dictate Anywhere key in its File menu."
        )

    def _dictation_hand_to_transcribe(self) -> bool:
        """QUILL Transcribe owns Dictate Anywhere where it runs or is released:
        hand the settings there instead of to Inkwell (quill/core/dictation_owner.py)."""
        from quill.core.app_launcher import is_app_released, launch_app
        from quill.core.dictation_owner import current_owner

        if current_owner() == "transcribe":
            from quill.core.ipc import enqueue_open_request

            enqueue_open_request(None, slot="transcribe")  # it takes the hand-off when shown
        elif not (
            is_app_released("transcribe")
            and launch_app("transcribe", extra_args=("--dictate-anywhere",))
        ):
            return False
        self._dictation_say(  # type: ignore[attr-defined]
            "QUILL Transcribe has your dictation settings. Use its start and stop key, "
            "or its tray menu, in the program you want to dictate into."
        )
        return True

    # -- status --------------------------------------------------------------------- #

    def cmd_dictation_status(self) -> None:
        """What dictation is doing now, said once."""
        self._dictation_say(self._dictation_status_sentence())  # type: ignore[attr-defined]

    def _dictation_status_sentence(self) -> str:
        from quill.core.windows_dictation.engines import ENGINES

        controller = _shared()._controller
        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        language = "Spanish" if preferences.speech_language == "es" else "English"
        names = {engine.id: engine.label.split(" (")[0] for engine in ENGINES}
        engine = names.get(preferences.engine, preferences.engine)
        if controller is None or not (controller.active or controller.standing_by):
            return f"Dictation is off. {engine}, in {language}."
        if controller.transcribing:
            return controller.transcript_status() + "."
        if controller.standing_by:
            return f"Waiting for the wake phrase, {preferences.wake_phrase}."
        modes = controller.mode_text
        spelling = " Spelling." if controller.spelling else ""
        # Command mode (D-1) is otherwise only in the status bar, which a
        # braille display does not show while the editor has the focus.
        command = str(getattr(controller, "command_mode_text", "") or "")
        return (
            f"Dictation on, {engine}, in {language}."
            + (f" {modes[:1].upper()}{modes[1:]} on." if modes else "")
            + spelling
            + (f" {command}." if command else "")
        )
