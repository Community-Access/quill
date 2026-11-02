"""Review Dictation in QUILL and QUILL Lite: the editors' half of D-2.

One command, **Review Dictation** (Shift+F4 in both editors, rule 2:
free in both; keymap.py says why that key), and the hooks the shared review
window (:mod:`quill.ui.dictation_review_frame`) asks of its host. Inherited by
:class:`~quill.ui.windows_dictation_commands.WindowsDictationMixin`, so QUILL's
adapter adds no command and QUILL Lite is never ahead of QUILL.

* **Opening.** The key takes the last phrase back out of the document (or the
  words held while paused) and opens them for review; with nothing to take, an
  empty review, or the words kept from a review that did not finish. "QUILL
  review that" does the same by voice (:mod:`quill.core.windows_dictation.review_mixin`).
  While the review is open, dictation writes into its text, not the document.
* **The AI** is the editor's own AI help (:class:`ServiceReviewAi` over
  ``HostedAiMixin._ai_service()``), on a direct route only -- a ChatGPT
  subscription or an own key, as Tidy Dictated Text -- so a review never spends
  the free service's allowance. Off when AI help is switched off, in Safe Mode,
  or with no direct route; the window then edits and inserts without it.
* **Insert** is one undo step at the place the words came from
  (:func:`~quill.ui.atomic_edit.replace_as_one_undo`), and the words as said and
  as inserted both go to Recent Phrases.

QUILL Transcribe uses the same window and :class:`ServiceReviewAi` through
:mod:`quill.apps.transcribe_review`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.windows_dictation.review_session import CONSENT_VERSION, REVIEW_FEATURE

__all__ = ["DictationReviewMixin", "ServiceReviewAi", "review_desk", "review_open"]

#: The one review desk in this app, and the editor window it belongs to.
_desk: Any = None
_rescue_told = False

NO_DIRECT_ROUTE = (
    "Changing your words with AI needs your ChatGPT subscription or your own AI key, "
    "set up from the AI menu. You can still edit them here, then insert."
)
SAFE_MODE = "Safe Mode is on, so the AI is not used. You can still edit your words, then insert."
RESCUE_NOTICE = (
    "A dictation review did not finish last time. Review Dictation, in the Dictation "
    "menu, brings the words back."
)


def _shared() -> Any:
    from quill.ui import windows_dictation_commands

    return windows_dictation_commands


def review_open() -> bool:
    """Whether this app's review window is open."""
    return bool(_desk is not None and _desk.is_open())


def review_desk(host: Any) -> Any:
    """The review desk for *host*: the open one, or a new one belonging to it."""
    global _desk
    from quill.ui.dictation_review_frame import ReviewDesk

    if _desk is None or (not _desk.is_open() and _desk.host is not host):
        _desk = ReviewDesk(host)
    return _desk


class ServiceReviewAi:
    """The review's AI route over a family :class:`~quill.ui.hosted_ai_service.AiService`."""

    def __init__(
        self,
        service: Any,
        *,
        off: Callable[[], str],
        consent: Callable[[], int],
        agree: Callable[[], None],
    ) -> None:
        self._service = service
        self._off = off
        self._consent = consent
        self._agree = agree

    def reason(self) -> str:
        off = self._off()
        if off:
            return off
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            return SAFE_MODE
        if not bool(getattr(self._service, "direct", False)):
            return NO_DIRECT_ROUTE
        return ""

    def provider(self) -> str:
        route = getattr(self._service, "route", "")
        # Codex sends single requests over the ChatGPT plan (decision 21).
        if route in {"chatgpt", "codex"}:
            return "OpenAI, on your ChatGPT subscription"
        if route == "copilot":
            return "GitHub Copilot, on your Copilot plan"
        from quill.core.ai.own_key import provider_name

        name = provider_name(str(getattr(self._service, "own_key_provider", "") or "openai"))
        return f"{name}, with your own key"

    def consented(self) -> bool:
        try:
            return int(self._consent()) >= CONSENT_VERSION
        except (TypeError, ValueError):
            return False

    def agree(self) -> None:
        self._agree()

    def ask(self, prompt: str, on_done: Any, on_error: Any) -> Any:
        return self._service.ask(
            REVIEW_FEATURE,
            prompt,
            None,
            on_done=lambda text, _quota: on_done(str(text)),
            on_error=on_error,
            requires=("text",),
        )

    def cancel(self, request: Any) -> None:
        cancel = getattr(self._service, "cancel", None)
        if callable(cancel):
            cancel(request)


class DictationReviewMixin:
    """Review Dictation, and the review window's hooks, for both editors."""

    def cmd_dictation_review(self) -> None:
        """Take the last phrase (or the held words) into Review Dictation."""
        desk = review_desk(self)
        if desk.is_open():
            desk.focus()
            return
        controller = _shared()._controller
        if controller is not None and controller.active and _shared()._host is self:
            controller.review_last()
            return
        desk.open("")

    # -- the review window's hooks (dictation_review_frame.ReviewDesk) ---------- #

    def _review_parent(self) -> Any:
        return self._dictation_parent()  # type: ignore[attr-defined]

    def _review_say(self, text: str) -> None:
        self._dictation_say(text)  # type: ignore[attr-defined]

    def _review_ai(self) -> ServiceReviewAi | None:
        service_for = getattr(self, "_ai_service", None)
        if not callable(service_for):
            return None
        return ServiceReviewAi(
            service_for(),
            off=self._review_ai_off,
            consent=lambda: getattr(
                self._dictation_settings(), "windows_dictation_review_consent", 0
            ),  # type: ignore[attr-defined]
            agree=self._review_agree,
        )

    def _review_ai_on(self) -> bool:
        """Whether a review could ask the AI now: Dictation Settings offers
        the Polished style only then (D-20)."""
        try:
            ai = self._review_ai()
            return bool(ai is not None and not ai.reason())
        except Exception:  # noqa: BLE001 - unknown is off
            return False

    def _review_ai_off(self) -> str:
        host = getattr(self, "_ai_host", None)
        try:
            on = bool(host().feature_enabled("hosted_ai")) if callable(host) else False
        except Exception:  # noqa: BLE001 - unknown is off
            on = False
        if on:
            return ""
        return (
            "AI help is switched off, so this window cannot change your words. You can "
            "still edit them here, then insert."
        )

    def _review_agree(self) -> None:
        settings = self._dictation_settings()  # type: ignore[attr-defined]
        settings.windows_dictation_review_consent = CONSENT_VERSION
        self._dictation_save_settings()  # type: ignore[attr-defined]

    def _review_rescue_path(self) -> Path:
        from quill.core.windows_dictation.review_session import RESCUE_FILE

        return Path(self._dictation_profile_path()).with_name(RESCUE_FILE)  # type: ignore[attr-defined]

    def _review_my_instructions(self) -> str:
        from quill.core.windows_dictation.instructions import instructions_path, read

        return read(instructions_path(self._dictation_profile_path()))  # type: ignore[attr-defined]

    def _review_context(self) -> str:
        context = getattr(self, "_dictation_document_context", None)
        return str(context()) if callable(context) else ""

    def _review_context_offered(self) -> bool:
        return callable(getattr(self, "_dictation_document_context", None))

    def _review_context_setting(self) -> bool:
        return bool(getattr(self._dictation_settings(), "windows_dictation_review_context", False))  # type: ignore[attr-defined]

    def _review_polish_on(self) -> bool:
        """Allow polishing my dictation with AI (P3, opt-in, off by default)."""
        return bool(getattr(self._dictation_settings(), "windows_dictation_polish", False))  # type: ignore[attr-defined]

    def _review_set_context(self, on: bool) -> None:
        settings = self._dictation_settings()  # type: ignore[attr-defined]
        settings.windows_dictation_review_context = bool(on)
        self._dictation_save_settings()  # type: ignore[attr-defined]

    def _review_retarget(self, document: Any) -> None:
        """Dictation into the review's text while it is open; back afterwards."""
        shared = _shared()
        if document is not None:
            control = self._dictation_control()  # type: ignore[attr-defined]
            self._review_anchor = tuple(int(value) for value in control.GetSelection())
        controller = shared._controller
        if controller is None or not controller.active or shared._host is not self:
            return
        if document is not None:
            from quill.ui.windows_dictation_ports import HostFeedback

            controller.retarget(document, HostFeedback(self))
        else:
            self._dictation_target(self)  # type: ignore[attr-defined]

    def _review_insert(self, text: str, original: str) -> None:
        """One undo step, where the words came from; then back to the document."""
        from quill.core.windows_dictation.composer import compose
        from quill.core.windows_dictation.parser import Piece
        from quill.ui.atomic_edit import replace_as_one_undo

        control = self._dictation_control()  # type: ignore[attr-defined]
        last = int(control.GetLastPosition())
        anchor, self._review_anchor = getattr(self, "_review_anchor", None), None
        start, end = anchor or control.GetSelection()
        start, end = min(int(start), last), min(int(end), last)
        before = str(control.GetRange(max(0, start - 80), start))
        after = str(control.GetRange(end, min(end + 2, last)))
        written = compose((Piece(text, verbatim=True),), before=before, after=after)
        replace_as_one_undo(control, start, end, written)
        self._dictation_after_edit()  # type: ignore[attr-defined]
        controller = _shared()._controller
        if controller is not None:
            for phrase in (original, text):
                if phrase.strip():
                    controller.recent.appendleft(" ".join(phrase.split()))
            controller.note_inserted(written)  # "read that" reads all of it (D-18)
        try:
            wx.CallAfter(control.SetFocus)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            pass
        self._dictation_say("Inserted. Press Control Z to undo.")  # type: ignore[attr-defined]

    def _review_bind_keys(self, frame: Any) -> None:
        """Ctrl+F11 in the review dictates into its text, as in any field."""
        from quill.ui.windows_dictation_tools import bind_field_dictation

        bind_field_dictation(frame, [frame.text], self)

    def _review_mute(self, seconds: float) -> None:
        controller = _shared()._controller
        if controller is not None and controller.active:
            controller.mute_for(seconds)

    def _review_tell_rescue(self) -> None:
        """Once a run, at start: words from last time are waiting -- a review
        that did not finish (D-2), or words not written (D-5)."""
        global _rescue_told
        if _rescue_told:
            return
        _rescue_told = True
        try:
            from quill.ui.dictation_kept import kept_at_start

            sentence = kept_at_start(self._dictation_kept(), RESCUE_NOTICE)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - nothing to tell
            return
        if sentence:
            try:
                wx.CallLater(1500, self._dictation_say, sentence)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - no event loop (tests)
                pass
