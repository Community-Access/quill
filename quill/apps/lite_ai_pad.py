"""The two windows the work happens in: the pad, and what came back.

Split from :mod:`quill.apps.lite_ai_dialogs` under GATE-11, and the seam is a
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

from quill.apps.lite_ai_dialogs import _PAD, _close_row, _read_only, focus_on
from quill.core.ai import gateway_context as ctx
from quill.ui.accessible_names import set_accessible_name

__all__ = ["ACTIONS", "AiPadFrame", "AiResultFrame"]

#: The five things the free tier does, in the order the list offers them.
#:
#: The sentence beside each is the control's inline ``SetHelpText``, which is
#: what F1 reads, what the audit checks for, and what
#: ``docs/f1-help-reference.md`` renders. One sentence, written once, reaching
#: three places -- and written to be *heard*, since arriving on a row in a list
#: is how most people will meet it.
ACTIONS: tuple[tuple[str, str, str], ...] = (
    (
        "summarize",
        "Summarize",
        "A few plain sentences saying what this passage says.",
    ),
    (
        "rewrite",
        "Rewrite",
        "The same meaning, clearer and shorter.",
    ),
    (
        "proofread",
        "Proofread",
        "Spelling, grammar and punctuation corrected, wording left alone.",
    ),
    (
        "explain",
        "Explain",
        "What this passage means, in plain language.",
    ),
    (
        "document_qna",
        "Ask a question about the document",
        "Type a question; QuillLite finds the parts of the document that answer "
        "it and sends only those.",
    ),
)

_ACTION_TITLES = {
    "summarize": "Summary",
    "rewrite": "Rewrite",
    "proofread": "Proofread",
    "explain": "Explanation",
    "document_qna": "Answer",
}


# --------------------------------------------------------------------------- #
# The result
# --------------------------------------------------------------------------- #


class AiResultFrame(wx.Frame):
    """What came back, and the four things you can do with it.

    Read-only, because an AI answer is a proposal. Editing happens in the
    document, through the ordinary undo stack, and nothing here changes a
    document without a keystroke saying so -- not on a timer, not on close.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        action: str,
        text: str,
        used: str,
        on_replace: Callable[[str], None] | None,
        on_insert: Callable[[str], None] | None,
        on_again: Callable[[], None] | None,
        announce: Callable[[str], None],
    ) -> None:
        super().__init__(parent, title=_ACTION_TITLES.get(action, "AI Result"))
        self._text = text
        self._announce = announce

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        body = _read_only(
            panel,
            sizer,
            "The answer",
            text,
            "What the AI sent back. Read-only -- use Replace My Selection or "
            "Insert Below to put it into your document.",
        )

        extra: list[wx.Button] = []
        if on_replace is not None:
            replace = wx.Button(panel, label="&Replace My Selection")
            replace.SetHelpText(
                "Puts this in place of the text you had selected. Control Z takes it back."
            )
            replace.Bind(wx.EVT_BUTTON, lambda _e: self._apply(on_replace, "Replaced."))
            extra.append(replace)
        if on_insert is not None:
            insert = wx.Button(panel, label="Insert &Below")
            insert.SetHelpText(
                "Puts this into your document underneath the current paragraph. "
                "Control Z takes it back."
            )
            insert.Bind(wx.EVT_BUTTON, lambda _e: self._apply(on_insert, "Inserted."))
            extra.append(insert)

        copy = wx.Button(panel, label="&Copy")
        copy.SetHelpText("Puts the answer on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, self._on_copy)
        extra.append(copy)

        if on_again is not None:
            again = wx.Button(panel, label="Try &Again")
            again.SetHelpText(
                "Sends the same text again. This uses one more of your free requests."
            )

            def _retry(_event: wx.CommandEvent) -> None:
                self.Close()
                on_again()

            again.Bind(wx.EVT_BUTTON, _retry)
            extra.append(again)

        _close_row(self, sizer, *extra)

        used_label = wx.StaticText(panel, label=used)
        sizer.Add(used_label, 0, wx.ALL, _PAD)

        self.SetInitialSize((620, 460))
        self.Centre()
        # Focus lands on the answer, so the reader reads it. Nothing is
        # announced on top of that (GATE-13): the window title and the focused
        # field are both things it already says.
        focus_on(self, body)

    def _apply(self, action: Callable[[str], None], said: str) -> None:
        action(self._text)
        self._announce(f"{said} Press Control Z to undo.")

    def _on_copy(self, _event: wx.CommandEvent) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied.")


# --------------------------------------------------------------------------- #
# The pad
# --------------------------------------------------------------------------- #


class AiPadFrame(wx.Frame):
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
    ) -> None:
        super().__init__(parent, title="AI Assistant")
        self._service = service
        self._announce = announce
        self._on_result = on_result
        self._document = document_text
        self._selection = selection
        self._position = position
        self._scope = ""

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        self._panel = panel

        self._summary = wx.StaticText(panel, label="")
        sizer.Add(self._summary, 0, wx.ALL, _PAD)

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
        self._actions = wx.ListBox(panel, choices=[label for _id, label, _help in ACTIONS])
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
            "What you want to know about this document. QuillLite finds the "
            "parts that answer it and sends only those."
        )
        sizer.Add(self._question_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._question, 0, wx.EXPAND | wx.ALL, _PAD)

        self._send = wx.Button(panel, label="&Send")
        self._send.SetHelpText("Sends the text above and uses one of your free requests.")
        self._send.Bind(wx.EVT_BUTTON, self._on_send)
        _close_row(self, sizer, self._send)

        self._status = wx.StaticText(panel, label="")
        sizer.Add(self._status, 0, wx.ALL, _PAD)

        index = next((i for i, (aid, _l, _h) in enumerate(ACTIONS) if aid == initial_action), 0)
        self._actions.SetSelection(index)
        self._on_action_changed()
        self._refresh_preview()

        self.SetInitialSize((640, 620))
        self.Centre()
        # Focus on the preview: the reader reads it, which is what somebody
        # wants to hear first, and nothing is announced on top (GATE-13).
        focus_on(self, self._preview)

    # -- state ------------------------------------------------------------ #

    @property
    def _action_id(self) -> str:
        index = max(0, self._actions.GetSelection())
        return ACTIONS[index][0]

    def _asking(self) -> bool:
        return self._action_id == "document_qna"

    def _on_action_changed(self) -> None:
        """Show the question field only for the one action that uses it.

        Shown, not enabled-and-empty: a control that is present but meaningless
        is a stop on every Tab cycle, forever, for a choice that does not exist.
        """
        asking = self._asking()
        self._question_label.Show(asking)
        self._question.Show(asking)
        self._panel.Layout()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._asking():
            found = ctx.pick_excerpts(
                self._document,
                self._question.GetValue(),
                limit=self._service.limits.max_chunks_per_request,
            )
            excerpts = found.excerpts
            if not excerpts:
                self._preview.SetValue("")
                self._summary.SetLabel("There is nothing in this document to search.")
                return
            words = sum(e.words for e in excerpts)
            body = "\n\n".join(
                f"Excerpt {n}{f', from “{e.heading}”' if e.heading else ''}:\n{e.text}"
                for n, e in enumerate(excerpts, start=1)
            )
            self._preview.SetValue(body)
            self._summary.SetLabel(
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
        self._summary.SetLabel(
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
        oversized, words, allowed = ctx.too_large(text, self._service.limits.max_input_tokens)
        if not oversized:
            return ""
        return (
            f" That is more than the free limit of about {allowed:,} words, so it "
            "will be refused. Select less, or choose a smaller part above. "
            "Nothing is sent and nothing is used."
        )

    # -- sending ---------------------------------------------------------- #

    def _on_send(self, _event: wx.CommandEvent) -> None:
        reason = self._service.unavailable_reason(self._action_id)
        if reason:
            self._say(reason)
            return

        feature = self._action_id
        chunks: list[str] | None = None
        if self._asking():
            question = self._question.GetValue().strip()
            if not question:
                self._say("Type a question first.")
                self._question.SetFocus()
                return
            excerpts = ctx.pick_excerpts(
                self._document, question, limit=self._service.limits.max_chunks_per_request
            ).excerpts
            if not excerpts:
                self._say("There is nothing in this document to answer from.")
                return
            chunks = [e.text for e in excerpts]
            prompt = question
        else:
            prompt = self._preview.GetValue().strip()
            if not prompt:
                self._say("There is nothing here to send.")
                return

        combined = prompt + "".join(chunks or [])
        oversized, words, allowed = ctx.too_large(combined, self._service.limits.max_input_tokens)
        if oversized:
            self._say(
                f"That is about {words} words, and the free limit is about "
                f"{allowed}. Select less, or choose a smaller part above. "
                "Nothing was sent and nothing was used."
            )
            return

        self._send.Disable()
        self._status.SetLabel("Working...")
        self._announce("Working.")
        self._service.ask(
            feature,
            prompt,
            chunks,
            on_done=lambda text, quota: self._done(feature, text, quota),
            on_error=self._failed,
        )

    def _done(self, feature: str, text: str, quota: Any) -> None:
        used = ""
        if quota is not None:
            used = (
                f"Used 1 request. {quota.monthly_cap} left this month, "
                f"{quota.daily_cap} left today."
            )
        if self:
            self._send.Enable()
            self._status.SetLabel(used)
        # The result window takes focus, so the reader announces it and reads
        # the answer. Nothing is announced here on top of that.
        self._on_result(feature, text, used)

    def _failed(self, message: str) -> None:
        if self:
            self._send.Enable()
            self._status.SetLabel(message)
        self._announce(message)

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)
