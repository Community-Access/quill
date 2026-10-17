"""More Dictation Settings: holding the key, the live preview, talking to the
AI, and OpenAI with your own key.

Reached from Dictation Settings (More Dictation Settings..., Alt+A). Its own
window because every Alt letter is taken there, and nobody needs these on day one:

* **Hold the dictation key to talk** (off by default): hold Ctrl+F11 and speak,
  let go to stop; a quick press still turns dictation on and off.
* **While you speak, the words heard so far**: a streaming engine's live
  preview in the status bar and on braille, said quietly too, or not at all.
* **Tick while a phrase is being worked on** (off in the editors, on in QUILL
  Transcribe; ``quill/core/windows_dictation/working_tick.py``).
* **Allow polishing my dictation with AI**, only where Review Dictation exists:
  without it (Quill Inkwell, ``review=False``) the box is hidden, its value kept.
* **Talking to the AI**: the AI Conversation window's own profile -- send at
  the pause or wait for Enter, its own pause length, fillers and punctuation.
* **OpenAI**: whether your speech may be sent (an agreement taken back here),
  and the models your key can use, read live from OpenAI, never kept in QUILL.
* **My Dictation Instructions...**: the file Tidy Dictated Text follows.
* **Programs Dictation Never Types Into...** (D-24): the never-type list
  (:mod:`quill.ui.dictation_never_type_dialog`), kept until this window's OK.
* **Keep a dictation history** (D-5): off, or one, seven or thirty days of the
  text dictated, sealed for this Windows account; Recent Phrases lists it.
* **Commands** (D-1): the command word ("QUILL"), strict mode and command
  mode's wait (:mod:`quill.core.windows_dictation.command_mode`). OK is refused,
  with the reason, while the command word is a common word or one of My Words.

Nothing is applied until OK (:meth:`MoreDictationDialog.values`); Dictation
Settings applies it with its own OK, so Cancel there cancels this too.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import wx

from quill.core.windows_dictation.anywhere import dictation_fields
from quill.core.windows_dictation.never_type import coerce_never_type
from quill.core.windows_dictation.options import PAUSE_CHOICES, coerce_pause
from quill.core.windows_dictation.preview import PREVIEW_CHOICES, coerce_preview
from quill.core.windows_dictation.settings_fields import SHARE_FIELD, share_on
from quill.ui.dialog_contract import apply_modal_ids

__all__ = [
    "DICTATE_ANYWHERE",
    "EDIT_INSTRUCTIONS",
    "EDIT_OPENAI_KEY",
    "MoreDictationDialog",
    "SEND_CHOICES",
]

#: What My Dictation Instructions... ends both windows with.
EDIT_INSTRUCTIONS = 5803

#: What Add or Change OpenAI Key... ends both windows with: the caller saves
#: these settings, then opens the shared Use My Own AI Key window.
EDIT_OPENAI_KEY = 5804

#: What Dictate in Other Programs... ends both windows with: the caller saves
#: these settings, hands them to Quill Inkwell and starts it (dict.md 3.9).
DICTATE_ANYWHERE = 5805

#: (value, label) for when a dictated message goes to the AI.
SEND_CHOICES: tuple[tuple[str, str], ...] = (
    ("pause", "When I pause"),
    ("enter", "When I press Enter"),
)

_PAD = 8


class MoreDictationDialog(wx.Dialog):
    """The less everyday dictation choices. Read with :meth:`values` after OK."""

    def __init__(
        self,
        parent: Any,
        settings: Any,
        announce: Callable[[str], None] | None = None,
        *,
        pending: dict[str, Any] | None = None,
        load_models: bool = True,
        my_words: Iterable[str] | None = None,
        help_for: dict[str, str] | None = None,
        review: bool = True,
    ) -> None:
        super().__init__(parent, title="More Dictation Settings")
        self._announce = announce or (lambda _text: None)
        saved = dict(pending or {})

        def value(name: str, default: Any) -> Any:
            return saved.get(name, getattr(settings, name, default))

        root = wx.BoxSizer(wx.VERTICAL)

        self.hold = wx.CheckBox(
            self, label="&Hold the dictation key to talk; a quick press still turns it on and off"
        )
        self.hold.SetValue(bool(value("windows_dictation_hold_to_talk", False)))
        self.hold.SetHelpText(
            "Left off, Ctrl+F11 starts dictating with one press and stops with the next. "
            "Turned on, you can also hold Ctrl+F11 while you talk, and dictation stops when "
            "you let go, keeping your last phrase. A quick press still turns it on and off."
        )
        if (help_for or {}).get("hold"):  # QUILL Transcribe's key is its own (D-9)
            self.hold.SetHelpText(str((help_for or {})["hold"]))
        root.Add(self.hold, 0, wx.ALL, _PAD)

        preview_label = wx.StaticText(self, label="While you speak, the &words heard so far:")
        self._previews = [choice for choice, _label in PREVIEW_CHOICES]
        self.preview = wx.Choice(self, choices=[label for _v, label in PREVIEW_CHOICES])
        self.preview.SetSelection(
            self._previews.index(coerce_preview(value("windows_dictation_preview", "show")))
        )
        self.preview.SetHelpText(
            "Nemotron and OpenAI recognise while you are still talking. Show puts the words "
            "heard so far in the status bar and on a braille display, never in your "
            "document, and the final words replace them when you pause. Say also speaks "
            "the new words quietly, a few at a time. The built-in engines wait for the "
            "pause, so with them the status bar says Hearing you."
        )
        root.Add(preview_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.preview, 0, wx.EXPAND | wx.ALL, _PAD)

        self.readback_marks = wx.CheckBox(self, label="&Say punctuation marks in the read-back")
        self.readback_marks.SetValue(bool(value("windows_dictation_readback_marks", True)))
        self.readback_marks.SetHelpText(
            "When each phrase is read back, say its punctuation by name: Hello comma "
            "world period. That way you hear whether the comma or full stop went in, "
            "whatever your screen reader's punctuation level is. The status bar and a "
            "braille display always show the real marks. On by default."
        )
        root.Add(self.readback_marks, 0, wx.ALL, _PAD)

        self.working_tick = wx.CheckBox(self, label="Tick while a phrase is being wo&rked on")
        self.working_tick.SetValue(bool(value("windows_dictation_working_tick", False)))
        self.working_tick.SetHelpText(
            "When a phrase takes more than a second to turn into text after you pause, "
            "play a soft tick every second until it arrives. The first time a phrase "
            "takes four seconds, dictation also says Still working on that phrase. "
            "While a tick plays the microphone is not listened to, as with every QUILL "
            "sound. Off by default in QUILL and QUILL Lite, on in QUILL Transcribe."
        )
        root.Add(self.working_tick, 0, wx.ALL, _PAD)

        self.timestamps = wx.CheckBox(self, label="&Time stamps in live transcripts")
        self.timestamps.SetValue(bool(value("windows_dictation_transcript_timestamps", False)))
        self.timestamps.SetHelpText(
            "In a live transcript, start each new paragraph with the time, like 10:42 "
            "in square brackets, so you can find a moment later. A new paragraph starts "
            "when the speaker pauses for four seconds or more. Off by default."
        )
        root.Add(self.timestamps, 0, wx.ALL, _PAD)

        self.review_first = wx.CheckBox(self, label="Send dictation to re&view first")
        self.review_first.SetValue(bool(value("windows_dictation_review_first", False)))
        self.review_first.SetHelpText(
            "When this is on, what you dictate goes into the Review Dictation window "
            "instead of the document or the other program. Read it, change it, and "
            "press Control Enter to insert it once. Off by default: then say QUILL "
            "review that, or press Review Dictation, when you want a phrase reviewed."
        )
        root.Add(self.review_first, 0, wx.ALL, _PAD)

        # P3: opt-in, never automatic; only where Review Dictation exists (not Inkwell).
        self.polish: wx.CheckBox | None = None
        if review:
            self.polish = wx.CheckBox(
                self, label="Allow polishin&g my dictation with AI when I ask"
            )
            self.polish.SetValue(bool(value("windows_dictation_polish", False)))
            self.polish.SetHelpText(
                "When this is on, saying QUILL polish that, or pressing Polish in Review "
                "Dictation, asks the AI to fix punctuation, capital letters and small slips "
                "in your words, keeping your words. The words open in Review Dictation "
                "first, you are asked once before anything is sent, you hear what changed, "
                "and nothing is inserted until you insert it. Off by default; it needs AI. "
                "Quill Inkwell has no Review Dictation, so it does not show this box."
            )
            root.Add(self.polish, 0, wx.ALL, _PAD)

        self._add_history(root, value)
        # dict.md D-13: one settings store for the family (family_store.py).
        self.share_family = wx.CheckBox(
            self, label="Share dictation settings with every &QuillVille program"
        )
        self.share_family.SetValue(share_on({**dictation_fields(settings), **saved}))
        self.share_family.SetHelpText(
            "When this is on, the dictation settings you save here are used by QUILL, "
            "QUILL Lite, QUILL Transcribe and Quill Inkwell on this computer, and a change "
            "saved in any of them reaches this one the next time it comes to the front. "
            "The keys, the tray, the working tick, strict mode, the read-back's sound and "
            "every permission to send your speech somewhere stay with each program. If two "
            "programs save at once, the last one saved wins; nothing is half written. On "
            "for a new install, off for one whose settings you had already changed, until "
            "you turn it on. The first time a program takes the family's settings, its own "
            "are kept in a backup file, and if the shared copy cannot be saved you are told "
            "why. A portable copy shares only with programs in its own folder."
        )
        root.Add(self.share_family, 0, wx.ALL, _PAD)

        self._my_words = my_words
        self._add_profile(root, value)  # D-23
        self._add_command_word(root, value)

        ai_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Talking to the AI")
        ai = ai_box.GetStaticBox()
        send_label = wx.StaticText(ai, label="Send a dictated message to the AI:")
        self._sends = [choice for choice, _label in SEND_CHOICES]
        self.send = wx.Choice(ai, choices=[label for _v, label in SEND_CHOICES])
        sending = str(value("windows_dictation_ai_send", "pause"))
        self.send.SetSelection(self._sends.index(sending) if sending in self._sends else 0)
        self.send.SetHelpText(
            "In the AI Conversation window, Ctrl+F11 dictates your message. When I pause "
            "sends it as soon as you stop talking, the reply is read aloud, and the "
            "microphone waits until it has been read before it listens again; Escape "
            "listens at once. When I press Enter lets you check the message first."
        )
        ai_pause_label = wx.StaticText(ai, label="&Pause before the message is written:")
        self._pauses = [choice for choice, _label in PAUSE_CHOICES]
        self.ai_pause = wx.Choice(ai, choices=[label for _v, label in PAUSE_CHOICES])
        self.ai_pause.SetSelection(
            self._pauses.index(coerce_pause(value("windows_dictation_ai_pause", "long")))
        )
        self.ai_pause.SetHelpText(
            "How long you can stop to think while talking to the AI before what you said "
            "is written -- and, with When I pause, sent. Long is the default, so a "
            "breath does not send half a question."
        )
        self.ai_fillers = wx.CheckBox(ai, label="Remove &filler words when talking to the AI")
        self.ai_fillers.SetValue(bool(value("windows_dictation_ai_remove_fillers", True)))
        self.ai_fillers.SetHelpText(
            "Leave out um, uh and their kin from what you say to the AI. On by default, "
            "because the AI does not need them."
        )
        self.ai_punctuation = wx.CheckBox(ai, label="Automatic p&unctuation when talking to the AI")
        self.ai_punctuation.SetValue(bool(value("windows_dictation_ai_auto_punctuation", True)))
        self.ai_punctuation.SetHelpText(
            "Let the speech engine put in full stops, commas and question marks in what "
            "you say to the AI."
        )
        ai_box.Add(send_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        ai_box.Add(self.send, 0, wx.EXPAND | wx.ALL, _PAD)
        ai_box.Add(ai_pause_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        ai_box.Add(self.ai_pause, 0, wx.EXPAND | wx.ALL, _PAD)
        ai_box.Add(self.ai_fillers, 0, wx.ALL, _PAD)
        ai_box.Add(self.ai_punctuation, 0, wx.ALL, _PAD)
        root.Add(ai_box, 0, wx.EXPAND | wx.ALL, _PAD)

        cloud_box = wx.StaticBoxSizer(wx.VERTICAL, self, "OpenAI, with your own key")
        cloud = cloud_box.GetStaticBox()
        self.consent = wx.CheckBox(cloud, label="&Let OpenAI dictation send my speech to OpenAI")
        self.consent.SetValue(bool(value("windows_dictation_openai_consent", False)))
        self.consent.SetHelpText(
            "Off unless you agreed when you chose OpenAI as the speech engine. While it "
            "is on and OpenAI is the engine, what you say is sent to OpenAI with the "
            "OpenAI key saved in Use My Own AI Key and billed to your account. Turn it "
            "off to stop that; the built-in engines never send anything."
        )
        model_label = wx.StaticText(cloud, label="OpenAI speech &model:")
        self._chosen_model = str(value("windows_dictation_openai_model", "") or "")
        self._models: list[str] = [self._chosen_model] if self._chosen_model else []
        self.model = wx.Choice(cloud, choices=list(self._models))
        if self._models:
            self.model.SetSelection(0)
        self.model.SetHelpText(
            "The OpenAI transcription models your key can use, read from OpenAI when "
            "this window opens, newest first. Models OpenAI is retiring are left out. "
            "gpt-live-transcribe writes as you speak; gpt-transcribe sends each phrase "
            "when you pause. If the one you chose goes away, you are told and asked to "
            "choose again -- dictation never changes it for you."
        )
        status_label = wx.StaticText(cloud, label="OpenAI's list of models:")
        self.model_status = wx.TextCtrl(cloud, style=wx.TE_READONLY)
        self.model_status.SetHelpText("Whether OpenAI's list of models could be read.")
        cloud_box.Add(self.consent, 0, wx.ALL, _PAD)
        cloud_box.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        cloud_box.Add(self.model, 0, wx.EXPAND | wx.ALL, _PAD)
        cloud_box.Add(status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        cloud_box.Add(self.model_status, 0, wx.EXPAND | wx.ALL, _PAD)
        add_key = wx.Button(cloud, label="Add or Change OpenAI &Key...")
        add_key.SetHelpText(
            "Saves these settings, then opens Use My Own AI Key, where you paste an "
            "OpenAI key or change the one you saved. The key is kept in Windows' "
            "secure store, never in a file. Once it is there, OpenAI appears in the "
            "speech engine list and its models load here."
        )
        add_key.Bind(wx.EVT_BUTTON, lambda _e: self._end_if_ready(EDIT_OPENAI_KEY))
        cloud_box.Add(add_key, 0, wx.ALL, _PAD)
        root.Add(cloud_box, 0, wx.EXPAND | wx.ALL, _PAD)

        instructions = wx.Button(self, label="My Dictation &Instructions...")
        instructions.SetHelpText(
            "Opens the file where you tell Tidy Dictated Text how you like your "
            "dictation tidied: write numbers as digits, British spelling, names "
            "always spelled your way. Saves these settings first."
        )
        instructions.Bind(wx.EVT_BUTTON, lambda _e: self._end_if_ready(EDIT_INSTRUCTIONS))
        anywhere = wx.Button(self, label="Dictate in &Other Programs...")
        anywhere.SetHelpText(
            "Saves these settings, then starts Quill Inkwell with them, so you can "
            "dictate into your browser, your email or any other program on a key you "
            "choose in Inkwell's File menu. Punctuation, spelling and scratch that work "
            "there; selecting and correcting words work only in QUILL's own documents."
        )
        anywhere.Bind(wx.EVT_BUTTON, lambda _e: self._end_if_ready(DICTATE_ANYWHERE))
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(instructions, 0, wx.RIGHT, _PAD)
        row.Add(anywhere, 0)
        root.Add(row, 0, wx.ALL, _PAD)
        self._never_type = coerce_never_type(value("windows_dictation_never_type", None))
        never_type = wx.Button(self, label="Programs Dictation &Never Types Into...")
        never_type.SetHelpText(
            "The programs dictation never types into from QUILL Transcribe or Quill "
            "Inkwell, such as your password manager: add the program you were just "
            "in, add one by its file name, or remove one. Matched by file name, "
            "never by a window title."
        )
        never_type.Bind(wx.EVT_BUTTON, lambda _e: self.edit_never_type())
        root.Add(never_type, 0, wx.ALL, _PAD)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(root)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.hold.SetFocus()
        if load_models:
            self._load_models()

    # -- the dictation profile (D-23) -------------------------------------------- #

    def _add_profile(self, root: Any, value: Callable[[str, Any], Any]) -> None:
        """The named profile, and the lock that stops voice switching."""
        from quill.core.windows_dictation.profiles import (
            DEFAULT_PROFILE,
            coerce_profile,
            profile_labels,
        )

        labels = profile_labels()
        self._profiles = [profile_id for profile_id, _label in labels]
        label = wx.StaticText(self, label="Dict&ation profile, for the kind of writing:")
        self.profile = wx.Choice(self, choices=[text for _id, text in labels])
        self.profile.SetSelection(
            self._profiles.index(
                coerce_profile(value("windows_dictation_profile", DEFAULT_PROFILE))
            )
        )
        self.profile.SetHelpText(
            "A profile changes the pause, the filler words and the punctuation for one kind "
            "of writing, and how headings, bold and italic are written. Standard is your "
            "settings as they are. Markdown writes the marks; Document and Email use QUILL's "
            "own formatting and type nothing for a heading elsewhere; Chat and Verbatim "
            "write plain text. You can also switch by voice: QUILL email mode."
        )
        self.profile_locked = wx.CheckBox(
            self, label="Lock the profile so it cannot be switched &by voice"
        )
        self.profile_locked.SetValue(bool(value("windows_dictation_profile_locked", False)))
        self.profile_locked.SetHelpText(
            "When this is on, saying QUILL chat mode or another profile's name does not "
            "switch profiles, and dictation says the profile stays as it is. You can still "
            "choose a profile here."
        )
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.profile, 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self.profile_locked, 0, wx.ALL, _PAD)

    # -- dictation history (D-5) ------------------------------------------------ #

    def _add_history(self, root: Any, value: Callable[[str, Any], Any]) -> None:
        """How many days of dictated text to keep; off by default."""
        from quill.core.windows_dictation.rescue import HISTORY_CHOICES, coerce_history_days

        label = wx.StaticText(self, label="Keep a dictation histor&y:")
        self._history_days = [days for days, _label in HISTORY_CHOICES]
        self.history = wx.Choice(self, choices=[text for _days, text in HISTORY_CHOICES])
        self.history.SetSelection(
            self._history_days.index(
                coerce_history_days(value("windows_dictation_history_days", 0))
            )
        )
        self.history.SetHelpText(
            "Off by default. Choose one, seven or thirty days to keep the text of what "
            "you dictate on this computer, never the sound, so Recent Phrases can bring "
            "back earlier phrases after the program closes. It is kept for this Windows account "
            "only, and Clear History in Recent Phrases deletes it. Turning it off deletes "
            "it too. Words that were never written are kept until you insert or discard "
            "them, whatever this says."
        )
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.history, 0, wx.EXPAND | wx.ALL, _PAD)

    # -- the command word (D-1) ------------------------------------------------- #

    def _add_command_word(self, root: Any, value: Callable[[str, Any], Any]) -> None:
        """The command word, strict mode and how long command mode lasts."""
        from quill.core.windows_dictation.command_mode import (
            DEFAULT_COMMAND_PREFIX,
            DEFAULT_COMMAND_TIMEOUT,
            MAX_COMMAND_TIMEOUT,
            MIN_COMMAND_TIMEOUT,
            coerce_prefix,
            coerce_timeout,
        )

        box_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Commands")
        box = box_sizer.GetStaticBox()
        prefix_label = wx.StaticText(box, label="&Command word (empty for none):")
        self.command_prefix = wx.TextCtrl(
            box,
            value=coerce_prefix(value("windows_dictation_command_prefix", DEFAULT_COMMAND_PREFIX)),
        )
        self.command_prefix.SetHelpText(
            "Say this word first to give a command instead of dictating: QUILL scratch "
            "that, QUILL select the cat. It counts only as the first word after a pause, "
            "so I told Quill about it is written as words. If what follows is not a "
            "command, nothing is typed, and QUILL type that writes it. Say literal QUILL "
            "to write the word itself. Leave it empty to give commands with the Speak a "
            "Command key only. A common word, or one of your own words in My Words and "
            "Phrases, is refused."
        )
        self.command_required = wx.CheckBox(
            box, label="Commands only after the command word (strict mod&e)"
        )
        self.command_required.SetValue(
            bool(value("windows_dictation_command_prefix_required", False))
        )
        self.command_required.SetHelpText(
            "When this is on, a command said on its own, like scratch that, is written as "
            "words, and only QUILL scratch that is a command. The stop phrase always "
            "works. On by default in QUILL Transcribe, where a command typed into an email "
            "by mistake is hard to take back; off in QUILL and QUILL Lite."
        )
        timeout_label = wx.StaticText(box, label="Seconds command mo&de waits for a command:")
        self.command_timeout = wx.SpinCtrl(
            box,
            min=MIN_COMMAND_TIMEOUT,
            max=MAX_COMMAND_TIMEOUT,
            initial=coerce_timeout(
                value("windows_dictation_command_timeout", DEFAULT_COMMAND_TIMEOUT)
            ),
        )
        self.command_timeout.SetHelpText(
            "Say QUILL command mode, or press Speak a Command twice, and everything you "
            "say is a command until you say dictation mode or give no command for this "
            "many seconds. A falling tone says it has ended. From 5 to 30; 8 by default."
        )
        box_sizer.Add(prefix_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        box_sizer.Add(self.command_prefix, 0, wx.EXPAND | wx.ALL, _PAD)
        box_sizer.Add(self.command_required, 0, wx.ALL, _PAD)
        box_sizer.Add(timeout_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        box_sizer.Add(self.command_timeout, 0, wx.ALL, _PAD)
        root.Add(box_sizer, 0, wx.EXPAND | wx.ALL, _PAD)

    def command_word_problem(self) -> str:
        """Why the command word typed here would not do, or ``""``."""
        from quill.core.windows_dictation.command_mode import command_prefix_problem

        return command_prefix_problem(self.command_prefix.GetValue(), self._words())

    def _words(self) -> list[str]:
        """The person's My Words vocabulary, which the command word may not be."""
        if self._my_words is not None:
            return list(self._my_words)
        try:
            from quill.core.speech.dictation_profile import default_profile_path
            from quill.core.windows_dictation.profile import load

            return list(load(default_profile_path()).vocabulary)
        except Exception:  # noqa: BLE001 - no words is a fine answer
            return []

    def _on_ok(self, event: Any) -> None:
        """OK: refused, with the reason, while the command word would not do."""
        if self._command_word_ready():
            event.Skip()

    def _end_if_ready(self, code: int) -> None:
        """The three buttons that close this window save its values too, so
        they pass the same check as OK: a refused word was saved through them
        until 2026-10-15, and every phrase starting with it typed nothing."""
        if self._command_word_ready():
            self.EndModal(code)

    def _command_word_ready(self) -> bool:
        """True when the command word will do; otherwise say why and go to it."""
        problem = self.command_word_problem()
        if not problem:
            return True
        from quill.ui.dialog_contract import show_message_box

        show_message_box(problem, "More Dictation Settings", wx.OK | wx.ICON_WARNING, self)
        self.command_prefix.SetFocus()
        self.command_prefix.SelectAll()
        return False

    # -- OpenAI's list --------------------------------------------------------- #

    def _load_models(self) -> None:
        """Read the models the key can use, on a worker; never on this thread."""
        from quill.core.windows_dictation.openai_models import cloud_problem, load_key

        problem = cloud_problem()
        if problem:
            self.model_status.SetValue(problem)
            self.model.Disable()
            return
        from quill.core.windows_dictation.openai_models import list_transcription_models
        from quill.ui.update_download import thread_submit

        self.model_status.SetValue("Reading the models your key can use from OpenAI...")
        key = load_key()

        def work(**_kwargs: Any) -> tuple[list[str], str]:
            return list_transcription_models(key)

        def done(_name: str, result: Any) -> None:
            wx.CallAfter(self.show_models, *result)

        def failed(_name: str, _error: BaseException) -> None:
            wx.CallAfter(self.show_models, [], "OpenAI's list of models could not be read.")

        thread_submit("quill-dictation-openai-models", work, on_success=done, on_failure=failed)

    def show_models(self, models: list[str], error: str) -> None:
        """Fill the list; say once if the chosen model is gone."""
        from quill.core.windows_dictation.openai_models import model_problem, newest

        if not self:
            return
        if error:
            self.model_status.SetValue(error)
            return
        problem = model_problem(self._chosen_model, models)
        self._models = list(models)
        self.model.Set(self._models)
        chosen = self._chosen_model if self._chosen_model in models else newest(models)
        self.model.SetSelection(self._models.index(chosen))
        count = len(models)
        sentence = f"OpenAI offers {count} speech model{'s' if count != 1 else ''} for your key."
        if problem:
            sentence = problem
            self.model.SetSelection(wx.NOT_FOUND)
            self._announce(problem)  # said once, here: never a silent switch
        self.model_status.SetValue(sentence)

    def edit_never_type(self) -> None:
        """The never-type list, in its own window; kept here until OK."""
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.dictation_never_type_dialog import NeverTypeDialog

        dialog = NeverTypeDialog(self, self._never_type, self._announce)
        try:
            if show_modal_dialog(dialog, "Programs Dictation Never Types Into") == wx.ID_OK:
                self._never_type = dialog.names()
        finally:
            dialog.Destroy()

    def focus_model(self) -> None:
        self.model.SetFocus()

    # -- reading it back --------------------------------------------------------- #

    def values(self) -> dict[str, Any]:
        """Every choice shown, under the settings' own names (a hidden one is left out)."""
        row = self.model.GetSelection()
        model = self._models[row] if 0 <= row < len(self._models) else self._chosen_model
        if row == wx.NOT_FOUND and self._chosen_model not in self._models:
            model = ""  # gone, and not chosen again: say so at the next start
        chosen: dict[str, Any] = {
            "windows_dictation_hold_to_talk": self.hold.GetValue(),
            "windows_dictation_preview": self._previews[max(0, self.preview.GetSelection())],
            "windows_dictation_ai_send": self._sends[max(0, self.send.GetSelection())],
            "windows_dictation_ai_pause": self._pauses[max(0, self.ai_pause.GetSelection())],
            "windows_dictation_ai_remove_fillers": self.ai_fillers.GetValue(),
            "windows_dictation_ai_auto_punctuation": self.ai_punctuation.GetValue(),
            "windows_dictation_openai_consent": self.consent.GetValue(),
            "windows_dictation_openai_model": model,
            "windows_dictation_readback_marks": self.readback_marks.GetValue(),
            "windows_dictation_transcript_timestamps": self.timestamps.GetValue(),
            "windows_dictation_working_tick": self.working_tick.GetValue(),
            "windows_dictation_never_type": list(self._never_type),
            "windows_dictation_command_prefix": " ".join(self.command_prefix.GetValue().split()),
            "windows_dictation_command_prefix_required": self.command_required.GetValue(),
            "windows_dictation_command_timeout": int(self.command_timeout.GetValue()),
            "windows_dictation_review_first": self.review_first.GetValue(),
            "windows_dictation_profile": self._profiles[max(0, self.profile.GetSelection())],
            "windows_dictation_profile_locked": self.profile_locked.GetValue(),
            "windows_dictation_history_days": self._history_days[
                max(0, self.history.GetSelection())
            ],
            SHARE_FIELD: "on" if self.share_family.GetValue() else "off",
        }
        if self.polish is not None:
            chosen["windows_dictation_polish"] = self.polish.GetValue()
        return chosen
