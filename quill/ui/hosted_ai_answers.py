"""What happens to an AI answer, and three commands that ask for one.

Shared by QUILL and QUILL Lite like everything else in the hosted AI: mixed into
:class:`~quill.ui.hosted_ai_commands.HostedAiMixin`, so both editors' document
windows get it through the same three hooks (``_ai_parent``, ``_ai_control``,
``_ai_host``) and neither has a copy. Split from that module under GATE-11.

**Where an answer goes** (:mod:`quill.core.ai.answer_delivery`): the AI Result
window (the default), straight into the document at the cursor, or onto the
clipboard -- chosen in the AI Assistant window and stored as
``ai_answer_delivery`` in either editor's settings. Only the window offers
Replace and Review Changes, because only there is the answer a proposal you read
first; the other two are for somebody who has already decided.

**Review Changes** is QUILL's word-level review of an AI edit
(:mod:`quill.ui.ai_diff_review_dialog`), offered in the result window whenever
Replace is: the answer against the selection it came from, change by change,
applied as one undo step.

**The commands:**

* :meth:`cmd_ai_chat_key` -- the **Chat Key**: the AI Assistant, opened on Ask a
  General Question with the caret already in the question box. Type, Enter,
  and the answer arrives the way you chose.
* :meth:`cmd_ai_prompt_library` -- QUILL's Prompt Library
  (:mod:`quill.ui.prompt_library_dialog`, :mod:`quill.core.prompt_library`), run
  on the free AI: choose a prompt, and it is sent as a general question with
  your selection filled in.
* :meth:`cmd_ai_web_searches` -- how many of this month's web searches are left
  on the free service (the gateway's ``web_search`` feature).
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["AiAnswersMixin"]

_NOT_CONNECTED = (
    "This computer is not connected to QUILL's free AI. "
    "Choose Connect or Sign Out in the AI menu to connect it."
)


class AiAnswersMixin:
    """Answer delivery, Review Changes, the Chat Key, the Prompt Library and
    the web search count. Expects the HostedAiMixin hooks and plumbing."""

    # ------------------------------------------------------------------ #
    # Where answers go
    # ------------------------------------------------------------------ #

    def _ai_delivery(self) -> str:
        """The stored delivery mode, or the AI Result window."""
        from quill.core.ai.answer_delivery import normalise

        settings = getattr(self._ai_host(), "settings", None)
        return normalise(getattr(settings, "ai_answer_delivery", ""))

    def _ai_delivery_hooks(self) -> dict[str, Any]:
        """What the pad needs to offer the choice: nothing when the host's
        settings have nowhere to keep it, so the pad leaves the chooser out."""
        settings = getattr(self._ai_host(), "settings", None)
        if settings is None or not hasattr(settings, "ai_answer_delivery"):
            return {}
        return {"delivery": self._ai_delivery(), "on_delivery": self._set_ai_delivery}

    def _set_ai_delivery(self, mode: str) -> None:
        """Remember the choice now: it is a preference, and a crash should not lose it."""
        from quill.core.ai.answer_delivery import normalise

        self._ai_host().settings.ai_answer_delivery = normalise(mode)
        self._ai_host().save_settings()

    def _show_ai_result(
        self,
        feature: str,
        text: str,
        used: str,
        start: int,
        end: int,
        original: str,
        action: str,
        request: tuple[str, str, list[str] | None] | None = None,
    ) -> None:
        """Deliver an answer: into the document, onto the clipboard, or -- the
        default -- into an AI Result window with everything it can offer."""
        if self._deliver_elsewhere(text):
            return
        from quill.ui.hosted_ai_chat import follow_up_seed
        from quill.ui.hosted_ai_pad import AiResultFrame

        can_replace = bool(original) and self._selection_unchanged(start, end, original)

        frame = AiResultFrame(
            self._ai_parent(),
            action=feature,
            text=text,
            used=used,
            on_replace=(
                (lambda answer: self._replace_range(start, end, answer)) if can_replace else None
            ),
            on_insert=self._insert_below,
            on_again=lambda: self._open_ai_pad(action=action),
            announce=self._announce,
            on_follow_up=(
                (lambda: self._open_ai_chat(seed=follow_up_seed(request, text)))
                if request is not None
                else None
            ),
            on_review=(
                (lambda answer: self._review_ai_answer(start, end, original, answer))
                if can_replace and text.strip() != original.strip()
                else None
            ),
        )
        self._show_ai_window(frame)

    def _deliver_elsewhere(self, text: str) -> bool:
        """Put *text* at the cursor or on the clipboard when that is the
        choice. Returns whether it did; ``False`` means open the window.

        Spoken either way, because focus does not move and nothing else would
        tell anybody the answer arrived -- the one case GATE-13 says to speak.

        What goes into the document or onto the clipboard is *text* exactly as
        it arrived; only the spoken copy is made speech-safe
        (:mod:`quill.core.ai.spoken_answer`), so Markdown is heard as words.
        """
        from quill.core.ai.answer_delivery import CLIPBOARD, CURSOR
        from quill.core.ai.spoken_answer import speakable_line

        mode = self._ai_delivery()
        if mode == CURSOR:
            control = self._ai_control()
            where = control.GetInsertionPoint()
            replace_as_one_undo(control, where, where, text)
            self._announce(
                f"Answer inserted at the cursor. Press Control Z to undo. {speakable_line(text)}"
            )
            return True
        if mode == CLIPBOARD:
            if not self._ai_copy_to_clipboard(text):
                return False  # the clipboard is busy: the window still has Copy
            self._announce(f"Answer copied to the clipboard. {speakable_line(text)}")
            return True
        return False

    def _ai_copy_to_clipboard(self, text: str) -> bool:
        """Put *text* on the clipboard; ``False`` when another program holds it."""
        if not wx.TheClipboard.Open():
            return False
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()
        return True

    def _review_ai_answer(self, start: int, end: int, original: str, answer: str) -> None:
        """Review Changes: QUILL's word-level review of the answer against the
        selection, applying only what is accepted, as one undo step."""
        if not self._selection_unchanged(start, end, original):
            self._announce(
                "The text this answer came from has changed since, so it cannot be "
                "compared. Nothing was changed."
            )
            return
        from quill.ui.ai_diff_review_dialog import DiffReviewDialog

        DiffReviewDialog(
            self._ai_parent(),
            title="Review AI Changes",
            original_text=original,
            revised_text=answer,
            on_apply=lambda reviewed: self._replace_range(start, end, reviewed),
            announce=self._announce,
        ).show_modal()

    # ------------------------------------------------------------------ #
    # The Chat Key
    # ------------------------------------------------------------------ #

    def cmd_ai_chat_key(self) -> None:
        """The AI Assistant on Ask a General Question, caret in the question box."""
        self._open_ai_pad(action="ask", focus_prompt=True)

    # ------------------------------------------------------------------ #
    # The Prompt Library, on the free AI
    # ------------------------------------------------------------------ #

    def _ai_prompt_library(self) -> Any:
        """The library this editor keeps: ``prompts.json`` in its data folder.

        QUILL overrides this with its own cached library, which also holds the
        prompts its Quillins contribute, so both of QUILL's ways in show one list.
        """
        from quill.core.prompt_fill import PROMPTS_FILE
        from quill.core.prompt_library import PromptLibrary

        return PromptLibrary(self._ai_host().data_dir / PROMPTS_FILE)

    def _ai_document_title(self) -> str:
        """The document's title for a prompt's ``{title}``, or nothing."""
        title = getattr(self, "_current_document_title", None)
        try:
            return str(title()) if callable(title) else ""
        except Exception:  # noqa: BLE001 - a missing title is an empty one
            return ""

    def cmd_ai_prompt_library(self) -> None:
        """Choose a saved prompt and run it on the selection, on the free AI."""
        if not self._ai_ready():
            return
        service = self._ai_service()
        if not self._ai_direct() and not service.signed_in:
            self._announce(_NOT_CONNECTED)
            self.cmd_ai_sign_in()
            return
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.prompt_library_dialog import PromptLibraryDialog

        control = self._ai_control()
        start, end = control.GetSelection()
        document = control.GetValue()
        selection = document[start:end] if end > start else ""
        dialog = PromptLibraryDialog(
            self._ai_parent(),
            self._ai_prompt_library(),
            self._ai_host().settings,
            selection=selection,
            document=document,
            title=self._ai_document_title(),
            announce_cb=self._announce,
            hosted=True,
        )
        try:
            # Only Run sets ``chosen``; Close and Escape leave it None.
            show_modal_dialog(dialog.dialog, "Prompt Library")
            chosen = dialog.chosen
        finally:
            dialog.close()
        if chosen is not None:
            self._run_library_prompt(chosen[1], start, end, selection)

    def _run_library_prompt(self, text: str, start: int, end: int, selection: str) -> None:
        """Send a filled prompt as a general question, and deliver the answer."""
        from quill.core.ai import gateway_context as ctx

        service = self._ai_service()
        reason = service.unavailable_reason("ask")
        if reason:
            self._announce(reason)
            return
        oversized, words, allowed = ctx.too_large(text, int(service.limits.max_input_tokens))
        if oversized and not self._ai_direct():
            self._announce(
                f"That prompt is about {words} words with your text in it, and the free "
                f"limit is about {allowed}. Select less and run it again. Nothing was "
                "sent and nothing was used."
            )
            return
        self._announce("Working.")
        request = ("ask", text, None)
        service.ask(
            "ask",
            text,
            None,
            on_done=lambda answer, quota: self._show_ai_result(
                "ask", answer, _used(quota), start, end, selection, "ask", request
            ),
            on_error=self._announce,
        )

    # ------------------------------------------------------------------ #
    # Web searches left
    # ------------------------------------------------------------------ #

    def cmd_ai_web_searches(self) -> None:
        """Say how many of this month's web searches are left on the free AI."""
        if not self._ai_host().feature_enabled("hosted_ai"):
            self._announce(f"AI help is switched off. Turn it on in {self._ai_switch_route()}.")
            return
        if self._ai_direct():
            self._announce(
                "Web search is part of QUILL's free AI. With your own key or ChatGPT "
                "plan it is not offered."
            )
            return
        service = self._ai_service()
        if not service.signed_in:
            self._announce(_NOT_CONNECTED)
            return
        from quill.core.ai.gateway_quota_text import describe_web_searches

        service.fetch_web_searches(
            on_done=lambda enabled, quota: self._announce(describe_web_searches(enabled, quota)),
            on_error=lambda message: self._announce(
                f"Web searches could not be checked just now. {message}"
            ),
        )


def _used(quota: Any) -> str:
    """The Requests line of a result window, as the pad words it."""
    if quota is None:
        return ""
    return f"Used 1 request. {quota.monthly_cap} left this month, {quota.daily_cap} left today."
