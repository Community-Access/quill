"""The two ChatGPT-subscription commands, shared by QUILL and QUILL Lite.

A base of :class:`quill.ui.hosted_ai_commands.HostedAiMixin` rather than a
second mixin each editor has to remember to add: both editors get these the
moment they get the rest, and the QUILL adapter's "no commands of its own"
test keeps holding, because neither editor writes a line of either.

**Use My ChatGPT Subscription** opens the account window
(:mod:`quill.ui.hosted_ai_chatgpt`). It needs the area switched on and nothing
else: the free service's agreement is about QUILL's servers, which this route
never touches, and the window itself says where the text goes.

**Ask About an Image** is the one AI help command only the plan can answer --
neither the free service nor an own key carries a picture -- so with no
sign-in it says so and opens the account window rather than failing later with
a less useful sentence. The answer arrives in the ordinary result window with
Insert Below and Copy, and nothing goes into the document without one of
those keystrokes.

**Tidy Dictated Text** is the third, and the one dictation asked for: speech
recognition writes what it heard, and what it heard is not always the word
meant. The selection, else the paragraph the cursor is in, goes to the model
with an instruction to fix misheard words, punctuation and fillers and change
nothing else, and the answer arrives with Replace My Selection ready -- one
keystroke to accept, Control Z to take it back. My Dictation Instructions
(``quill.core.windows_dictation.instructions``) go with it when there are
any. It runs only on a direct route (a ChatGPT plan or an own key): the free
service has no such template, and a person who dictates a page at a time
should not spend an allowance on it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.ui.word_tools_commands import WordToolsMixin

__all__ = ["ChatGptAiMixin", "_paragraph_span"]


def _paragraph_span(document: str, position: int) -> tuple[int, int, str]:
    """``(start, end, text)`` of the paragraph around *position*.

    A paragraph is what sits between blank lines, the same idea the AI pad
    uses; the offsets are what Replace My Selection needs to put the tidied
    text back exactly where the dictated text was.
    """
    if not document:
        return 0, 0, ""
    position = max(0, min(position, len(document)))
    before = document.rfind("\n\n", 0, position)
    start = 0 if before < 0 else before + 2
    after = document.find("\n\n", position)
    end = len(document) if after < 0 else after
    text = document[start:end]
    lead = len(text) - len(text.lstrip("\n"))
    trail = len(text) - len(text.rstrip("\n"))
    return start + lead, end - trail, text.strip("\n")


class ChatGptAiMixin(WordToolsMixin):
    """Use My ChatGPT Subscription, Ask About an Image, Tidy Dictated Text --
    and, as a base, the thesaurus and the dictionary (word_tools_commands)."""

    def cmd_ai_chatgpt(self) -> None:
        """Open the ChatGPT account window: sign in, choose the model, sign out."""
        if not self._ai_switched_on():
            return
        from quill.ui.hosted_ai_chatgpt import ChatGptFrame

        service = self._ai_service()
        self._open_ai_window(
            "chatgpt",
            lambda: ChatGptFrame(
                self._ai_parent(),
                service.chatgpt,
                self._announce,
                on_change=self._ai_route_changed,
            ),
        )

    def cmd_ai_image(self) -> None:
        """Choose a picture and a question, and hear what the model sees."""
        if not self._ai_switched_on():
            return
        service = self._ai_service()
        if not self._ai_chatgpt_active() and not bool(getattr(service, "own_key_can_see", False)):
            self._announce(
                "Ask About an Image uses your ChatGPT subscription, or your own Google "
                "Gemini key. Sign in with Use My ChatGPT Subscription, or save a Gemini "
                "key in Use My Own AI Key, first."
            )
            self.cmd_ai_chatgpt()
            return
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.hosted_ai_image import TITLE, AskImageDialog

        dialog = AskImageDialog(self._ai_parent(), announce=self._announce)
        try:
            if show_modal_dialog(dialog, TITLE) != wx.ID_OK:
                return
            path, question = dialog.chosen()
        finally:
            dialog.Destroy()
        self._announce("Working.")
        service.describe_image(
            path,
            question,
            on_done=lambda text: self._show_image_result(text, path),
            on_error=self._announce,
        )

    def cmd_dictation_tidy(self) -> None:
        """Tidy the selection, else the paragraph, as dictated text."""
        if not self._ai_switched_on():
            return
        service = self._ai_service()
        if not self._ai_direct():
            self._announce(
                "Tidy Dictated Text uses your ChatGPT subscription or your own AI key. "
                "Sign in with Use My ChatGPT Subscription, or save a key with Use My "
                "Own AI Key, and try again."
            )
            self.cmd_ai_chatgpt()
            return
        control = self._ai_control()
        document = control.GetValue()
        start, end = control.GetSelection()
        if end > start:
            original = document[start:end]
        else:
            start, end, original = _paragraph_span(document, control.GetInsertionPoint())
        if not original.strip():
            self._announce("There is nothing here to tidy. Select the dictated text first.")
            return
        self._announce("Working.")
        service.ask(
            "tidy_dictation",
            self._with_dictation_instructions(original),
            None,
            on_done=lambda text, _quota: self._show_ai_result(
                "tidy_dictation", text, "", start, end, original, ""
            ),
            on_error=self._announce,
        )

    # -- plumbing -------------------------------------------------------- #

    def _with_dictation_instructions(self, text: str) -> str:
        """*text*, with My Dictation Instructions when there are any (dict.md 5.3 C)."""
        from quill.core.windows_dictation.instructions import instructions_path, read, wrap

        profile = getattr(self, "_dictation_profile_path", None)
        if not callable(profile):
            return text
        context = getattr(self, "_dictation_document_context", None)
        try:
            about = str(context()) if callable(context) else ""
            return wrap(text, read(instructions_path(profile())), about)
        except Exception:  # noqa: BLE001 - instructions are a preference, never a blocker
            return text

    def _ai_direct(self) -> bool:
        """Whether requests skip QUILL's service: a ChatGPT sign-in, or an own key.

        Read through the service's ``direct`` when it has one, and through the
        older ``own_key_active`` otherwise, so a service stand-in that predates
        the ChatGPT route still answers -- there are a dozen in the tests, and
        each one is a place this would otherwise raise.
        """
        service = self._ai_service()
        direct = getattr(service, "direct", None)
        if direct is None:
            return bool(getattr(service, "own_key_active", False))
        return bool(direct)

    def _ai_chatgpt_active(self) -> bool:
        return bool(getattr(self._ai_service(), "chatgpt_active", False))

    def _ai_switched_on(self) -> bool:
        """The area is on. Nothing about the agreement: this route never reaches
        QUILL's servers, so that agreement does not apply."""
        if self._ai_host().feature_enabled("hosted_ai"):
            return True
        self._announce(f"AI help is switched off. Turn it on in {self._ai_switch_route()}.")
        return False

    def _ai_route_changed(self) -> None:
        """A sign-in or sign-out just changed where requests go.

        A hook, empty here: the service reads the account live, so nothing is
        cached that could go stale. An editor that shows the route somewhere --
        a status cell, an About window already open -- overrides this.
        """

    def _show_image_result(self, text: str, path: Path) -> None:
        from quill.core.ai.chatgpt_ai_help import IMAGE_FEATURE
        from quill.ui.hosted_ai_pad import AiResultFrame

        insert: Any = getattr(self, "_insert_below", None)
        frame = AiResultFrame(
            self._ai_parent(),
            action=IMAGE_FEATURE,
            text=text,
            used="",
            on_replace=None,
            on_insert=insert,
            on_again=None,
            announce=self._announce,
        )
        self._show_ai_window(frame)
