"""The two windows the work happens in: the pad, and what came back.

Shared by both editors -- see :mod:`quill.ui.hosted_ai_dialogs` for why these
live in ``quill/ui`` rather than beside QUILL Lite's own modules.

Split from :mod:`quill.ui.hosted_ai_dialogs` under GATE-11, and the seam is a
real one rather than a line count: that module is about the *account* -- getting
connected, and seeing what is left -- while this is about a single request.
They change for different reasons and at different rates.

The shared frame furniture (the labelled read-only field, the button row with
its ``bind_close_button`` Close) is imported from there rather than copied.
Every rule in that module's docstring applies here too: modeless frames, Close
bound by hand because a ``wx.Frame`` does not answer ``ID_CANCEL``, nothing
shown modally from a close handler, and GATE-13 applied one surface at a time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai import gateway_context as ctx
from quill.core.ai.answer_delivery import DELIVERY_LABELS, DELIVERY_MODES, normalise
from quill.core.ai.gateway_catalogue import INPUT_DOCUMENT, INPUT_PROMPT
from quill.core.ai.writing_tools import (
    ACTION_TITLES,
    ACTIONS,
    CONVERSATION,
    DEFAULT_LANGUAGE,
    LANGUAGES,
)
from quill.ui.accessible_names import set_accessible_name
from quill.ui.hosted_ai_dialogs import _PAD, _close_row, _read_only, focus_on, show_problem
from quill.ui.hosted_ai_pad_catalogue import PadRowsMixin

# The result window lives in its own module (GATE-11); exported from here
# because this is where the shared commands and the tests look it up.
from quill.ui.hosted_ai_result import AiResultFrame

__all__ = ["ACTIONS", "AiPadFrame", "AiResultFrame"]

#: What each result window is called. The rows themselves -- seventeen built
#: in, then the service catalogue's extras -- are :mod:`hosted_ai_pad_catalogue`.
_ACTION_TITLES = ACTION_TITLES


# --------------------------------------------------------------------------- #
# The pad
# --------------------------------------------------------------------------- #


class AiPadFrame(PadRowsMixin, wx.Frame):
    """The one surface every AI feature is reached through.

    One window rather than five commands, and the keymap settled that: measured
    across both editors, three chords are free in *both*, and a design needing
    six entry points cannot have them. It is the better shape anyway -- one
    place that shows what will be sent, one that shows what is left, and one
    consent surface instead of five.
    """

    def __init__(
        self,
        parent: wx.Window,
        service: Any,
        *,
        document_text: str,
        selection: str,
        position: int,
        announce: Callable[[str], None],
        on_result: Callable[[str, str, str], None],
        initial_action: str = "",
        on_chat: Callable[[str], None] | None = None,
        delivery: str = "",
        on_delivery: Callable[[str], None] | None = None,
        focus_prompt: bool = False,
    ) -> None:
        super().__init__(parent, title="AI Assistant")
        self._service = service
        self._announce = announce
        self._on_result = on_result
        self._document = document_text
        self._selection = selection
        self._position = position
        self._scope = ""
        self._on_chat = on_chat
        #: ``(feature, prompt, chunks)`` of the request whose answer is showing,
        #: so Follow Up can carry the conversation on from it.
        self.last_request: tuple[str, str, list[str] | None] | None = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        self._panel = panel

        self._summary = _read_only(
            panel,
            sizer,
            "About to send",
            "",
            "How much will be sent, from where, and whether it fits the free limit.",
            grow=False,
        )

        self._preview = _read_only(
            panel,
            sizer,
            "What will be sent",
            "",
            "Exactly the text QUILL will send. Nothing else from your document is sent.",
        )

        self._scopes = ctx.scopes_available(document_text, selection, position)
        self._scope_choice: wx.Choice | None = None
        if len(self._scopes) > 1:
            label = wx.StaticText(panel, label="Send &this much")
            choice = wx.Choice(panel, choices=[ctx.SCOPE_LABELS[s] for s in self._scopes])
            set_accessible_name(choice, "Send this much")
            choice.SetHelpText(
                "Which part of your document to send: what you selected, the "
                "paragraph you are in, or the whole section."
            )
            choice.SetSelection(0)
            choice.Bind(wx.EVT_CHOICE, lambda _e: self._refresh_preview())
            sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
            sizer.Add(choice, 0, wx.EXPAND | wx.ALL, _PAD)
            self._scope_choice = choice

        action_label = wx.StaticText(panel, label="What do you want &done?")
        self._actions = wx.ListBox(panel, choices=self._init_rows())
        set_accessible_name(self._actions, "What do you want done?")
        self._actions.SetHelpText(
            "Choose what the AI should do with the text above. Each choice has "
            "its own description -- press F1 on one to hear it."
        )
        self._actions.Bind(wx.EVT_LISTBOX, lambda _e: self._on_action_changed())
        sizer.Add(action_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._actions, 1, wx.EXPAND | wx.ALL, _PAD)

        self._question_label = wx.StaticText(panel, label="Your &question")
        self._question = wx.TextCtrl(panel)
        set_accessible_name(self._question, "Your question")
        self._question.SetHelpText(
            "What you want to know. For a question about the document, QUILL "
            "finds the parts that answer it and sends only those; for a general "
            "question, only the question is sent."
        )
        sizer.Add(self._question_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._question, 0, wx.EXPAND | wx.ALL, _PAD)

        self._language_label = wx.StaticText(panel, label="Translate &into")
        self._language = wx.Choice(panel, choices=list(LANGUAGES))
        set_accessible_name(self._language, "Translate into")
        self._language.SetHelpText(
            "The language Translate writes in. Only these languages are offered."
        )
        self._language.SetSelection(LANGUAGES.index(DEFAULT_LANGUAGE))
        sizer.Add(self._language_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._language, 0, wx.EXPAND | wx.ALL, _PAD)

        # Where the answer goes (quill/core/ai/answer_delivery.py). Only when
        # the editor can remember the choice; a host with nowhere to keep it
        # always uses the AI Result window.
        self._delivery: wx.Choice | None = None
        if on_delivery is not None:
            label = wx.StaticText(panel, label="Put the &answer in")
            self._delivery = wx.Choice(
                panel, choices=[DELIVERY_LABELS[mode] for mode in DELIVERY_MODES]
            )
            set_accessible_name(self._delivery, "Put the answer in")
            self._delivery.SetHelpText(
                "Where the answer goes when it arrives: the AI Result window, where you "
                "can read it and choose what to do; your document at the cursor, as one "
                "edit Control Z takes back; or the clipboard. Remembered until you change it."
            )
            self._delivery.SetSelection(DELIVERY_MODES.index(normalise(delivery)))
            self._delivery.Bind(
                wx.EVT_CHOICE,
                lambda _e: on_delivery(DELIVERY_MODES[max(0, self._delivery.GetSelection())]),
            )
            sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
            sizer.Add(self._delivery, 0, wx.EXPAND | wx.ALL, _PAD)

        self._send = wx.Button(panel, label="&Send")
        self._send.SetHelpText(
            "Sends the text above and uses one of your free requests. While a request "
            "is on its way this button is Stop, and pressing it stops the request."
        )
        self._working = False
        self._request_cancel: Any = None
        self._send.Bind(wx.EVT_BUTTON, self._on_send)
        _close_row(self, sizer, self._send)

        self._status = _read_only(
            panel,
            sizer,
            "Status",
            "Ready.",
            "What happened to the last request: working, used, or what went wrong.",
            grow=False,
        )

        self._actions.SetSelection(self._row_index(initial_action))
        self._on_action_changed()
        self._refresh_preview()

        self.SetInitialSize((640, 620))
        self.Centre()
        # Focus on the preview: the reader reads it, which is what somebody
        # wants to hear first, and nothing is announced on top (GATE-13). The
        # Chat Key opens on a typed row with the question box focused instead,
        # so the first thing is typing.
        focus_on(self, self._question if focus_prompt and self._asking() else self._preview)

    # -- state ------------------------------------------------------------ #

    def _direct(self) -> bool:
        """Whether requests skip QUILL's service: an own key, or a ChatGPT plan.

        Either way there is no QUILL limit, no excerpt picking, and a warning
        in place of a refusal; the sentences differ and come from the service.
        """
        direct = getattr(self._service, "direct", None)
        if direct is None:  # a service that predates the ChatGPT route
            return bool(getattr(self._service, "own_key_active", False))
        return bool(direct)

    def _route_label(self) -> str:
        return str(getattr(self._service, "route_label", "") or "your own key")

    def _on_action_changed(self) -> None:
        """Show the question field only for the actions that use it.

        Shown, not enabled-and-empty: a control that is present but meaningless
        is a stop on every Tab cycle, forever, for a choice that does not exist.
        """
        # F1 on the list answers for the row you are on: that row's own
        # sentence first, then what the list is for.
        _aid, label, help_text = self._row()
        self._actions.SetHelpText(
            f"{label}: {help_text} Choose what the AI should do with the text above; "
            "each choice has its own description."
        )
        asking = self._asking()
        self._question_label.Show(asking)
        self._question.Show(asking)
        translating = self._action_id == "translate"
        self._language_label.Show(translating)
        self._language.Show(translating)
        self._panel.Layout()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._action_id == CONVERSATION:
            self._preview.SetValue("")
            self._summary.SetValue(
                "Opens a conversation window. Only what you type is sent, with the "
                "conversation so far; nothing from this document. Type a first "
                "message below if you like."
                + (
                    f" With {self._route_label()} the whole conversation goes each time."
                    if self._direct()
                    else " Each message uses one of your free requests."
                )
            )
            return
        if self._input_kind() == INPUT_PROMPT:
            # Nothing from the document: the question is typed below, and it
            # is the whole of what is sent.
            self._preview.SetValue("")
            self._summary.SetValue(
                "About to send only your question, typed below. Nothing from "
                f"this document is sent.{self._direct_note('')}"
            )
            return
        if self._asking() and self._direct():
            # On a direct route there is no excerpt picking: the whole document
            # goes, so no answer is missed for want of a fourth passage.
            self._preview.SetValue(self._document)
            self._summary.SetValue(
                f"About to send the whole document ({ctx.words_in(self._document):,} "
                f"words), and your question.{self._direct_note(self._document)}"
                if self._document.strip()
                else "There is nothing in this document to search."
            )
            return
        if self._asking():
            found = ctx.pick_excerpts(
                self._document,
                self._question.GetValue(),
                limit=self._service.limits.max_chunks_per_request,
            )
            excerpts = found.excerpts
            if not excerpts:
                self._preview.SetValue("")
                self._summary.SetValue("There is nothing in this document to search.")
                return
            words = sum(e.words for e in excerpts)
            body = "\n\n".join(
                f"Excerpt {n}{f', from “{e.heading}”' if e.heading else ''}:\n{e.text}"
                for n, e in enumerate(excerpts, start=1)
            )
            self._preview.SetValue(body)
            self._summary.SetValue(
                f"About to send {len(excerpts)} excerpt"
                f"{'' if len(excerpts) == 1 else 's'} from this document "
                f"(about {words} words), and your question."
                f"{' ' + found.note() if found.note() else ''}"
                f"{self._size_warning(''.join(e.text for e in excerpts))}"
            )
            return

        scope = ""
        if self._scope_choice is not None:
            scope = self._scopes[max(0, self._scope_choice.GetSelection())]
        self._scope, text = ctx.resolve_scope(
            self._document, self._selection, self._position, scope
        )
        self._preview.SetValue(text)
        where = ctx.SCOPE_LABELS.get(self._scope, "your document").lower()
        self._summary.SetValue(
            f"About to send {ctx.words_in(text)} words from {where}.{self._size_warning(text)}"
            if text
            else "There is nothing here to send."
        )

    def _size_warning(self, text: str) -> str:
        """ " Too long" said while it can still be fixed, not after Send.

        The size is refused server-side whatever happens, and the client
        refuses it too -- but a refusal that only arrives on pressing Send is a
        refusal somebody meets after committing to the action. Saying it in the
        summary means the sentence is already there when they arrive on the
        button.

        Worth being plain about one case: a document with a single heading at
        the top makes "this section" the whole document. That is a real choice
        somebody can make, so it is not blocked -- but it is exactly the case
        where the count is startling, and this is what makes it visible before
        the request rather than after.
        """
        if self._direct():
            return self._direct_note(text)
        oversized, words, allowed = ctx.too_large(text, self._input_limit())
        if not oversized:
            return ""
        return (
            f" That is more than the free limit of about {allowed:,} words, so it "
            "will be refused. Select less, or choose a smaller part above. "
            "Nothing is sent and nothing is used."
        )

    def _direct_note(self, text: str) -> str:
        """On a direct route: no limit, so a warning instead of a refusal.

        Empty on the free service. The sentence is the service's, because what
        is worth saying differs: an own key is priced per request and a plan is
        not (``AiService.size_note``).
        """
        if not self._direct():
            return ""
        note = getattr(self._service, "size_note", None)
        if callable(note):
            return " " + str(note(text))
        from quill.core.ai.own_key import size_warning

        free = getattr(self._service, "free_limits", None)
        free_tokens = free.max_input_tokens if free is not None else 1500
        model = str(getattr(self._service, "own_key_model", "") or "your chosen model")
        return " " + size_warning(text, model, free_limit_tokens=free_tokens)

    # -- sending ---------------------------------------------------------- #

    def _on_send(self, _event: wx.CommandEvent) -> None:
        if self._working:  # the button is Stop while a request is on its way
            self._stop()
            return
        reason = self._service.unavailable_reason(self._action_id)
        if reason:
            self._say(reason)
            return

        feature = self._action_id
        if feature == CONVERSATION:
            # Not sent from here: the conversation window does the sending,
            # and the first message goes with it.
            first = self._question.GetValue().strip()
            if self._on_chat is not None:
                self.Close()
                self._on_chat(first)
            return
        chunks: list[str] | None = None
        if self._asking():
            question = self._question.GetValue().strip()
            if not question:
                # Focus goes to the empty field, not to the message: the field
                # is what needs typing into, so the sentence is spoken instead.
                self._status.SetValue("Type a question first.")
                self._announce("Type a question first.")
                self._question.SetFocus()
                return
            prompt = question
            if self._input_kind() == INPUT_DOCUMENT:
                if self._direct():
                    # No excerpt limit on a direct route: the whole document.
                    chunks = [self._document] if self._document.strip() else []
                else:
                    chunks = [
                        e.text
                        for e in ctx.pick_excerpts(
                            self._document,
                            question,
                            limit=self._service.limits.max_chunks_per_request,
                        ).excerpts
                    ]
                if not chunks:
                    self._say("There is nothing in this document to answer from.")
                    return
        else:
            prompt = self._preview.GetValue().strip()
            if not prompt:
                self._say("There is nothing here to send.")
                return

        combined = prompt + "".join(chunks or [])
        # Never refused on size on a direct route: the summary already warned.
        oversized, words, allowed = ctx.too_large(combined, self._input_limit())
        if oversized and not self._direct():
            self._say(
                f"That is about {words} words, and the free limit is about "
                f"{allowed}. Select less, or choose a smaller part above. "
                "Nothing was sent and nothing was used."
            )
            return

        self._working = True
        self._send.SetLabel("&Stop")
        self._status.SetValue("Working...")
        self._announce("Working. Alt+S stops it.")
        self.last_request = (feature, prompt, chunks)
        # Only Translate carries a language, so every other request keeps the
        # call shape it always had.
        extra: dict[str, str] = {}
        if feature == "translate":
            extra["language"] = LANGUAGES[max(0, self._language.GetSelection())]
        self._request_cancel = self._service.ask(
            feature,
            prompt,
            chunks,
            on_done=lambda text, quota: self._done(feature, text, quota),
            on_error=self._failed,
            **extra,
        )

    def _done(self, feature: str, text: str, quota: Any) -> None:
        used = ""
        if quota is not None:
            used = (
                f"Used 1 request. {quota.monthly_cap} left this month, "
                f"{quota.daily_cap} left today."
            )
        if self:
            self._idle()
            self._status.SetValue(used)
        # The result window takes focus, so the reader announces it and reads
        # the answer. Nothing is announced here on top of that.
        self._on_result(feature, text, used)

    def _failed(self, message: str) -> None:
        if not self:
            self._announce(message)
            return
        self._idle()
        show_problem(self, self._status, message, self._announce)

    def _idle(self) -> None:
        self._working = False
        self._request_cancel = None
        self._send.SetLabel("&Send")

    def _stop(self) -> None:
        """Stop: the answer, or the failure, is never shown (qc.md X-07). On an own
        Gemini key the connection closes part way; elsewhere the answer is dropped
        on arrival. Spoken, because the status line is not where focus is."""
        cancel = getattr(self._service, "cancel", None)
        request = self._request_cancel
        stopped = bool(cancel(request)) if callable(cancel) else False
        self._idle()
        message = "Stopped. The answer will not be shown." if stopped else "Nothing to stop."
        self._status.SetValue(message)
        self._announce(message)

    def _say(self, message: str) -> None:
        show_problem(self, self._status, message, self._announce)
