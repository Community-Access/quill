"""The conversation window: talk back and forth with AI help.

Shared by both editors, like the pad (:mod:`quill.ui.hosted_ai_pad`), and built
from the same furniture (:mod:`quill.ui.hosted_ai_dialogs`): a modeless frame,
Close bound by hand, every sentence in a read-only field Tab can reach.

**Where focus lives.** In the message box, the whole time. Type, press Enter,
and keep typing: the reply is read aloud when it arrives, because it lands in
the transcript, which does not have focus -- the one case GATE-13 says the app
must speak. The transcript is one Shift+Tab away for reading it again, word by
word, and the last reply can be copied or put into the document from here.

**What it costs, said once and plainly.** On QUILL's free AI every message is
one request, and the conversation so far goes with it only as far as it fits
the ordinary size limit (:mod:`quill.core.ai.hosted_chat`). When the oldest
part of a conversation stops being sent, the window says so -- once, when it
first happens -- rather than leaving somebody to work out why the AI forgot
what they told it ten minutes ago. With the user's own API key there is no
such limit, and it says that instead.

Nothing here edits the document without a button press, and that edit goes
through the ordinary undo stack like every other AI edit.

**Talking to it** (dict.md 3.2): Ctrl+F11 in the message box dictates there,
with dictation's **Talking to AI** profile -- its own pause, fillers and
punctuation -- and by default the message is sent at the pause, the reply is
read aloud as always, and the microphone is muted while it is read, so the
reply is not heard as the next message. Dictation Settings can make it wait
for Enter instead.

**Saved conversations** (2026-10-15): every exchange is saved on this computer
the way QUILL's Ask Quill has always saved its own -- a writing session in the
app's ``ai-sessions`` folder, through the one recorder both use
(:func:`quill.core.ai.sessions.record_exchange`). **Saved Conversations** lists
them (:mod:`quill.ui.hosted_ai_saved_chats`) and opens one here to carry on.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.ai.hosted_chat import Conversation
from quill.ui.accessible_names import set_accessible_name
from quill.ui.hosted_ai_dialogs import _PAD, _close_row, _read_only, focus_on, show_problem

__all__ = ["AiChatFrame", "follow_up_seed", "open_for"]


class AiChatFrame(wx.Frame):
    """A conversation with AI help."""

    def __init__(
        self,
        parent: wx.Window,
        service: Any,
        *,
        announce: Callable[[str], None],
        on_insert: Callable[[str], None] | None = None,
        conversation: Conversation | None = None,
        first_message: str = "",
        store: Path | None = None,
    ) -> None:
        super().__init__(parent, title="AI Conversation")
        #: Told each reply as it is read aloud: dictation mutes its microphone.
        self.on_reply: Callable[[str], None] | None = None
        self._service = service
        self._announce = announce
        self._on_insert = on_insert
        self._conversation = conversation or Conversation()
        self._told_set_aside = False
        self._busy = False
        #: Where exchanges are saved (an ``ai-sessions`` folder), or None.
        self._store = store
        #: The saved session this conversation is being written to.
        self._session: Any = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        self._about = _read_only(
            panel,
            sizer,
            "About this conversation",
            self._about_text(),
            "What is sent with each message, and what it uses.",
            grow=False,
        )

        self._transcript = _read_only(
            panel,
            sizer,
            "Conversation",
            self._conversation.transcript(),
            "Everything said so far, newest at the end. Read-only -- each reply is "
            "also read aloud as it arrives.",
        )

        label = wx.StaticText(panel, label="Your &message")
        self._message = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self._message, "Your message")
        self._message.SetHelpText(
            "Type what you want to say and press Enter to send it. The reply is "
            "read aloud and added to the conversation above."
        )
        self._message.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._send())
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._message, 0, wx.EXPAND | wx.ALL, _PAD)

        self._send_button = wx.Button(panel, label="&Send")
        self._send_button.SetHelpText(
            "Sends your message, with as much of the conversation so far as fits."
        )
        self._send_button.Bind(wx.EVT_BUTTON, lambda _e: self._send())

        fresh = wx.Button(panel, label="&New Conversation")
        fresh.SetHelpText("Forgets this conversation and starts again. Nothing is sent.")
        fresh.Bind(wx.EVT_BUTTON, lambda _e: self._start_over())

        copy = wx.Button(panel, label="Copy &Last Reply")
        copy.SetHelpText("Puts the most recent reply on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, lambda _e: self._copy_last())

        extra = [self._send_button, fresh, copy]
        if store is not None:
            saved = wx.Button(panel, label="Saved Con&versations...")
            saved.SetHelpText(
                "Lists the conversations saved on this computer, newest first, so you "
                "can open one and carry on, or delete one."
            )
            saved.Bind(wx.EVT_BUTTON, lambda _e: self._open_saved())
            extra.append(saved)
        if on_insert is not None:
            insert = wx.Button(panel, label="&Insert Last Reply Below")
            insert.SetHelpText(
                "Puts the most recent reply into your document underneath the "
                "current paragraph. Control Z takes it back."
            )
            insert.Bind(wx.EVT_BUTTON, lambda _e: self._insert_last())
            extra.append(insert)
        _close_row(self, sizer, *extra)

        self._status = _read_only(
            panel,
            sizer,
            "Status",
            "Ready.",
            "What happened to the last message: working, used, or what went wrong.",
            grow=False,
        )

        self.SetInitialSize((680, 640))
        self.Centre()
        focus_on(self, self._message)
        if first_message.strip():
            self._message.SetValue(first_message)
            # Sent once the window is on screen, so the reader has arrived in
            # it before the reply is read out.
            wx.CallAfter(self._send)

    # -- what the window says ---------------------------------------------- #

    def _direct(self) -> bool:
        """Whether this conversation skips QUILL's service: an own key, or a ChatGPT plan."""
        direct = getattr(self._service, "direct", None)
        if direct is None:  # a service that predates the ChatGPT route
            return bool(getattr(self._service, "own_key_active", False))
        return bool(direct)

    def _about_text(self) -> str:
        excerpts = (
            " Excerpts from your document go with every message, as they did with your question."
            if self._conversation.excerpts
            else " Nothing from your document is sent."
        )
        if self._store is not None:
            excerpts += (
                " The conversation is saved on this computer as it goes; Saved "
                "Conversations opens it again."
            )
        note = getattr(self._service, "conversation_note", None)
        if callable(note):
            return str(note()) + excerpts
        if self._direct():
            return (
                "This conversation uses your own API key: no limits, billed to "
                "your own account. The whole conversation goes with each message, "
                "so a long one costs more per reply." + excerpts
            )
        return (
            "Each message uses one of your free requests. The conversation so far "
            "goes with it as far as the free size limit allows, so a long "
            "conversation gradually forgets its beginning; this window says when "
            "that starts." + excerpts
        )

    # -- sending ------------------------------------------------------------ #

    def _send(self) -> None:
        if self._busy or not self:
            return
        message = self._message.GetValue().strip()
        if not message:
            self._status.SetValue("Type a message first.")
            self._announce("Type a message first.")
            return
        reason = self._service.unavailable_reason("chat")
        if reason:
            show_problem(self, self._status, reason, self._announce)
            return
        limit = self._ceiling()
        if not self._conversation.fits(message, limit):
            show_problem(
                self,
                self._status,
                "That message is more than the free limit accepts on its own. "
                "Shorten it, or send it in parts. Nothing was sent and nothing was used.",
                self._announce,
            )
            return
        history = self._conversation.history_for(message, limit)
        self._busy = True
        self._send_button.Disable()
        self._status.SetValue("Working...")
        self._announce("Working.")
        self._service.converse(
            message,
            list(self._conversation.excerpts),
            history,
            on_done=lambda text, quota, dropped: self._reply(message, text, quota, dropped),
            on_error=self._failed,
        )

    def _ceiling(self) -> int:
        if self._direct():
            from quill.core.ai.own_key import CONTEXT_WARNING_TOKENS

            return CONTEXT_WARNING_TOKENS
        return int(self._service.limits.max_input_tokens)

    def _reply(self, message: str, text: str, quota: Any, dropped: int) -> None:
        from quill.core.ai.spoken_answer import speakable_line

        self._busy = False
        if not self:
            # Closed while the reply was on its way: still say it, once.
            self._announce(speakable_line(text))
            return
        self._conversation.add("user", message)
        self._conversation.add("assistant", text)
        self._save_exchange(message, text)
        self._conversation.set_aside += max(0, int(dropped or 0))
        self._transcript.SetValue(self._conversation.transcript())
        self._transcript.SetInsertionPointEnd()
        # Only what was sent goes: anything said or typed while waiting stays.
        current = self._message.GetValue().strip()
        if current.startswith(message):
            self._message.SetValue(current[len(message) :].strip())
        self._message.SetInsertionPointEnd()
        self._send_button.Enable()
        used = "Ready."
        if quota is not None:
            used = (
                f"Used 1 request. {quota.monthly_cap} left this month, "
                f"{quota.daily_cap} left today."
            )
        self._status.SetValue(used)
        # The transcript keeps the reply as it came; the listener hears words,
        # not Markdown symbols (quill/core/ai/spoken_answer.py).
        spoken = speakable_line(text)
        if self._conversation.set_aside and not self._told_set_aside:
            self._told_set_aside = True
            spoken += " " + self._set_aside_sentence()
        # The transcript does not have focus, so the reader will not read the
        # reply on its own: this is the one thing here the app must say.
        if self.on_reply is not None:
            self.on_reply(spoken)
        self._announce(spoken)

    @property
    def message_box(self) -> wx.TextCtrl:
        """Where a message is written -- and dictated (Ctrl+F11)."""
        return self._message

    def send_dictated(self) -> None:
        """Dictation wrote a phrase and paused: send it (Talking to AI)."""
        if self._message.GetValue().strip():
            self._send()

    def _set_aside_sentence(self) -> str:
        if self._direct():
            return (
                "This conversation is now longer than the model can read at once, "
                "so its beginning is no longer sent."
            )
        return (
            "The beginning of this conversation is no longer sent, to stay within "
            "the free limit. New Conversation starts fresh."
        )

    def _failed(self, message: str) -> None:
        self._busy = False
        if not self:
            self._announce(message)
            return
        self._send_button.Enable()
        show_problem(self, self._status, message, self._announce)

    # -- the other buttons -------------------------------------------------- #

    def _save_exchange(self, message: str, text: str) -> None:
        """Save this exchange (the store Ask Quill uses). Never fails the reply."""
        if self._store is None:
            return
        from quill.core.ai.sessions import record_exchange

        try:
            if self._session is None:
                # A Follow Up starts with the question and answer it came
                # from: they open the saved conversation too.
                earlier = self._conversation.turns[:-2]
                for asked, answered in zip(earlier[::2], earlier[1::2], strict=False):
                    self._session = record_exchange(
                        self._session, asked.text, answered.text, directory=self._store
                    )
            self._session = record_exchange(self._session, message, text, directory=self._store)
        except Exception:  # noqa: BLE001 - a disk that will not write costs the copy only
            pass

    def _open_saved(self) -> None:
        """Saved Conversations: choose one, and carry on with it here."""
        if self._store is None or self._busy:
            return
        from quill.ui.hosted_ai_saved_chats import choose_saved_conversation

        session = choose_saved_conversation(self, self._store, self._announce)
        if session is not None:
            self.load_session(session)

    def load_session(self, session: Any) -> None:
        """Show a saved conversation here; new messages are added to it.

        Only the branch it was last on, which is the conversation as it was
        last read. Said aloud, because the transcript changing is not where
        focus is.
        """
        from quill.core.ai.sessions import current_path

        conversation = Conversation()
        for turn in current_path(session):
            if turn.role in ("user", "assistant") and turn.text.strip():
                conversation.add(turn.role, turn.text)
        self._conversation = conversation
        self._session = session
        self._told_set_aside = False
        self._transcript.SetValue(conversation.transcript())
        self._transcript.SetInsertionPointEnd()
        self._about.SetValue(self._about_text())
        self._status.SetValue("Ready.")
        self._message.SetFocus()
        count = len(conversation.turns)
        self._announce(
            f"Opened {session.title}, {count} message{'' if count == 1 else 's'}. "
            "Your next message carries it on."
        )

    def _start_over(self) -> None:
        self._conversation = Conversation()
        self._session = None
        self._told_set_aside = False
        self._transcript.SetValue("")
        self._about.SetValue(self._about_text())
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

    def _insert_last(self) -> None:
        answer = self._conversation.last_answer()
        if not answer:
            self._announce("There is no reply yet.")
            return
        if self._on_insert is not None:
            self._on_insert(answer)
            self._announce("Inserted. Press Control Z to undo.")


# --------------------------------------------------------------------------- #
# Opening one -- the editors' half, kept here so HostedAiMixin stays one line
# --------------------------------------------------------------------------- #


def open_for(host: Any, *, first_message: str = "", seed: Conversation | None = None) -> None:
    """Open the AI Conversation window from either editor's HostedAiMixin.

    Reached from the pad's **Have a conversation** row and from **Follow Up**
    in a result window -- no command and no chord of its own, because the
    chords free in both editors are too few to spend on a second door to the
    same place. The same readiness rules as the pad: the agreement, and a
    connection or an own key.
    """
    if not host._ai_ready():
        return
    service = host._ai_service()
    if not _direct_service(service) and not service.signed_in:
        host._announce(
            "This computer is not connected to QUILL's free AI. "
            "Choose Connect or Sign Out in the AI menu to connect it."
        )
        host.cmd_ai_sign_in()
        return
    service.refresh_limits()
    frame = AiChatFrame(
        host._ai_parent(),
        service,
        announce=host._announce,
        on_insert=host._insert_below,
        conversation=seed,
        first_message=first_message,
        store=_conversation_store(host),
    )
    _talk_to_it(frame, host)
    host._after_agreement(lambda: host._show_ai_window(frame))


def _conversation_store(host: Any) -> Path | None:
    """The editor's ``ai-sessions`` folder: QUILL's is the one Ask Quill writes."""
    from quill.core.ai.sessions import SESSIONS_FOLDER

    data_dir = getattr(host._ai_host(), "data_dir", None)
    return Path(data_dir) / SESSIONS_FOLDER if data_dir else None


def _talk_to_it(frame: AiChatFrame, host: Any) -> None:
    """Dictation in the message box, on the Talking to AI profile (dict.md 3.2)."""
    if not callable(getattr(host, "cmd_dictation_into", None)):
        return
    from quill.ui.windows_dictation_tools import bind_field_dictation

    box = frame.message_box
    box._quill_dictation_profile = "ai"  # type: ignore[attr-defined]
    box._quill_dictation_after_phrase = frame.send_dictated  # type: ignore[attr-defined]
    bind_field_dictation(frame, [box], host)
    mute = getattr(host, "_dictation_mute_for_reply", None)
    if callable(mute):
        frame.on_reply = lambda text: mute(text, box)


def _direct_service(service: Any) -> bool:
    """Whether *service* skips QUILL's service, read either way it can say so."""
    direct = getattr(service, "direct", None)
    if direct is None:
        return bool(getattr(service, "own_key_active", False))
    return bool(direct)


def follow_up_seed(request: tuple[str, str, list[str] | None], answer: str) -> Conversation:
    """A conversation that starts where an answer left off.

    The first turn says what was asked in words the model reads as a request
    ("Summarize this: ..."), the second is the answer. A question about the
    document keeps its excerpts attached, so the follow-ups can keep asking
    about the same passages.
    """
    from quill.core.ai.writing_tools import label_for

    feature, prompt, chunks = request
    conversation = Conversation()
    if feature == "document_qna":
        conversation.excerpts = list(chunks or [])
        asked = prompt
    elif feature == "ask":
        asked = prompt
    else:
        asked = f"{label_for(feature)} this:\n\n{prompt}"
    conversation.add("user", asked)
    conversation.add("assistant", answer)
    return conversation
