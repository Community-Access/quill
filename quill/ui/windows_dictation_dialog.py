"""Dictation Settings: the engine, the microphone, and what you hear.

Five questions and nothing else, because dictation has to work well without
anybody opening this window:

* **Which speech engine.** Moonshine (the default), Whisper, or Windows' own
  recogniser -- see :mod:`quill.core.windows_dictation.engines`. The first two
  are built in and punctuate by themselves.
* **Which microphone.** By name, with the Windows default first. The name is
  what is saved, because it is the one thing all three engines can agree on:
  Windows speech knows a microphone by a registry token and the built-in engines
  by a sound-device number, and both of those change when a device is replugged.
* **What happens after each phrase** -- the shared four-way choice from
  :data:`~quill.core.action_feedback.ACTION_FEEDBACK_LABELS`. Speech here means
  the words that went into the document are read back, which is the only way to
  hear whether they were the words you said.
* **Sounds for on, off and errors.**
* **Saying "Dictation on" and "Dictation off".**
* **The finer choices** (:mod:`quill.core.windows_dictation.options`): whether
  the engine punctuates, how long a pause ends a phrase, whether filler words
  are dropped, and when silence stops dictation.
* **Test Microphone**, which records four seconds on the chosen microphone and
  says how loud it was and, with a built-in engine, what it heard. On a worker
  thread; the result goes into a read-only field beside the button and is
  spoken, because a field changing beside the focused button is exactly what a
  screen reader does not announce.

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
from quill.core.windows_dictation.engines import ENGINES, coerce_engine
from quill.core.windows_dictation.options import (
    PAUSE_CHOICES,
    SILENCE_CHOICES,
    coerce_pause,
    coerce_silence,
    level_sentence,
)
from quill.core.windows_dictation.vocabulary import DASH_STYLES
from quill.core.windows_dictation.wake import (
    DEFAULT_STOP_PHRASE,
    DEFAULT_WAKE_PHRASE,
    stop_phrase_problem,
    wake_phrase_problem,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_message_box

__all__ = ["EDIT_WORDS", "SHOW_COMMANDS", "DictationCommandsDialog", "WindowsDictationDialog"]

#: What the two extra buttons end the dialog with. Edit My Words saves the
#: settings first -- a person who changed the engine and then went to add a word
#: should not lose the engine.
SHOW_COMMANDS = 5801
EDIT_WORDS = 5802

_PAD = 8


def _microphone_names() -> list[str]:
    """Every microphone by name: Windows speech's full names, else sounddevice's."""
    names: list[str] = []
    try:
        from quill.platform.windows.sapi_dictation import list_microphones

        names = [microphone.name for microphone in list_microphones()]
    except Exception:  # noqa: BLE001 - try the other list
        names = []
    if not names:
        try:
            from quill.core.windows_dictation.local_recognizer import list_input_names

            names = list_input_names()
        except Exception:  # noqa: BLE001 - an empty list is the honest answer
            names = []
    return names


def _recognizer_names() -> list[str]:
    try:
        from quill.platform.windows.sapi_dictation import list_recognizers

        return list_recognizers()
    except Exception:  # noqa: BLE001 - Windows speech not available here
        return []


def _default_microphone_name() -> str:
    try:
        from quill.platform.windows.sapi_dictation import default_microphone_id, list_microphones

        default_id = default_microphone_id()
        return next((m.name for m in list_microphones() if m.id == default_id), "")
    except Exception:  # noqa: BLE001 - the row simply does not name it
        return ""


class WindowsDictationDialog(wx.Dialog):
    """The dictation settings. Read with :meth:`apply` after OK."""

    def __init__(
        self, parent: Any, settings: Any, announce: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(parent, title="Dictation Settings")
        self._announce = announce or (lambda _text: None)
        # Two columns, so the window fits a 768-pixel-high screen. Tab order is
        # creation order, which runs down the left column and then the right.
        outer = wx.BoxSizer(wx.VERTICAL)
        columns = wx.BoxSizer(wx.HORIZONTAL)
        root = wx.BoxSizer(wx.VERTICAL)  # the left column: what is heard and written

        engine_label = wx.StaticText(self, label="Speech &engine:")
        self._engine_ids = [engine.id for engine in ENGINES]
        self.engine = wx.Choice(self, choices=[engine.label for engine in ENGINES])
        self.engine.SetHelpText(
            "Which speech recogniser dictation uses. "
            + " ".join(f"{engine.label}: {engine.description}" for engine in ENGINES)
        )
        self.engine.SetSelection(
            self._engine_ids.index(coerce_engine(getattr(settings, "windows_dictation_engine", "")))
        )
        root.Add(engine_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.engine, 0, wx.EXPAND | wx.ALL, _PAD)

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
        self._languages = [""] + _recognizer_names()
        self.language = wx.Choice(self, choices=["Windows default"] + self._languages[1:])
        self.language.SetHelpText(
            "Which of the speech languages installed in Windows the Windows speech "
            "recognition engine listens for. Moonshine and Whisper understand "
            "English and ignore this. Add languages in Windows Settings, Time and "
            "language, Speech."
        )
        saved_language = str(getattr(settings, "windows_dictation_language", "") or "")
        self.language.SetSelection(
            self._languages.index(saved_language) if saved_language in self._languages else 0
        )
        root.Add(language_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.language, 0, wx.EXPAND | wx.ALL, _PAD)

        names = _microphone_names()
        self._microphone_names = [""] + names
        default_name = _default_microphone_name()
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
            "you hear Speak now -- then says how loud it was and, with Moonshine "
            "or Whisper, what the engine heard. Nothing is kept."
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
        words = wx.Button(self, label="Edit My Wo&rds and Phrases...")
        words.SetHelpText(
            "Open your own list of words and phrases for dictation in the editor: "
            "names and jargon to spell your way, and phrases of your own that "
            "write whatever you choose. Saves these settings first."
        )
        words.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(EDIT_WORDS))
        more.Add(commands, 0, wx.RIGHT, _PAD)
        more.Add(words, 0)
        root.Add(more, 0, wx.ALL, _PAD)

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

        def work(**_kwargs: Any) -> tuple[float, str]:
            return record_and_hear(microphone, engine)

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


class DictationCommandsDialog(wx.Dialog):
    """Everything dictation understands, as read-only text to arrow through.

    A text field rather than a list or a label, because a screen reader can only
    read *through* text it can put a cursor in; a long label is announced once,
    in one breath, and cannot be reviewed afterwards.
    """

    def __init__(self, parent: Any, body: str) -> None:
        super().__init__(
            parent, title="Dictation Commands", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Commands:")
        self.text = wx.TextCtrl(
            self, value=body, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self.text.SetHelpText(
            "Every phrase dictation acts on and what it does. Read with the arrow "
            "keys; Escape closes. The same list is in the user guide."
        )
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this list.")
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.text, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(close, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((640, 520))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        self.text.SetFocus()
        self.text.SetInsertionPoint(0)
