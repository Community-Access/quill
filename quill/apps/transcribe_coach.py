"""QUILL Transcribe's coaching and profiles: Practice Dictation, the recognition
test, the tutorials, and the Dictation Profile window (D-25, D-23).

* **Practice Dictation** (Dictation > Practice Dictation..., Ctrl+Shift+P) is
  :mod:`quill.apps.transcribe_practice`'s window; this mixin starts and stops
  dictation in its field and scores Read This Sentence
  (:func:`quill.core.transcribe.practice.score`).
* **Tutorials** (Help > Tutorials..., Ctrl+Alt+F1) open the family's shared
  Tutorials window over QUILL Transcribe's five lessons. The window asks its
  host for ``commands`` (``get``/``run``) and ``_binding_for``; QUILL
  Transcribe has no command registry, so :class:`_LessonHost` answers from
  :mod:`quill.core.transcribe.tutorials`'s one table.
* **Dictation Profile** (Dictation > Dictation Profile..., Ctrl+Shift+F, and
  the tray) chooses Standard, Email, Document, Markdown, Chat, Coding or
  Verbatim; **Lock Profile** (Ctrl+Shift+L) stops voice switching. The profile
  in use shows in the window's Model and microphone field, the tray's
  read-out and the tray name.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = ["ProfileDialog", "TranscribeCoachMixin"]

_PAD = 8
#: How long after a phrase the test's result is said: after its read-back.
_SCORE_DELAY_MS = 900


class ProfileDialog(wx.Dialog):
    """The seven profiles, what the chosen one does, and Lock Profile."""

    def __init__(self, parent: Any, *, current: str, locked: bool) -> None:
        super().__init__(parent, title="Dictation Profile")
        from quill.core.windows_dictation.profiles import PROFILES, coerce_profile

        self._ids = [profile.id for profile in PROFILES]
        self._descriptions = [profile.description for profile in PROFILES]
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Profiles:")
        self.list = wx.ListBox(self, choices=[profile.name for profile in PROFILES])
        self.list.SetHelpText(
            "The kind of writing dictation is for. Standard is your Dictation Settings "
            "as they are. A profile changes the pause, the filler words and the "
            "punctuation, and how headings, bold and italic are written."
        )
        about_label = wx.StaticText(self, label="&What this profile does:")
        self.about = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.about.SetHelpText("What the profile you are on changes, in one sentence.")
        self.lock = wx.CheckBox(self, label="&Lock the profile so it cannot be switched by voice")
        self.lock.SetHelpText(
            "When this is on, saying QUILL chat mode or another profile's name does "
            "not switch profiles. You can still choose one here."
        )
        self.lock.SetValue(locked)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, wx.ID_OK, "OK")
        ok.SetHelpText("Use the chosen profile from the next phrase on.")
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Keep the profile you have.")
        buttons.Add(ok, 0, wx.RIGHT, _PAD)
        buttons.Add(cancel, 0)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(about_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.about, 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self.lock, 0, wx.ALL, _PAD)
        root.Add(buttons, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((520, 420))
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, cancel, modeless=False)
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._describe())
        self.list.SetSelection(self._ids.index(coerce_profile(current)))
        self._describe()
        self.list.SetFocus()

    def _describe(self) -> None:
        index = self.list.GetSelection()
        if 0 <= index < len(self._descriptions):
            self.about.SetValue(self._descriptions[index])

    def chosen(self) -> str:
        return self._ids[max(0, self.list.GetSelection())]


class _LessonHost:
    """What the shared Tutorials window asks of a host, for QUILL Transcribe."""

    def __init__(self, frame: Any) -> None:
        self._frame = frame
        self._announce = frame._announce
        self._windows = getattr(frame, "_windows", None)
        self.commands = self

    def get(self, command_id: str) -> object | None:
        from quill.core.transcribe.tutorials import method_for

        method = method_for(command_id)
        return getattr(self._frame, method, None) if method else None

    def run(self, command_id: str) -> None:
        command = self.get(command_id)
        if callable(command):
            command()

    def _binding_for(self, command_id: str) -> str:
        from quill.core.transcribe.tutorials import key_for

        return key_for(command_id)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._frame, name)


class TranscribeCoachMixin:
    """On ``QuillTranscribeFrame``: practice, the test, tutorials and profiles."""

    frame: Any
    _settings: Any

    # -- Practice Dictation (D-25) --------------------------------------------- #

    def open_practice(self) -> None:
        """Dictation > Practice Dictation...: open, or bring forward, the window."""
        window = getattr(self, "_practice", None)
        if window is not None and window:
            window.Raise()
            window.field.SetFocus()
            return
        from quill.apps.transcribe_practice import PracticeDictationFrame

        window = PracticeDictationFrame(
            None,
            start_or_stop=self.practice_start_or_stop,
            read_sentence=self.practice_read_sentence,
            score_field=self.practice_score_field,
            next_sentence=self.practice_next_sentence,
        )
        window.Bind(wx.EVT_CLOSE, self._on_practice_close)
        self._practice = window
        self._practice_test = ""
        window.Show()
        window.Raise()
        window.field.SetFocus()

    def _practice_window(self) -> Any:
        window = getattr(self, "_practice", None)
        return window if window is not None and window else None

    def _practicing(self) -> bool:
        """Whether dictation is on and writing into the practice field."""
        from quill.apps.transcribe_practice import PracticeFieldDocument

        controller = getattr(self, "_dictation", None)
        return bool(
            controller is not None
            and controller.active
            and isinstance(controller.document, PracticeFieldDocument)
        )

    def practice_start_or_stop(self) -> None:
        """Start Dictation Here (Ctrl+F11 in the Practice window)."""
        window = self._practice_window()
        if window is None:
            self.open_practice()
            window = self._practice_window()
            if window is None:
                return
        if self._practicing():
            self._controller().finish()  # type: ignore[attr-defined]
            return
        if self.dictation_active():  # type: ignore[attr-defined]
            self._announce(  # type: ignore[attr-defined]
                "Dictation is on in another program. Stop it first, then start it here."
            )
            return
        refusal = self._refusal()  # type: ignore[attr-defined]
        if refusal:
            self._dictation_refused(refusal)  # type: ignore[attr-defined]
            return
        from quill.apps.transcribe_practice import PracticeFieldDocument

        controller = self._controller()  # type: ignore[attr-defined]
        controller.review_retarget(PracticeFieldDocument(window.field))
        window.field.SetFocus()
        controller.start()
        if not controller.active:
            self._leave_practice()

    def _leave_practice(self) -> None:
        """Point the controller back at the locked field, once practice is over."""
        from quill.apps.transcribe_practice import PracticeFieldDocument

        controller = getattr(self, "_dictation", None)
        if controller is None or not isinstance(controller.document, PracticeFieldDocument):
            return
        external = getattr(self, "_dictation_document", None)
        if external is not None:
            controller.review_retarget(external)

    def _practice_state_changed(self) -> None:
        """Every dictation state change: the button's label, and the way back."""
        controller = getattr(self, "_dictation", None)
        if controller is not None and not controller.active:
            self._leave_practice()
            self._practice_test = ""
        window = self._practice_window()
        if window is not None:
            window.set_listening(self._practicing())

    def _on_practice_close(self, event: Any) -> None:
        if self._practicing():
            self._controller().stop("Dictation off.")  # type: ignore[attr-defined]
        self._leave_practice()
        self._practice = None
        self._practice_test = ""
        event.Skip()

    # -- the recognition test --------------------------------------------------- #

    def practice_read_sentence(self) -> None:
        """Read This Sentence: clear the field, then score the first phrase."""
        window = self._practice_window()
        if window is None:
            return
        window.field.ChangeValue("")
        window.result.ChangeValue("")
        self._practice_test = window.sentence.GetValue()
        window.field.SetFocus()
        if not self._practicing():
            self.practice_start_or_stop()
            if not self._practicing():
                self._practice_test = ""
                return
        self._set_status(f"Read aloud: {self._practice_test}")  # type: ignore[attr-defined]

    def practice_score_field(self) -> None:
        """Score the Field: everything in the field against the sentence."""
        window = self._practice_window()
        if window is None:
            return
        self._practice_test = ""
        self._practice_result(window.sentence.GetValue(), window.field.GetValue())

    def practice_next_sentence(self) -> None:
        from quill.core.transcribe.practice import next_sentence

        window = self._practice_window()
        if window is None:
            return
        window.sentence.ChangeValue(next_sentence(window.sentence.GetValue()))
        window.sentence.SetFocus()

    def _practice_phrase_written(self, text: str) -> None:
        """The feedback port's ``phrase_written``: the test's first phrase is in."""
        del text
        sentence = getattr(self, "_practice_test", "")
        window = self._practice_window()
        if not sentence or window is None or not self._practicing():
            return
        self._practice_test = ""
        heard = window.field.GetValue()
        try:
            wx.CallLater(_SCORE_DELAY_MS, self._practice_result, sentence, heard)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            self._practice_result(sentence, heard)

    def _practice_result(self, sentence: str, heard: str) -> None:
        from quill.core.transcribe.practice import score

        outcome = score(sentence, heard).sentence()
        window = self._practice_window()
        if window is not None:
            window.result.ChangeValue(outcome)
        self._announce(outcome, force=True)  # type: ignore[attr-defined]

    # -- tutorials --------------------------------------------------------------- #

    def open_transcribe_tutorials(self) -> None:
        """Help > Tutorials...: the five lessons in the family's window."""
        from quill.ui.transcribe_tutorials import open_tutorials

        open_tutorials(_LessonHost(self))

    # -- profiles (D-23) ------------------------------------------------------------ #

    def dictation_profile_name(self) -> str:
        from quill.core.windows_dictation.profiles import active_profile

        return active_profile(self._dictation_settings_object()).name  # type: ignore[attr-defined]

    def profile_locked(self) -> bool:
        return bool(self._settings.dictation.get("windows_dictation_profile_locked", False))

    def choose_dictation_profile(self) -> None:
        """Dictation > Dictation Profile...: choose one, and Lock Profile."""
        settings = self._dictation_settings_object()  # type: ignore[attr-defined]
        dialog = ProfileDialog(
            self.frame,
            current=settings.windows_dictation_profile,
            locked=self.profile_locked(),
        )
        try:
            if self._show_modal_dialog(dialog, "Dictation Profile") != wx.ID_OK:  # type: ignore[attr-defined]
                return
            chosen, locked = dialog.chosen(), dialog.lock.GetValue()
        finally:
            dialog.Destroy()
        if locked != self.profile_locked():
            self._set_dictation_field("windows_dictation_profile_locked", locked)  # type: ignore[attr-defined]
        self._save_dictation_profile(chosen)
        self._announce(f"{self.dictation_profile_name()} profile.")  # type: ignore[attr-defined]

    def toggle_profile_lock(self) -> None:
        """Dictation > Lock Profile: voice switching off, or on again."""
        locked = not self.profile_locked()
        self._set_dictation_field("windows_dictation_profile_locked", locked)  # type: ignore[attr-defined]
        self._refresh_profile_lock_item()
        self._announce(  # type: ignore[attr-defined]
            "Profile locked." if locked else "Profile unlocked: you can switch it by voice."
        )

    def _refresh_profile_lock_item(self) -> None:
        item_id = getattr(self, "_lock_item_id", None)
        menu_bar = self.frame.GetMenuBar()
        if item_id is None or menu_bar is None:
            return
        item = menu_bar.FindItemById(int(item_id))
        if item is not None:
            item.Check(self.profile_locked())

    def _save_dictation_profile(self, profile_id: str) -> None:
        """Keep the profile (by voice, or from the window), and show it."""
        from quill.core.windows_dictation.profiles import coerce_profile

        # _set_dictation_field saves, and refreshes the window and the tray name.
        self._set_dictation_field("windows_dictation_profile", coerce_profile(profile_id))  # type: ignore[attr-defined]
