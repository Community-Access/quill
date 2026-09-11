"""QUILL's earcons: the moments a screen reader says nothing about.

QUILL declared a hundred and forty-one sound events and **posted forty-five of
them**. The other ninety-six were sounds you could choose, preview and switch
off, and would then never hear -- reported by ear, 2026-09-10: *"are all of them
supported in both quill and quill lite?"* They were not.

The gap was not random. What had earcons were QUILL's own clever features -- the
assistant, the conversation mode, the indent tones. What had none were the
ordinary moments: cut, copy, paste, delete, undo, redo, open, close, print,
start, exit. **For a listener that is exactly backwards.** The clever features
announce themselves in words; the ordinary ones are silent by design, because
nothing is spoken when a paste lands, no focus moves when you cut, and a screen
reader has nothing to read out about an undo. An earcon is the *only* feedback
those moments can carry -- which makes them the ones that most needed sounds and
the last to get them.

Three decisions shape this module.

**One place, not thirty.** Each cue could have been a line at its own call site,
and thirty scattered lines is thirty chances for one of them to be posted twice,
or on the failure path, or before the thing it announces actually happened.
Everything here is either a hook onto an event wx already raises or a one-line
helper the owning method calls, and the roster gate
(``tests/unit/core/test_sound_app_events.py``) reads the whole set back.

**Bound to wx's own events where wx has one.** Cut, copy and paste are stock
commands the text control handles itself -- there is no QUILL method to add a
line to, and the three paths (the accelerator, the Edit menu, the context menu)
would each need their own. ``EVT_TEXT_CUT`` / ``COPY`` / ``PASTE`` fire for all
three, once each, after the edit. One binding, no duplicates, nothing to keep in
step.

**Never in the way.** Every cue here is silent when the pack has no such sound,
when the event is switched off, or when there is no audio stack at all, and none
of them can raise. A cue that could break a paste would be worse than no cue.
"""

from __future__ import annotations

from quill.core.sound_events import SoundEvent

__all__ = ["CueMixin"]


class CueMixin:
    """Post an earcon for the things speech does not cover."""

    # ------------------------------------------------------------------ #
    # The one way in
    # ------------------------------------------------------------------ #

    def cue(self, event: str) -> None:
        """Play *event*'s earcon. Never raises, never blocks, often silent.

        Silent covers three ordinary situations and no errors: the user has
        switched this event off, the active pack has no sound for it, or the
        machine has no audio. All three are answers rather than failures, which
        is why nothing here reports them.
        """
        try:
            from quill.ui.sound_manager import post_sound

            post_sound(str(event))
        except Exception:  # noqa: BLE001 - an earcon must never break the action
            return

    def action(self, event: str, message: str) -> None:
        """Report an action that landed, in whichever channel the user chose.

        The pair of an earcon and a phrase for the *same* moment. Which of them
        happens is ``settings.action_feedback``, resolved in
        :func:`quill.core.action_feedback.resolve` against whether the loaded pack
        has a clip for this event at all -- a mode that asked for a tone and found
        none says the words instead, because the setting chooses between two kinds
        of feedback and never down to none.

        The default is the tone alone, which is what QUILL has always done: a
        setting that changed behaviour for somebody who never opened it would be
        a regression wearing a feature's clothes.
        """
        play, speak = self.action_channels(event)
        if play:
            self.cue(event)
        if speak:
            self._speak_action(message)

    def action_channels(self, event: str) -> tuple[bool, bool]:
        """``(play_sound, speak)`` for *event* under the user's chosen mode.

        Public because a few callers own their own status line and cannot hand
        the phrase over -- QUILL's status bar speaks what it is given, so
        "set the bar but do not say it" is a decision only the caller can make
        (:meth:`_set_status_quiet`). They ask this, then do both halves
        themselves.
        """
        try:
            from quill.core.action_feedback import resolve
            from quill.ui.sound_manager import has_sound_for

            return resolve(
                getattr(getattr(self, "settings", None), "action_feedback", "sound"),
                has_sound=has_sound_for(event),
            )
        except Exception:  # noqa: BLE001 - feedback must never break the action
            return (True, False)

    def _speak_action(self, message: str) -> None:
        """Say *message* through whatever this frame speaks with.

        Looked up rather than assumed: the cue mixin is composed into a frame it
        does not own, and an announcer that is not there must leave the earcon
        working rather than take the command down with it.
        """
        speak = getattr(self, "_announce", None) or getattr(self, "announce", None)
        if callable(speak):
            try:
                speak(message)
            except Exception:  # noqa: BLE001 - as above
                return

    # ------------------------------------------------------------------ #
    # Clipboard: wx's own events, so all three routes are covered at once
    # ------------------------------------------------------------------ #

    def bind_clipboard_cues(self, editor: object) -> None:
        """Hook cut, copy and paste on *editor*.

        ``Skip()`` on every one of them: these events are how the control learns
        it has been asked to cut, so swallowing one would make Ctrl+X stop
        working. The cue rides along; it does not intercept.
        """
        wx = self._wx
        for event, cue in (
            (wx.EVT_TEXT_CUT, SoundEvent.TEXT_CUT),
            (wx.EVT_TEXT_COPY, SoundEvent.TEXT_COPIED),
            (wx.EVT_TEXT_PASTE, SoundEvent.TEXT_PASTED),
        ):
            editor.Bind(event, self._clipboard_cue(cue))

    def _clipboard_cue(self, cue: str):  # type: ignore[no-untyped-def]
        phrase = {
            SoundEvent.TEXT_CUT: "Cut",
            SoundEvent.TEXT_COPIED: "Copied",
            SoundEvent.TEXT_PASTED: "Pasted",
        }.get(cue, "")

        def handler(event: object) -> None:
            self.action(cue, phrase)
            event.Skip()

        return handler

    # ------------------------------------------------------------------ #
    # Named moments, each called by the method that owns it
    # ------------------------------------------------------------------ #

    def cue_undo(self, *, moved: bool) -> None:
        """Undo or redo happened, or there was nothing left to undo.

        The third case gets a cue of its own that does not move in pitch,
        because the undo stack did not move either -- and it is the one of the
        three where something *failed*, which a listener should not have to
        infer from a tone that sounds like the other two.
        """
        if moved:
            self.action(SoundEvent.UNDO_PERFORMED, "Undone")
        else:
            self.cue(SoundEvent.NOTHING_TO_UNDO)

    def cue_redo(self, *, moved: bool) -> None:
        if moved:
            self.action(SoundEvent.REDO_PERFORMED, "Redone")
        else:
            self.cue(SoundEvent.NOTHING_TO_UNDO)

    def cue_message(self, style: int) -> None:
        """The tone that matches a message box's icon.

        Hooked into ``_show_message_box`` rather than into forty call sites,
        which is the only reason all four tones can be trusted to agree with the
        icons: the style flag is already there and already correct.

        A modal is announced by the reader when it takes focus, but *what kind*
        of thing has happened is the part a tone delivers before the title
        finishes -- and the difference between a warning and a question is the
        difference between reading the box and answering it.
        """
        wx = self._wx
        if style & getattr(wx, "ICON_ERROR", 0):
            self.cue(SoundEvent.ERROR)
        elif style & getattr(wx, "ICON_WARNING", 0):
            self.cue(SoundEvent.WARNING)
        elif style & getattr(wx, "ICON_QUESTION", 0):
            self.cue(SoundEvent.QUESTION)
        elif style & getattr(wx, "ICON_INFORMATION", 0):
            self.cue(SoundEvent.INFORMATION)

    def cue_document_opened(self) -> None:
        self.cue(SoundEvent.DOCUMENT_OPENED)

    def cue_document_closed(self) -> None:
        self.cue(SoundEvent.DOCUMENT_CLOSED)

    def cue_app_started(self) -> None:
        """The longest silence in the product: a launch.

        A window appears, the reader announces a title, and until then nothing
        at all says the double-click worked.
        """
        self.cue(SoundEvent.APP_STARTED)

    def cue_app_exiting(self) -> None:
        """The one moment where the sound is the only confirmation left: after
        this the window is gone and the reader has nothing to announce.

        And the one cue that is *waited for*. Everything else here returns
        instantly because it comments on something the user is in the middle of;
        this one is followed by the process ending, so posting it and moving on
        plays half a note and then silence.
        """
        try:
            from quill.ui.sound_manager import post_sound_and_wait

            post_sound_and_wait(SoundEvent.APP_EXITING)
        except Exception:  # noqa: BLE001 - never delay or break an exit
            return

    def cue_task_complete(self) -> None:
        """A background job finished. Distinct from the assistant answering,
        which is the AI family's own arpeggio: a finished job is not an answer."""
        self.cue(SoundEvent.TASK_COMPLETE)

    def cue_structure(self, kind: str) -> None:
        """Entering a table or a list -- structure a sighted reader sees at once.

        The one thing a listener genuinely cannot get from the text: that the
        cursor has crossed into something with a shape. Called only on the
        *transition*, never per row, or a long table becomes a metronome.
        """
        if kind == "table":
            self.cue(SoundEvent.TABLE_ENTERED)
        elif kind == "list":
            self.cue(SoundEvent.LIST_ENTERED)

    def cue_typing_assist(self, kind: str) -> None:
        """The app typed something on your behalf.

        Autocomplete accepted, a snippet inserted, a word autocorrected: three
        moments where text appears that nobody typed, and where a reader says
        nothing because no focus moved and no control was named.
        """
        events = {
            "autocomplete": SoundEvent.AUTOCOMPLETE_ACCEPTED,
            "snippet": SoundEvent.SNIPPET_INSERTED,
            "autocorrect": SoundEvent.WORD_CORRECTED,
        }
        cue = events.get(kind)
        if cue is not None:
            self.cue(cue)

    def cue_printing(self, *, finished: bool) -> None:
        self.cue(SoundEvent.PRINT_COMPLETE if finished else SoundEvent.PRINT_STARTED)

    def cue_dictation(self, kind: str) -> None:
        """Dictation state, and each word as it lands.

        The word cue is the quietest in the pack because it fires once per
        spoken word; anything louder turns dictation into a woodpecker. The
        locked pair is distinct from start/stop because hands-free is a
        different commitment from press-and-hold and sounds like one.
        """
        events = {
            "started": SoundEvent.TRANSCRIPTION_STARTED,
            "stopped": SoundEvent.TRANSCRIPTION_STOPPED,
            "word": SoundEvent.TRANSCRIPTION_WORD_INSERTED,
            "locked_on": SoundEvent.DICTATION_LOCKED_ON,
            "locked_off": SoundEvent.DICTATION_LOCKED_OFF,
        }
        cue = events.get(kind)
        if cue is not None:
            self.cue(cue)

    def cue_conversation(self, kind: str) -> None:
        """Conversation mode: on, woken by name, and still working.

        The other six conversation cues were already posted; these three were
        declared and never fired, so the mode announced its middle and not its
        beginning -- and "still working" is precisely the one a listener needs,
        because a silent assistant and a crashed one sound identical.
        """
        events = {
            "on": SoundEvent.CONVERSATION_ON,
            "wake": SoundEvent.CONVERSATION_WAKE,
            "thinking": SoundEvent.CONVERSATION_THINKING_TICK,
        }
        cue = events.get(kind)
        if cue is not None:
            self.cue(cue)

    def cue_ssh(self, *, connected: bool) -> None:
        """A remote session opening or closing.

        Worth a sound because the thing that changed is *where your keystrokes
        go*, and nothing on screen says so continuously.
        """
        self.cue(SoundEvent.SSH_CONNECTED if connected else SoundEvent.SSH_DISCONNECTED)
