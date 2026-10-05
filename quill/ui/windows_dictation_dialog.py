"""Dictation Settings: the engine, the microphone, and what you hear.

Dictation has to work well without anybody opening this window. It holds:

* **Which speech engine** -- Moonshine (the default), Whisper, Windows' own
  recogniser, and any optional model downloaded with **Better Accuracy: Speech
  Models...** (:mod:`quill.ui.dictation_models_dialog`).
* **Which microphone**, saved by name: the one thing every engine agrees on,
  where tokens and device numbers change when a device is replugged.
* **What happens after each phrase** (the shared
  :data:`~quill.core.action_feedback.ACTION_FEEDBACK_LABELS`), sounds, and
  saying "Dictation on" and "Dictation off".
* **The finer choices** (:mod:`quill.core.windows_dictation.options`).
* **Test Microphone**: four seconds on a worker; the result goes into a field
  beside the button and is spoken, because a field changing beside the focused
  button is exactly what a screen reader does not announce.
* **More Dictation Settings...** (:mod:`quill.ui.dictation_more_dialog`):
  holding the key, the live preview, talking to the AI, and OpenAI. Choosing
  OpenAI as the engine asks first, in plain words, whether your speech may be
  sent (:data:`~quill.core.windows_dictation.openai_models.CONSENT_TEXT`).

Nothing is applied until OK, and :meth:`WindowsDictationDialog.apply` writes
only the fields this window owns.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.action_feedback import ACTION_FEEDBACK_LABELS
from quill.core.action_feedback import coerce as coerce_feedback
from quill.core.windows_dictation.controller import DEFAULT_PHRASE_FEEDBACK
from quill.core.windows_dictation.engines import (
    ENGINES,
    coerce_engine,
    engine_choices,
    language_model_problem,
)
from quill.core.windows_dictation.options import (
    PAUSE_CHOICES,
    SILENCE_CHOICES,
    coerce_pause,
    coerce_silence,
    level_sentence,
)
from quill.core.windows_dictation.speech_language import (
    SPEECH_LANGUAGES,
    STOP_PHRASES,
    WAKE_PHRASES,
    coerce_speech_language,
    localised_phrase,
)
from quill.core.windows_dictation.vocabulary import DASH_STYLES
from quill.core.windows_dictation.wake import (
    DEFAULT_STOP_PHRASE,
    DEFAULT_WAKE_PHRASE,
    stop_phrase_problem,
    wake_phrase_problem,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box
from quill.ui.dictation_lists_dialog import DictationCommandsDialog, RecentPhrasesDialog
from quill.ui.windows_dictation_devices import (
    default_microphone_name,
    microphone_names,
    recognizer_names,
)

__all__ = [
    "EDIT_INSTRUCTIONS",
    "EDIT_OPENAI_KEY",
    "EDIT_WORDS",
    "SHOW_COMMANDS",
    "DictationCommandsDialog",
    "RecentPhrasesDialog",
    "WindowsDictationDialog",
]

#: What the two extra buttons end the dialog with. Edit My Words saves the
#: settings first -- a person who changed the engine and then went to add a word
#: should not lose the engine.
SHOW_COMMANDS = 5801
EDIT_WORDS = 5802
EDIT_INSTRUCTIONS = 5803  # quill.ui.dictation_more_dialog's, passed on
EDIT_OPENAI_KEY = 5804  # quill.ui.dictation_more_dialog's, passed on

_PAD = 8


class WindowsDictationDialog(wx.Dialog):
    """The dictation settings. Read with :meth:`apply` after OK."""

    def __init__(
        self, parent: Any, settings: Any, announce: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(parent, title="Dictation Settings")
        self._announce = announce or (lambda _text: None)
        self._settings = settings
        #: More Dictation Settings' choices, applied with this window's OK.
        self._more: dict[str, object] = {}
        # Two columns, so the window fits a 768-pixel-high screen. Tab order is
        # creation order, which runs down the left column and then the right.
        outer = wx.BoxSizer(wx.VERTICAL)
        columns = wx.BoxSizer(wx.HORIZONTAL)
        root = wx.BoxSizer(wx.VERTICAL)  # the left column: what is heard and written

        engine_label = wx.StaticText(self, label="Speech &engine:")
        saved_engine = coerce_engine(getattr(settings, "windows_dictation_engine", ""))
        rows = engine_choices(saved_engine)
        self._engine_ids = [engine_id for engine_id, _label in rows]
        self.engine = wx.Choice(self, choices=[label for _id, label in rows])
        self.engine.SetHelpText(
            "Which speech recogniser dictation uses. "
            + " ".join(f"{engine.label}: {engine.description}" for engine in ENGINES)
            + " Models you download with Better Accuracy: Speech Models are listed too."
        )
        self.engine.SetSelection(self._engine_ids.index(saved_engine))
        self._engine_row = self.engine.GetSelection()
        self.engine.Bind(wx.EVT_CHOICE, self._on_engine)
        root.Add(engine_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.engine, 0, wx.EXPAND | wx.ALL, _PAD)
        self.speech_models = wx.Button(self, label="&Better Accuracy: Speech Models...")
        self.speech_models.SetHelpText(
            "Optional, larger speech models for better accuracy -- the ones VS Code "
            "offers and the rest of the Whisper family -- to download, remove or choose. "
            "Dictation works without them."
        )
        self.speech_models.Bind(wx.EVT_BUTTON, self._on_speech_models)
        root.Add(self.speech_models, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

        speech_label = wx.StaticText(self, label="Dictation lan&guage:")
        self._speech_languages = [value for value, _label in SPEECH_LANGUAGES]
        self.speech_language = wx.Choice(self, choices=[label for _v, label in SPEECH_LANGUAGES])
        self.speech_language.SetHelpText(
            "The language you dictate in: English, or Spanish, which is new. In Spanish, "
            "Moonshine and Whisper both use Whisper's multilingual model; Windows speech "
            "recognition needs Spanish installed in Windows. Commands stay in English for "
            "now, and Spanish punctuation words such as coma and punto work while automatic "
            "punctuation is off."
        )
        saved = getattr(settings, "windows_dictation_speech_language", "")
        self.speech_language.SetSelection(
            self._speech_languages.index(coerce_speech_language(saved))
        )
        self.speech_language.Bind(wx.EVT_CHOICE, self._on_speech_language)
        root.Add(speech_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.speech_language, 0, wx.EXPAND | wx.ALL, _PAD)

        self.auto_punctuation = wx.CheckBox(
            self, label="Automatic punctuat&ion (Moonshine and Whisper)"
        )
        self.auto_punctuation.SetValue(
            bool(getattr(settings, "windows_dictation_auto_punctuation", True))
        )
        self.auto_punctuation.SetHelpText(
            "On: Moonshine and Whisper put in full stops, commas and question marks "
            "by themselves, and any mark you say still wins. Off: nothing is added "
            "for you, and a sentence runs on until you say a mark, as with Windows "
            "speech recognition, which never punctuates by itself."
        )
        root.Add(self.auto_punctuation, 0, wx.ALL, _PAD)

        language_label = wx.StaticText(self, label="&Language for Windows speech recognition:")
        self._languages = [""] + recognizer_names()
        self.language = wx.Choice(self, choices=["Windows default"] + self._languages[1:])
        self.language.SetHelpText(
            "Which of the speech languages installed in Windows the Windows speech "
            "recognition engine listens for. Moonshine and Whisper ignore this and "
            "follow the dictation language. Add languages in Windows Settings, Time "
            "and language, Speech."
        )
        saved_language = str(getattr(settings, "windows_dictation_language", "") or "")
        self.language.SetSelection(
            self._languages.index(saved_language) if saved_language in self._languages else 0
        )
        root.Add(language_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.language, 0, wx.EXPAND | wx.ALL, _PAD)

        names = microphone_names()
        self._microphone_names = [""] + names
        default_name = default_microphone_name()
        default_row = (
            f"Windows default microphone ({default_name})"
            if default_name
            else "Windows default microphone"
        )
        mic_label = wx.StaticText(self, label="&Microphone:")
        self.microphone = wx.Choice(self, choices=[default_row] + names)
        self.microphone.SetHelpText(
            "The microphone dictation listens on. The Windows default follows "
            "whatever Windows Sound settings choose as the default recording "
            "device; choose a named microphone to keep using that one whatever "
            "the default becomes. If the chosen microphone is unplugged, starting "
            "dictation says so rather than quietly listening on another."
        )
        chosen = str(getattr(settings, "windows_dictation_microphone", "") or "")
        if chosen.startswith("HKEY_"):
            # Saved by an earlier 1.1 build as a Windows speech token. Mapped
            # back to its name when the microphone is here; otherwise dropped,
            # because a registry path means nothing to the other engines.
            chosen = next((name for name in names if chosen.lower().endswith(name.lower())), "")
        if chosen and chosen not in self._microphone_names:
            # Remembered but not connected. Kept as a row, so pressing OK does
            # not silently forget the headset somebody has only unplugged.
            self._microphone_names.append(chosen)
            self.microphone.Append(f"{chosen} (not connected)")
        self.microphone.SetSelection(self._microphone_names.index(chosen) if chosen else 0)
        root.Add(mic_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.microphone, 0, wx.EXPAND | wx.ALL, _PAD)

        test_row = wx.BoxSizer(wx.HORIZONTAL)
        self.test_microphone = wx.Button(self, label="Test Micropho&ne")
        self.test_microphone.SetHelpText(
            "Records four seconds on the chosen microphone -- start speaking when "
            "you hear Speak now -- then says how loud it was and, with an engine that "
            "runs on this computer, what the engine heard. Nothing is kept."
        )
        self.test_microphone.Bind(wx.EVT_BUTTON, self._on_test_microphone)
        self.test_result = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.test_result.SetHelpText("What the last microphone test found.")
        self.test_result.SetName("Microphone test result")
        test_row.Add(self.test_microphone, 0, wx.RIGHT, _PAD)
        test_row.Add(self.test_result, 1, wx.EXPAND)
        root.Add(test_row, 0, wx.EXPAND | wx.ALL, _PAD)

        feedback_label = wx.StaticText(self, label="After each &phrase is written, give me:")
        self._feedback_values = [str(mode) for mode, _label in ACTION_FEEDBACK_LABELS]
        self.feedback = wx.Choice(self, choices=[label for _mode, label in ACTION_FEEDBACK_LABELS])
        self.feedback.SetHelpText(
            "What you hear each time a phrase goes into the document. A sound is "
            "a short tone. Speech reads back the words that were written, so you "
            "can hear whether they are the words you said. Use headphones if you "
            "choose speech: read back through speakers, the microphone can hear "
            "it and write it down again."
        )
        mode = str(
            coerce_feedback(
                getattr(settings, "windows_dictation_phrase_feedback", DEFAULT_PHRASE_FEEDBACK)
            )
        )
        self.feedback.SetSelection(self._feedback_values.index(mode))
        root.Add(feedback_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.feedback, 0, wx.EXPAND | wx.ALL, _PAD)

        dash_label = wx.StaticText(self, label='Saying "&dash" writes:')
        self._dash_styles = list(DASH_STYLES)
        self.dash = wx.Choice(self, choices=[label for label, _text in DASH_STYLES.values()])
        self.dash.SetHelpText(
            "What the spoken word dash writes. A hyphen, said as hyphen, is "
            "always a plain hyphen that joins two words."
        )
        dash = str(getattr(settings, "windows_dictation_dash", "em") or "em")
        self.dash.SetSelection(self._dash_styles.index(dash) if dash in self._dash_styles else 0)
        root.Add(dash_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.dash, 0, wx.EXPAND | wx.ALL, _PAD)

        pause_label = wx.StaticText(self, label="Pa&use before a phrase is written:")
        self._pauses = [value for value, _label in PAUSE_CHOICES]
        self.pause = wx.Choice(self, choices=[label for _value, label in PAUSE_CHOICES])
        self.pause.SetHelpText(
            "How long you can stop talking before what you said is written. Choose "
            "Long if dictation cuts you off while you are still thinking; Short "
            "writes sooner after you stop."
        )
        self.pause.SetSelection(
            self._pauses.index(coerce_pause(getattr(settings, "windows_dictation_pause", "")))
        )
        root.Add(pause_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.pause, 0, wx.EXPAND | wx.ALL, _PAD)

        self.remove_fillers = wx.CheckBox(self, label="Remove filler words li&ke um and uh")
        self.remove_fillers.SetValue(
            bool(getattr(settings, "windows_dictation_remove_fillers", False))
        )
        self.remove_fillers.SetHelpText(
            "Leave out hesitations -- um, uh, erm, hmm -- instead of writing them. "
            "Real words are never removed."
        )
        root.Add(self.remove_fillers, 0, wx.ALL, _PAD)

        self.continuous = wx.CheckBox(
            self, label="&Just write what I say: nothing happens at a pause"
        )
        self.continuous.SetValue(bool(getattr(settings, "windows_dictation_continuous", False)))
        self.continuous.SetHelpText(
            "For talking in one long run and pausing wherever you like. A pause "
            "then puts in no full stop, plays no sound and reads nothing back, and "
            "voice commands are written as words -- only the stop phrase still "
            "stops dictation. Punctuation you say still works."
        )
        root.Add(self.continuous, 0, wx.ALL, _PAD)

        columns.Add(root, 1, wx.EXPAND)
        root = wx.BoxSizer(wx.VERTICAL)  # the right column: starting and stopping
        self.cue_sounds = wx.CheckBox(
            self, label="Play &sounds when dictation starts, stops or fails"
        )
        self.cue_sounds.SetValue(bool(getattr(settings, "windows_dictation_cue_sounds", True)))
        self.cue_sounds.SetHelpText(
            "A rising pair of tones when dictation starts listening, a falling "
            "pair when it stops, and a low double tone when something goes wrong. "
            "A failure is always spoken as well, whatever this is set to."
        )
        root.Add(self.cue_sounds, 0, wx.ALL, _PAD)

        self.announce = wx.CheckBox(self, label='Say "Dictation on" and "Dictation &off"')
        self.announce.SetValue(bool(getattr(settings, "windows_dictation_announce", True)))
        self.announce.SetHelpText(
            "Speak the words as well as, or instead of, the sounds when dictation "
            "starts and stops. With both off, the check mark on the Dictation "
            "menu item still shows whether it is on."
        )
        root.Add(self.announce, 0, wx.ALL, _PAD)

        self.wake = wx.CheckBox(self, label="Listen for the wake p&hrase while dictation is off")
        self.wake.SetValue(bool(getattr(settings, "windows_dictation_wake_enabled", False)))
        self.wake.SetHelpText(
            "Start dictation by saying the wake phrase instead of pressing a key. "
            "While this is on, the microphone stays open whenever this program is "
            "the window in front -- nothing it hears is written, kept or sent "
            "anywhere until it hears the wake phrase -- and it closes whenever "
            "another program comes to the front. Off unless you turn it on."
        )
        root.Add(self.wake, 0, wx.ALL, _PAD)

        wake_label = wx.StaticText(self, label="&Wake phrase:")
        self.wake_phrase = wx.TextCtrl(
            self,
            value=str(
                getattr(settings, "windows_dictation_wake_phrase", "") or DEFAULT_WAKE_PHRASE
            ),
        )
        self.wake_phrase.SetHelpText(
            "The words that start dictation, at least two of them. Choose words "
            "you would not say in passing: a name and a verb works well, like the "
            "default, Quill dictate. Anything you say after it in the same breath "
            "is written."
        )
        root.Add(wake_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.wake_phrase, 0, wx.EXPAND | wx.ALL, _PAD)

        stop_label = wx.StaticText(self, label="S&top phrase:")
        self.stop_phrase = wx.TextCtrl(
            self,
            value=str(
                getattr(settings, "windows_dictation_stop_phrase", "") or DEFAULT_STOP_PHRASE
            ),
        )
        self.stop_phrase.SetHelpText(
            "The words that stop dictation, at least two of them, said on their "
            "own after a pause. Stop dictation always works as well. With the wake "
            "phrase on, stopping goes back to listening for the wake phrase."
        )
        root.Add(stop_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.stop_phrase, 0, wx.EXPAND | wx.ALL, _PAD)

        silence_label = wx.StaticText(self, label="Stop dictation a&fter silence:")
        self._silences = [minutes for minutes, _label in SILENCE_CHOICES]
        self.silence = wx.Choice(self, choices=[label for _minutes, label in SILENCE_CHOICES])
        self.silence.SetHelpText(
            "Stop dictation by itself when it has heard nothing for this long, so it "
            "is not left writing in an empty room. With the wake phrase on, it goes "
            "back to waiting for the wake phrase instead."
        )
        self.silence.SetSelection(
            self._silences.index(
                coerce_silence(getattr(settings, "windows_dictation_silence_minutes", 0))
            )
        )
        root.Add(silence_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.silence, 0, wx.EXPAND | wx.ALL, _PAD)

        more = wx.BoxSizer(wx.HORIZONTAL)
        commands = wx.Button(self, label="Dictation &Commands...")
        commands.SetHelpText(
            "The list of everything dictation understands: punctuation, layout, "
            "the commands, spelling, and your own phrases. Saying what can I say "
            "while dictating opens the same list."
        )
        commands.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(SHOW_COMMANDS))
        words = wx.Button(self, label="My Wo&rds and Phrases...")
        words.SetHelpText(
            "Add, change and remove your own words for dictation in a window: "
            "names and jargon to spell your way, phrases that write whatever you "
            "choose, and corrections for what the engine keeps hearing wrong. "
            "Saves these settings first."
        )
        words.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(EDIT_WORDS))
        more.Add(commands, 0, wx.RIGHT, _PAD)
        more.Add(words, 0)
        root.Add(more, 0, wx.ALL, _PAD)
        self.more_button = wx.Button(self, label="More Dict&ation Settings...")
        self.more_button.SetHelpText(
            "Holding Ctrl+F11 to talk, the words heard so far while you speak, how "
            "dictation behaves when you talk to the AI, OpenAI with your own key, and "
            "My Dictation Instructions."
        )
        self.more_button.Bind(wx.EVT_BUTTON, lambda _e: self.open_more())
        root.Add(self.more_button, 0, wx.ALL, _PAD)

        columns.Add(root, 1, wx.EXPAND)
        outer.Add(columns, 1, wx.EXPAND)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(outer)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.engine.SetFocus()

    def _on_ok(self, event: Any) -> None:
        """Refuse a wake or stop phrase that would start or stop dictation by accident."""
        checks = [(stop_phrase_problem(self.stop_phrase.GetValue()), self.stop_phrase)]
        if self.wake.GetValue():
            checks.insert(0, (wake_phrase_problem(self.wake_phrase.GetValue()), self.wake_phrase))
        for problem, field in checks:
            if problem:
                show_message_box(problem, "Dictation Settings", wx.OK | wx.ICON_WARNING, self)
                field.SetFocus()
                return
        event.Skip()

    def _on_speech_language(self, _event: Any) -> None:
        """Default wake and stop phrases follow the language; a missing model is said."""
        language = self._speech_languages[max(0, self.speech_language.GetSelection())]
        for field, defaults in ((self.wake_phrase, WAKE_PHRASES), (self.stop_phrase, STOP_PHRASES)):
            field.SetValue(localised_phrase(field.GetValue(), language, defaults))
        engine = self._engine_ids[max(0, self.engine.GetSelection())]
        problem = language_model_problem(engine, language)
        if problem:
            self._show_test(problem)

    def _on_engine(self, _event: Any) -> None:
        """Choosing OpenAI asks first whether speech may leave the computer."""
        from quill.core.windows_dictation.engines import CLOUD_ENGINE
        from quill.core.windows_dictation.openai_models import CONSENT_TEXT

        row = self.engine.GetSelection()
        engine = self._engine_ids[row] if 0 <= row < len(self._engine_ids) else ""
        agreed = self._more.get(
            "windows_dictation_openai_consent",
            getattr(self._settings, "windows_dictation_openai_consent", False),
        )
        if engine != CLOUD_ENGINE or agreed:
            self._engine_row = row
            return
        answer = show_message_box(
            CONSENT_TEXT, "OpenAI Dictation", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self
        )
        if answer != wx.YES:
            self.engine.SetSelection(self._engine_row)
            self._announce("OpenAI was not chosen. Nothing was sent.")
            return
        self._engine_row = row
        self._more["windows_dictation_openai_consent"] = True
        self.open_more(focus_model=True)

    def open_more(self, *, focus_model: bool = False) -> None:
        """More Dictation Settings, its choices kept until this window's OK."""
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.dictation_more_dialog import EDIT_INSTRUCTIONS as MORE_INSTRUCTIONS
        from quill.ui.dictation_more_dialog import EDIT_OPENAI_KEY as MORE_KEY
        from quill.ui.dictation_more_dialog import MoreDictationDialog

        dialog = MoreDictationDialog(self, self._settings, self._announce, pending=self._more)
        if focus_model:
            dialog.focus_model()
        try:
            answer = show_modal_dialog(dialog, "More Dictation Settings")
            if answer in (wx.ID_OK, MORE_INSTRUCTIONS, MORE_KEY):
                self._more.update(dialog.values())
        finally:
            dialog.Destroy()
        if answer == MORE_INSTRUCTIONS:
            self.EndModal(EDIT_INSTRUCTIONS)
        elif answer == MORE_KEY:
            self.EndModal(EDIT_OPENAI_KEY)

    def _on_speech_models(self, _event: Any) -> None:
        """Speech Models, then the engine list again: a model may have come or gone."""
        from quill.ui.dictation_models_dialog import open_speech_models

        current = self._engine_ids[max(0, self.engine.GetSelection())]
        chosen = open_speech_models(self, self._announce) or current
        rows = engine_choices(chosen)
        self._engine_ids = [engine_id for engine_id, _label in rows]
        self.engine.Set([label for _id, label in rows])
        self.engine.SetSelection(self._engine_ids.index(chosen))

    # -- Test Microphone -------------------------------------------------- #

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

    def apply(self, settings: Any) -> None:
        """Write every choice into *settings*. The caller saves."""
        engine = self.engine.GetSelection()
        if 0 <= engine < len(self._engine_ids):
            settings.windows_dictation_engine = self._engine_ids[engine]
        speech = self.speech_language.GetSelection()
        settings.windows_dictation_speech_language = self._speech_languages[max(0, speech)]
        row = self.microphone.GetSelection()
        settings.windows_dictation_microphone = (
            self._microphone_names[row] if 0 <= row < len(self._microphone_names) else ""
        )
        choice = self.feedback.GetSelection()
        if 0 <= choice < len(self._feedback_values):
            settings.windows_dictation_phrase_feedback = self._feedback_values[choice]
        settings.windows_dictation_cue_sounds = self.cue_sounds.GetValue()
        language = self.language.GetSelection()
        settings.windows_dictation_language = (
            self._languages[language] if 0 <= language < len(self._languages) else ""
        )
        dash = self.dash.GetSelection()
        if 0 <= dash < len(self._dash_styles):
            settings.windows_dictation_dash = self._dash_styles[dash]
        phrase = " ".join(self.wake_phrase.GetValue().split())
        settings.windows_dictation_wake_phrase = phrase or DEFAULT_WAKE_PHRASE
        settings.windows_dictation_wake_enabled = bool(
            self.wake.GetValue() and not wake_phrase_problem(phrase)
        )
        settings.windows_dictation_announce = self.announce.GetValue()
        settings.windows_dictation_auto_punctuation = self.auto_punctuation.GetValue()
        settings.windows_dictation_remove_fillers = self.remove_fillers.GetValue()
        settings.windows_dictation_continuous = self.continuous.GetValue()
        pause = self.pause.GetSelection()
        if 0 <= pause < len(self._pauses):
            settings.windows_dictation_pause = self._pauses[pause]
        silence = self.silence.GetSelection()
        if 0 <= silence < len(self._silences):
            settings.windows_dictation_silence_minutes = self._silences[silence]
        stop = " ".join(self.stop_phrase.GetValue().split())
        settings.windows_dictation_stop_phrase = (
            stop if stop and not stop_phrase_problem(stop) else DEFAULT_STOP_PHRASE
        )
        for name, value in self._more.items():
            setattr(settings, name, value)
