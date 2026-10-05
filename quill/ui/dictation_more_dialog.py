"""More Dictation Settings: holding the key, the live preview, talking to the
AI, and OpenAI with your own key.

Reached from Dictation Settings (More Dictation Settings..., Alt+A) in both
editors. A window of its own because Dictation Settings is full -- every letter
a screen-reader user can reach with Alt is taken there -- and because these are
the choices nobody needs on the first day:

* **Hold the dictation key to talk** (off by default): when on, hold Ctrl+F11
  and speak, let go to stop; a quick press still turns dictation on and off.
  Off, one press starts dictation and the next stops it.
* **While you speak, the words heard so far**: the live preview of a streaming
  engine (Nemotron, OpenAI) in the status bar and on a braille display, said
  quietly as well, or not at all.
* **Talking to the AI**: the AI Conversation window's own profile -- send at
  the pause or wait for Enter, its own pause length, fillers and punctuation.
* **OpenAI**: whether your speech may be sent (the agreement, which can be
  taken back here), and which of the transcription models your key can use,
  read live from OpenAI when this window opens -- never a list kept in QUILL.
* **My Dictation Instructions...**: the file Tidy Dictated Text follows.

Nothing is applied until OK (:meth:`MoreDictationDialog.values`); Dictation
Settings applies it with its own OK, so Cancel there cancels this too.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.windows_dictation.options import PAUSE_CHOICES, coerce_pause
from quill.core.windows_dictation.preview import PREVIEW_CHOICES, coerce_preview
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["EDIT_INSTRUCTIONS", "EDIT_OPENAI_KEY", "MoreDictationDialog", "SEND_CHOICES"]

#: What My Dictation Instructions... ends both windows with.
EDIT_INSTRUCTIONS = 5803

#: What Add or Change OpenAI Key... ends both windows with: the caller saves
#: these settings, then opens the shared Use My Own AI Key window.
EDIT_OPENAI_KEY = 5804

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
        add_key.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(EDIT_OPENAI_KEY))
        cloud_box.Add(add_key, 0, wx.ALL, _PAD)
        root.Add(cloud_box, 0, wx.EXPAND | wx.ALL, _PAD)

        instructions = wx.Button(self, label="My Dictation &Instructions...")
        instructions.SetHelpText(
            "Opens the file where you tell Tidy Dictated Text how you like your "
            "dictation tidied: write numbers as digits, British spelling, names "
            "always spelled your way. Saves these settings first."
        )
        instructions.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(EDIT_INSTRUCTIONS))
        root.Add(instructions, 0, wx.ALL, _PAD)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(root)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.hold.SetFocus()
        if load_models:
            self._load_models()

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

    def focus_model(self) -> None:
        self.model.SetFocus()

    # -- reading it back --------------------------------------------------------- #

    def values(self) -> dict[str, Any]:
        """Every choice, under the settings' own names."""
        row = self.model.GetSelection()
        model = self._models[row] if 0 <= row < len(self._models) else self._chosen_model
        if row == wx.NOT_FOUND and self._chosen_model not in self._models:
            model = ""  # gone, and not chosen again: say so at the next start
        return {
            "windows_dictation_hold_to_talk": self.hold.GetValue(),
            "windows_dictation_preview": self._previews[max(0, self.preview.GetSelection())],
            "windows_dictation_ai_send": self._sends[max(0, self.send.GetSelection())],
            "windows_dictation_ai_pause": self._pauses[max(0, self.ai_pause.GetSelection())],
            "windows_dictation_ai_remove_fillers": self.ai_fillers.GetValue(),
            "windows_dictation_ai_auto_punctuation": self.ai_punctuation.GetValue(),
            "windows_dictation_openai_consent": self.consent.GetValue(),
            "windows_dictation_openai_model": model,
        }
