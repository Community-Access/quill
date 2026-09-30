"""Ask QUILL Radio: a conversation about what is on, on the listener's ChatGPT plan.

Quill Radio's own assistant, and deliberately not the editors' AI: there is no
free QUILL service behind it and no API key to paste. It works one way -- the
listener signs in with the ChatGPT subscription they already pay for
(:mod:`quill.core.ai.chatgpt_account`, as the agent "QUILL Radio") -- and then
it knows one thing the general ChatGPT does not: **what is playing**. Every
message goes with the station and the title the stream is announcing
(:mod:`quill.core.radio.assistant_prompt`), so "what is this song" and "tell me
about this station" need no names typed.

Built from the hosted-AI furniture (:mod:`quill.ui.hosted_ai_dialogs`): a
modeless frame, every sentence in a read-only field Tab can reach, Close and
Escape bound by hand, and replies read aloud when they land because the
transcript does not have focus (GATE-13). It is a peer window in Quill Radio's
window model -- registered with the WindowManager, on the Window menu, with the
transport keys -- so the player is still one key away while you ask.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai.hosted_chat import Conversation
from quill.core.radio.assistant_prompt import (
    NEEDS_PLAYING,
    QUICK_QUESTIONS,
    describe_extra,
    instructions_for,
    suggested_questions,
)
from quill.ui.accessible_names import set_accessible_name
from quill.ui.hosted_ai_dialogs import _PAD, _close_row, _read_only, focus_on, show_problem

__all__ = ["AGENT_NAME", "TITLE", "AskRadioFrame"]

TITLE = "Ask QUILL Radio"
#: What OpenAI shows on the consent page and in ChatGPT's settings.
AGENT_NAME = "QUILL Radio"


class AskRadioFrame(wx.Frame):
    """Talk about what is on. Nothing here changes what is playing."""

    def __init__(
        self,
        parent: Any,
        *,
        account: Any,
        announce: Callable[[str], None],
        what_is_on: Callable[[], tuple[str, str]],
        submit: Callable[..., None],
        open_account: Callable[[], None],
        extra_for: Callable[[str], tuple[str, int]] | None = None,
    ) -> None:
        super().__init__(parent, title=TITLE)
        self._account = account
        self._announce = announce
        self._what_is_on = what_is_on
        self._submit = submit
        self._open_account = open_account
        self._extra_for = extra_for or (lambda _needs: ("", 0))
        self._conversation = Conversation()
        self._busy = False
        #: What the chosen quick question attaches; cleared after each send.
        self._extra_needs = NEEDS_PLAYING

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        self._about = _read_only(
            panel,
            sizer,
            "What it knows",
            self._about_text(),
            "What goes with every message: the station and the title playing now, "
            "and that answers come from ChatGPT on your own plan.",
            grow=False,
        )
        self._transcript = _read_only(
            panel,
            sizer,
            "Conversation",
            "",
            "Everything said so far, newest at the end. Read-only -- each reply is "
            "also read aloud as it arrives.",
        )

        quick_label = wx.StaticText(panel, label="&Quick questions")
        self._quick = wx.Choice(
            panel, choices=["Type your own question below"] + [q.label for q in QUICK_QUESTIONS]
        )
        set_accessible_name(self._quick, "Quick questions")
        self._quick.SetSelection(0)
        self._quick.SetHelpText(
            "Questions worth one keystroke. Arrow through them freely; press "
            "Enter, or Use This Question, to put the one you are on into the "
            "message box, where you can send it or change it. Six ask about "
            "what is playing; three also send something you keep -- your "
            "favorites, or the songs logged -- and say so before anything goes."
        )
        # Enter on the list is the choice. Arrowing is not: a selection event
        # fires on every arrow press in a closed wx.Choice, and acting on it
        # took focus away to the message box mid-list (reported 2026-09-29).
        self._quick.Bind(wx.EVT_CHAR_HOOK, self._on_quick_key)
        use = wx.Button(panel, label="Use &This Question")
        use.SetHelpText(
            "Puts the highlighted quick question into the message box and says "
            "what else, if anything, will go with it. Nothing is sent yet."
        )
        use.Bind(wx.EVT_BUTTON, lambda _e: self._use_quick())
        quick_row = wx.BoxSizer(wx.HORIZONTAL)
        quick_row.Add(self._quick, 1, wx.RIGHT, _PAD)
        quick_row.Add(use, 0)
        sizer.Add(quick_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(quick_row, 0, wx.EXPAND | wx.ALL, _PAD)

        label = wx.StaticText(panel, label="Your &message")
        self._message = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self._message, "Your message")
        self._message.SetHelpText(
            "Type a question and press Enter. What is playing goes with it, so "
            "'what is this song' and 'tell me about this station' just work."
        )
        self._message.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._send())
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._message, 0, wx.EXPAND | wx.ALL, _PAD)

        self._send_button = wx.Button(panel, label="&Send")
        self._send_button.SetHelpText("Sends your message with what is playing right now.")
        self._send_button.Bind(wx.EVT_BUTTON, lambda _e: self._send())
        playing = wx.Button(panel, label="Ask About What's &Playing")
        playing.SetHelpText(
            "Asks about the song and station playing right now, without typing. "
            "Press it again for the next suggested question."
        )
        playing.Bind(wx.EVT_BUTTON, lambda _e: self._ask_about_playing())
        fresh = wx.Button(panel, label="&New Conversation")
        fresh.SetHelpText("Forgets this conversation and starts again. Nothing is sent.")
        fresh.Bind(wx.EVT_BUTTON, lambda _e: self._start_over())
        copy = wx.Button(panel, label="Copy &Last Reply")
        copy.SetHelpText("Puts the most recent reply on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, lambda _e: self._copy_last())
        account_button = wx.Button(panel, label="Chat&GPT Account...")
        account_button.SetHelpText(
            "Opens the window where you sign in or out of ChatGPT, choose the "
            "model, and allow web search."
        )
        account_button.Bind(wx.EVT_BUTTON, lambda _e: self._open_account())
        _close_row(self, sizer, self._send_button, playing, fresh, copy, account_button)

        self._status = _read_only(
            panel,
            sizer,
            "Status",
            "Ready.",
            "What happened to the last message: working, answered, or what went wrong.",
            grow=False,
        )
        self._suggestion = 0
        self.SetInitialSize((700, 640))
        self.Centre()
        focus_on(self, self._message)

    # -- what it says -------------------------------------------------------- #

    def _about_text(self) -> str:
        station, now_playing = self._what_is_on()
        if station and now_playing:
            on = f"Playing now: {station}, and the stream says {now_playing}."
        elif station:
            on = f"Playing now: {station}."
        else:
            on = "Nothing is playing right now, so questions are answered without a station."
        web = "Web search is allowed." if self._account.web_search else "Web search is off."
        model = self._account.model or "the model your plan chooses"
        return (
            f"{on} That goes with every message. Answers come from ChatGPT on your "
            f"own plan, using {model}, and count toward your plan's usage. {web} "
            "Nothing here changes what is playing."
        )

    def refresh_context(self) -> None:
        """The station or title changed: say so in the About box, quietly."""
        if self:
            self._about.SetValue(self._about_text())

    # -- sending ---------------------------------------------------------------- #

    def _send(self) -> None:
        if self._busy or not self:
            return
        message = self._message.GetValue().strip()
        if not message:
            self._status.SetValue("Type a message first.")
            self._announce("Type a message first.")
            return
        if not self._account.signed_in:
            show_problem(
                self,
                self._status,
                "QUILL Radio is not signed in with ChatGPT. Choose ChatGPT Account "
                "and Continue with ChatGPT first.",
                self._announce,
            )
            return
        station, now_playing = self._what_is_on()
        extra, _count = self._extra_for(self._extra_needs)
        self._extra_needs = NEEDS_PLAYING
        instructions = instructions_for(
            station, now_playing, web_search=self._account.web_search, extra=extra
        )
        from quill.core.ai.own_key import CONTEXT_WARNING_TOKENS

        history = self._conversation.history_for(message, CONTEXT_WARNING_TOKENS)
        self.refresh_context()
        self._busy = True
        self._send_button.Disable()
        self._status.SetValue("Working...")
        self._announce("Working.")
        account = self._account

        def work(**_kwargs: Any) -> str:
            from quill.core.ai.chatgpt_ai_help import converse_with_chatgpt

            return converse_with_chatgpt(account, message, None, history, instructions=instructions)

        self._submit(
            "radio-ask-quill-radio",
            work,
            on_done=lambda text: self._reply(message, text),
            on_error=self._failed,
        )

    def _reply(self, message: str, text: str) -> None:
        self._busy = False
        if not self:
            self._announce(text)
            return
        self._conversation.add("user", message)
        self._conversation.add("assistant", text)
        self._transcript.SetValue(self._conversation.transcript())
        self._transcript.SetInsertionPointEnd()
        self._message.Clear()
        self._send_button.Enable()
        self._status.SetValue("Answered.")
        # The transcript does not have focus, so the reader will not read the
        # reply on its own: this is the one thing here the app must say.
        self._announce(text)

    def _failed(self, message: str) -> None:
        self._busy = False
        if not self:
            self._announce(message)
            return
        self._send_button.Enable()
        show_problem(self, self._status, message, self._announce)

    # -- quick questions ---------------------------------------------------------- #

    def _on_quick_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._use_quick()
            return
        event.Skip()

    def _use_quick(self) -> None:
        """Put the highlighted question in the box, and say what else it would send.

        Put in the box rather than sent: the person may want to add a word, and
        a question that sends their favorites should be theirs to press Enter
        on. The sentence about what goes with it lands in Status, which does
        not have focus, so it is spoken (GATE-13). Only ever on Enter or the
        button -- never on the list's own selection event, which fires on every
        arrow press.
        """
        row = self._quick.GetSelection() - 1
        if not 0 <= row < len(QUICK_QUESTIONS):
            self._extra_needs = NEEDS_PLAYING
            self._announce("Arrow to a question first, or type your own below.")
            return
        question = QUICK_QUESTIONS[row]
        self._extra_needs = question.needs
        _text, count = self._extra_for(question.needs)
        said = describe_extra(question.needs, count=count)
        self._message.SetValue(question.question)
        self._status.SetValue(said)
        self._announce(f"{said} Press Enter in Your message to send it.")
        self._message.SetFocus()

    # -- the other buttons ------------------------------------------------------- #

    def _ask_about_playing(self) -> None:
        station, now_playing = self._what_is_on()
        questions = suggested_questions(station, now_playing)
        if not questions:
            self._status.SetValue("Nothing is playing, so there is nothing to ask about yet.")
            self._announce("Nothing is playing, so there is nothing to ask about yet.")
            return
        question = questions[self._suggestion % len(questions)]
        self._suggestion += 1
        self._message.SetValue(question)
        self._send()

    def _start_over(self) -> None:
        self._conversation = Conversation()
        self._transcript.SetValue("")
        self._status.SetValue("Ready.")
        self._message.SetFocus()
        self._announce("New conversation.")

    def _copy_last(self) -> None:
        answer = self._conversation.last_answer()
        if not answer:
            self._announce("There is no reply yet.")
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(answer))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied.")
