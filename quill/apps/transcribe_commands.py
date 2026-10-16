"""QUILL Transcribe's commands that are not dictation itself.

Setup, the model and microphone, the shared Dictation Settings and Model
Library windows, the options, the documents and the hand-over from an editor.
Each one saves through :func:`quill.core.transcribe.settings.save_settings`
and says its outcome once -- never the name of a window that just opened,
which the screen reader says already.
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["TranscribeCommandsMixin"]

_DOC_REPO = "quill-transcribe"


class TranscribeCommandsMixin:
    """On ``QuillTranscribeFrame``."""

    _settings: Any
    _data_dir: Any
    _safe_mode: bool
    frame: Any

    # -- saving ------------------------------------------------------------------ #

    def _save(self) -> None:
        from quill.core.transcribe.settings import save_settings

        try:
            save_settings(self._data_dir, self._settings)
        except OSError as error:
            self._announce(f"Your settings could not be saved: {error.strerror or error}")  # type: ignore[attr-defined]
        refresh = getattr(self, "_refresh_view", None)
        if callable(refresh):
            refresh()

    def _set_dictation_field(self, name: str, value: Any) -> None:
        self._settings.dictation = {**self._settings.dictation, name: value}
        self._save()

    def set_option(self, name: str, value: bool) -> None:
        setattr(self._settings, name, bool(value))
        self._save()

    # -- the model ---------------------------------------------------------------- #

    def _agree_to_openai(self) -> bool:
        """Ask before any speech goes to OpenAI. No is the default."""
        from quill.core.windows_dictation.openai_models import CONSENT_TEXT

        answer = self._show_message_box(  # type: ignore[attr-defined]
            CONSENT_TEXT, "Use OpenAI", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        return bool(answer == wx.YES)

    def _use_model(self, engine: str) -> None:
        from quill.core.transcribe.models import model_name

        if engine == "openai" and not self._settings.dictation.get(
            "windows_dictation_openai_consent", False
        ):
            if not self._agree_to_openai():
                self._announce(f"Kept {model_name(self.chosen_engine())}.")  # type: ignore[attr-defined]
                return
            self._settings.dictation = {
                **self._settings.dictation,
                "windows_dictation_openai_consent": True,
            }
        self._set_dictation_field("windows_dictation_engine", engine)
        later = " From the next time you start dictation." if self.dictation_active() else ""  # type: ignore[attr-defined]
        self._announce(f"Model: {model_name(engine)}.{later}")  # type: ignore[attr-defined]

    def choose_model(self) -> None:
        from quill.apps.transcribe_dialogs import ChooseModelDialog

        dialog = ChooseModelDialog(
            self.frame,
            current=self.chosen_engine(),
            open_library=self._library_for_dialog,
            language=self._language(),
        )
        try:
            answer = self._show_modal_dialog(dialog, "Choose Model")  # type: ignore[attr-defined]
            chosen = dialog.chosen
        finally:
            dialog.Destroy()
        if answer == wx.ID_OK and chosen and chosen != self.chosen_engine():
            self._use_model(chosen)

    def _library_for_dialog(self) -> None:
        chosen = self._open_library()
        if chosen:
            self._use_model(chosen)

    def _open_library(self) -> str | None:
        if self._safe_mode:
            self._announce("Safe Mode is on, so models cannot be downloaded.")  # type: ignore[attr-defined]
            return None
        from quill.ui.dictation_models_dialog import open_speech_models

        return open_speech_models(self.frame, self._announce, language=self._language())  # type: ignore[attr-defined]

    def _language(self) -> str:
        """The dictation language, which the model recommendation follows (D-22)."""
        return str(self._settings.dictation.get("windows_dictation_speech_language", "") or "en")

    def open_model_library(self) -> None:
        chosen = self._open_library()
        if chosen and chosen != self.chosen_engine():
            self._use_model(chosen)
        else:
            refresh = getattr(self, "_refresh_view", None)
            if callable(refresh):
                refresh()

    def choose_microphone(self) -> None:
        from quill.apps.transcribe_dialogs import choose_microphone

        current = str(self._settings.dictation.get("windows_dictation_microphone", "") or "")
        chosen = choose_microphone(self, current)
        if chosen is None or chosen == current:
            return
        self._set_dictation_field("windows_dictation_microphone", chosen)
        self._announce(f"Microphone: {chosen or 'the Windows default'}.")  # type: ignore[attr-defined]

    def edit_dictation_settings(self) -> None:
        """The same Dictation Settings window both editors show, over our copy."""
        from quill.apps.transcribe_talk import HELP_FOR
        from quill.core.windows_dictation.anywhere import stored_from
        from quill.ui.windows_dictation_dialog import WindowsDictationDialog

        settings = self._dictation_settings_object()  # type: ignore[attr-defined]
        before = settings.windows_dictation_engine
        wake_before = bool(settings.windows_dictation_wake_enabled)
        dialog = WindowsDictationDialog(
            self.frame,
            settings,
            self._announce,  # type: ignore[attr-defined]
            help_for=HELP_FOR,
            ai_on=self._review_ai_on(),  # type: ignore[attr-defined]
        )
        try:
            answer = self._show_modal_dialog(dialog, "Dictation Settings")  # type: ignore[attr-defined]
            if answer == wx.ID_OK:
                dialog.apply(settings)
        finally:
            dialog.Destroy()
        if answer != wx.ID_OK:
            return
        self._settings.dictation = stored_from(settings)
        self._save()
        from quill.core.transcribe.models import model_name

        if settings.windows_dictation_engine != before:
            self._announce(f"Saved. Model: {model_name(settings.windows_dictation_engine)}.")  # type: ignore[attr-defined]
        else:
            self._set_status("Dictation settings saved.")  # type: ignore[attr-defined]
        self._wake_settings_changed(wake_before)  # type: ignore[attr-defined]

    def edit_dictation_words(self) -> None:
        """My Words and Phrases: the editors' window, over the same word list
        (``dictation.md`` in the family's data folder) that dictation here uses."""
        from quill.core.speech.dictation_profile import default_profile_path
        from quill.ui.dictation_words_dialog import DictationWordsDialog

        dialog = DictationWordsDialog(
            self.frame,
            default_profile_path(),
            say=self._announce,  # type: ignore[attr-defined]
        )
        try:
            self._show_modal_dialog(dialog, "My Words and Phrases")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    # -- What can I say (D-7) ------------------------------------------------------- #

    def _external_reference(self) -> str:
        """Exactly what works in another program, with the person's own phrases
        (D-7): the editors' list leaves out nothing; this one leaves out what
        QUILL Transcribe refuses."""
        from quill.core.speech.dictation_profile import default_profile_path
        from quill.core.windows_dictation.profile import load
        from quill.core.windows_dictation.reference import commands_reference

        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        try:
            own = tuple(load(default_profile_path()).replacements)
        except Exception:  # noqa: BLE001 - the built-in list is still worth showing
            own = ()
        return commands_reference(
            external=True,
            dash=preferences.dash,
            stop_phrase=preferences.stop_phrase,
            own_phrases=own,
            language=preferences.speech_language,
            command_prefix=preferences.command_prefix,
            prefix_required=preferences.command_prefix_required,
        )

    def spoken_commands_summary(self) -> str:
        """Five commands, and where the full list is, by its key as bound now."""
        from quill.core.windows_dictation.anywhere import spoken_summary

        key = ""
        item_id = getattr(self, "_commands_item_id", None)
        menu_bar = self.frame.GetMenuBar() if item_id is not None else None
        item = menu_bar.FindItemById(int(item_id)) if menu_bar is not None else None
        if item is not None:
            key = str(item.GetItemLabel()).partition(chr(9))[2].strip()  # after the tab
        where = f", {key}" if key else ""
        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        # Strict mode (D-1, on here by default): the commands need the word.
        prefix = preferences.command_prefix if preferences.command_prefix_required else ""
        return spoken_summary(
            f"For the full list, open Dictation Commands from the Dictation menu{where}.",
            prefix=prefix,
        )

    def show_dictation_commands(self) -> None:
        from quill.ui.dictation_lists_dialog import DictationCommandsDialog

        dialog = DictationCommandsDialog(self.frame, self._external_reference())
        try:
            self._show_modal_dialog(dialog, "Dictation Commands")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    # -- setup ---------------------------------------------------------------------- #

    def _test_microphone(self, microphone: str, engine: str, show: Any) -> None:
        """Four seconds on *microphone*, heard by a model on this computer."""
        from quill.core.transcribe.models import FALLBACK_ENGINE
        from quill.core.windows_dictation.engines import is_model_engine
        from quill.core.windows_dictation.options import level_sentence
        from quill.ui.update_download import thread_submit

        if self._safe_mode:
            show("Safe Mode is on, so the microphone is not opened.")
            return
        listen_with = engine if is_model_engine(engine) else FALLBACK_ENGINE
        self._announce("Speak now. Recording for four seconds.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> tuple[float, str]:
            from quill.core.windows_dictation.local_recognizer import record_and_hear

            return record_and_hear(microphone, listen_with)

        def done(_name: str, result: Any) -> None:
            peak, heard = result
            sentence = level_sentence(peak) + (f' It heard: "{heard}".' if heard else "")
            wx.CallAfter(self._finish_test, show, sentence)

        def failed(_name: str, error: BaseException) -> None:
            said = str(error.args[0]) if error.args else ""
            wx.CallAfter(self._finish_test, show, said or "The microphone test could not run.")

        thread_submit("transcribe-mic-test", work, on_success=done, on_failure=failed)

    def _finish_test(self, show: Any, sentence: str) -> None:
        show(sentence)
        self._announce(sentence)  # type: ignore[attr-defined]

    def open_setup(self) -> None:
        """Set Up QUILL Transcribe: microphone, model, key, start with Windows."""
        from quill.apps.transcribe_dialogs import SetupDialog
        from quill.core.family_chords import show_hide_key_problem
        from quill.ui.show_hide_key_picker import _family_choices

        microphone = str(self._settings.dictation.get("windows_dictation_microphone", "") or "")
        engine, key = self.chosen_engine(), self._settings.dictation_hotkey
        command = self._settings.command_hotkey
        at_login = self.launch_at_startup_enabled()
        while True:
            dialog = SetupDialog(
                self.frame,
                microphone=microphone,
                engine=engine,
                key=key,
                at_login=at_login,
                test_microphone=self._test_microphone,
                show_modal=self._show_modal_dialog,  # type: ignore[attr-defined]
                command_key=command,
                language=self._language(),
            )
            try:
                answer = self._show_modal_dialog(dialog, "Set Up QUILL Transcribe")  # type: ignore[attr-defined]
                microphone, engine = dialog.chosen_microphone(), dialog.chosen_engine()
                key, at_login = dialog.chosen_key(), bool(dialog.at_login.GetValue())
                command = dialog.chosen_command_key()
            finally:
                dialog.Destroy()
            if answer != wx.ID_OK:
                if not self._settings.setup_done:
                    self._settings.setup_done = True
                    self._save()
                self._announce("Setup skipped. It is on the Help menu whenever you want it.")  # type: ignore[attr-defined]
                return
            problem = show_hide_key_problem(
                key,
                app_id="transcribe",
                taken=_family_choices(),
                own=self._own_keys("dictation"),  # type: ignore[attr-defined]
            )
            if not problem and key != self._settings.dictation_hotkey and not self._safe_mode:
                if not self._register_dictation_key(key):  # type: ignore[attr-defined]
                    problem = (
                        f"Windows says another program is already using {key}. Windows "
                        "does not say which one. Choose another key, or leave the box empty."
                    )
            if not problem:
                problem = self._setup_command_key_problem(command, key)
            if not problem:
                break
            self._show_message_box(problem, "Set Up QUILL Transcribe", wx.OK | wx.ICON_WARNING)  # type: ignore[attr-defined]
        self._settings.dictation = {
            **self._settings.dictation,
            "windows_dictation_microphone": microphone,
        }
        self._settings.dictation_hotkey = key
        self._settings.command_hotkey = command
        self._settings.setup_done = True
        if engine and engine != self.chosen_engine():
            self._use_model(engine)
        else:
            self._save()
        if at_login != self.launch_at_startup_enabled():
            self.set_launch_at_startup(at_login, quiet=True)
        from quill.core.transcribe.models import model_name

        how = f"press {key} in the field you want" if key else "use the tray menu"
        commands = f" For a command, press {command} first." if command else ""
        self._announce(  # type: ignore[attr-defined]
            f"Ready. Model: {model_name(self.chosen_engine())}. To dictate, {how}.{commands}"
        )

    def _setup_command_key_problem(self, command: str, key: str) -> str:
        """Why the Command Key typed in setup cannot be used, or ``""`` once it is
        registered (D-1). It may not be the start and stop key."""
        from quill.core.family_chords import show_hide_key_problem
        from quill.ui.show_hide_key_picker import _family_choices

        if command and command.lower() == key.lower():
            return "The Command Key and the start and stop key must be different keys."
        own = {**self._own_keys("command"), "start and stop key": key}  # type: ignore[attr-defined]
        problem = show_hide_key_problem(
            command, app_id="transcribe", taken=_family_choices(), own=own
        )
        if problem or command == self._settings.command_hotkey or self._safe_mode:
            return str(problem or "")
        if not self._register_command_key(command):  # type: ignore[attr-defined]
            return (
                f"Windows says another program is already using {command}. Windows does "
                "not say which one. Choose another Command Key, or leave the box empty."
            )
        return ""

    # -- options --------------------------------------------------------------------- #

    def launch_at_startup_enabled(self) -> bool:
        try:
            from quill.platform.windows import transcribe_startup

            return bool(transcribe_startup.is_launch_at_startup_enabled())
        except Exception:  # noqa: BLE001
            return False

    def set_launch_at_startup(self, enabled: bool, *, quiet: bool = False) -> None:
        try:
            from quill.platform.windows import transcribe_startup

            transcribe_startup.set_launch_at_startup(enabled)
        except Exception:  # noqa: BLE001
            self._announce("Could not change the Windows startup setting.")  # type: ignore[attr-defined]
            return
        menu_bar = self.frame.GetMenuBar()
        item_id = getattr(self, "_startup_item_id", None)
        if menu_bar is not None and item_id is not None:
            found = menu_bar.FindItemById(int(item_id))
            if found is not None:
                found.Check(enabled)
        if not quiet:
            self._announce(  # type: ignore[attr-defined]
                "QUILL Transcribe will start with Windows, in the tray."
                if enabled
                else "QUILL Transcribe will not start with Windows."
            )

    # -- documents, updates, the editors ----------------------------------------------- #

    def open_user_guide(self) -> None:
        self.open_app_document(  # type: ignore[attr-defined]
            self._doc_candidates(_DOC_REPO, "userguide"),  # type: ignore[attr-defined]
            title="QUILL Transcribe User Guide",
            cache_name="app-docs",
        )

    def take_dictation_handoff(self) -> bool:
        """An editor's Dictate in Other Programs: take its settings, once."""
        from quill.core.windows_dictation.anywhere import take_handoff

        stored = take_handoff(self._data_dir)
        if stored is None:
            return False
        self._settings.dictation = stored
        self._save()
        key = self._settings.dictation_hotkey
        self._announce(  # type: ignore[attr-defined]
            f"QUILL Transcribe has your dictation settings. Press {key} in any program to start."
            if key
            else "QUILL Transcribe has your dictation settings. Choose a start and stop "
            "key in the File menu, or start from the tray."
        )
        return True
