"""Review Dictation in QUILL Transcribe (Ctrl+Alt+Shift+F11, the editors' chord; D-2).

The editors' window and the same shared review, not a second one: the window
is :mod:`quill.ui.dictation_review_frame`, the words and what is said are
:mod:`quill.core.windows_dictation.review_conversation`, and "QUILL review
that" is the shared controller's (:mod:`quill.core.windows_dictation.review_mixin`).
What QUILL Transcribe supplies:

* **The field it goes back to.** While the review is open, dictation writes
  into the review's text (the controller is pointed at it, not at the other
  program), so the locked field is never typed into and no "Dictation paused"
  is said: the review is an expected pause. **Insert** brings the locked
  field's window back to the front, and after a moment types the words there
  through the same checked keystrokes as every dictated phrase -- the field
  lock, the password and administrator checks, the never-type list -- inside
  the session, so "QUILL scratch that" takes them back. If the field cannot be
  written, nothing is typed, the reason is said, and the words are in Recent
  Phrases for Insert Again. With dictation off, Insert types into the program
  you switch to, as Insert Again does.
* **The AI.** Whichever AI is in use in QUILL Transcribe's own Choose Your AI
  (:mod:`quill.apps.transcribe_ai`), through the family's AI service
  (:class:`quill.ui.hosted_ai_service.AiService`), so no new network call site
  exists. Its ChatGPT sign-in is QUILL Transcribe's own, "QUILL Transcribe"
  (codex.md decision 2): until Phase 3 it borrowed QUILL's (risk R1), and the
  first time a review needs a plan it does not have, it says so once
  (:func:`~quill.apps.transcribe_ai.own_sign_in_notice`). Safe Mode, or no plan
  and no own key, is AI off: the window still edits and inserts. The consent is
  QUILL Transcribe's own.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.ui.windows_dictation_review import NO_DIRECT_ROUTE, ServiceReviewAi

__all__ = ["RESCUE_FILE", "TranscribeReviewMixin", "later"]

#: QUILL and QUILL Transcribe share a data folder; each keeps its own review.
RESCUE_FILE = "transcribe-dictation-review.json"
#: How long Insert waits for the field's window to come forward before typing.
_INSERT_DELAY_MS = 400
#: The timer that waits; a test runs the callback at once.
later: Any = wx.CallLater


class _TranscribeReviewAi(ServiceReviewAi):
    """The shared review route, saying once that QUILL Transcribe signs in on its own."""

    def __init__(self, service: Any, *, notice: Any = None, **hooks: Any) -> None:
        super().__init__(service, **hooks)
        self._notice = notice

    def reason(self) -> str:
        said = str(super().reason())
        if not said or self._notice is None or not self._needs_plan(said):
            return said
        first = str(self._notice() or "")
        return f"{first} {said}" if first else said

    def _needs_plan(self, said: str) -> bool:
        """No plan or key to review with: not Safe Mode, which is not about a sign-in."""
        return said == NO_DIRECT_ROUTE


class TranscribeReviewMixin:
    """On ``QuillTranscribeFrame``: Review Dictation and its hooks."""

    frame: Any
    _data_dir: Path
    _safe_mode: bool
    _settings: Any

    def review_dictation(self) -> None:
        """Take the last phrase, or the held words, into Review Dictation."""
        desk = self._review_desk()
        if desk.is_open():
            desk.focus()
            return
        controller = getattr(self, "_dictation", None)
        if controller is not None and controller.active:
            controller.review_last()
            return
        desk.open("")

    def _review_desk(self) -> Any:
        desk = getattr(self, "_review", None)
        if desk is None:
            from quill.ui.dictation_review_frame import ReviewDesk

            desk = ReviewDesk(self)
            self._review = desk
        return desk

    def _close_review(self) -> None:
        desk = getattr(self, "_review", None)
        if desk is not None:
            desk.shut_down()

    # -- the review window's hooks (dictation_review_frame.ReviewDesk) ---------- #

    def _review_parent(self) -> Any:
        return self.frame

    def _review_say(self, text: str) -> None:
        self._announce(text, force=True)  # type: ignore[attr-defined]

    def _review_ai(self, *, notice: bool = True) -> Any:
        from quill.core.windows_dictation.review_session import CONSENT_VERSION
        from quill.ui.windows_dictation_review import SAFE_MODE

        return _TranscribeReviewAi(
            self._ai_service(),  # type: ignore[attr-defined]
            off=lambda: SAFE_MODE if self._safe_mode else "",
            consent=lambda: self._settings.dictation.get("windows_dictation_review_consent", 0),
            agree=lambda: self._set_dictation_field(  # type: ignore[attr-defined]
                "windows_dictation_review_consent", CONSENT_VERSION
            ),
            notice=self._own_sign_in_notice if notice else None,
        )

    def _own_sign_in_notice(self) -> str:
        """The one sentence about QUILL Transcribe's own sign-in, the first time a
        review needs a plan it does not have (codex.md decision 2); then ""."""
        if self._settings.ai_sign_in_noticed:
            return ""
        from quill.apps.transcribe_ai import own_sign_in_notice

        self._settings.ai_sign_in_noticed = True
        self._save()  # type: ignore[attr-defined]
        sentence = own_sign_in_notice(self._ai_host().ai_choose_key)  # type: ignore[attr-defined]
        # Spoken and brailled, once: it lands in the review's Status line too,
        # which the reader does not read out by itself (GATE-13's other half).
        self._review_say(sentence)
        return sentence

    def _review_ai_on(self) -> bool:
        """Whether a review could ask the AI now: Dictation Settings offers
        the Polished style only then (D-20). Never says the sign-in sentence."""
        try:
            ai = self._review_ai(notice=False)
            return bool(ai is not None and not ai.reason())
        except Exception:  # noqa: BLE001 - unknown is off
            return False

    def _review_rescue_path(self) -> Path:
        return Path(self._data_dir) / RESCUE_FILE

    def _review_my_instructions(self) -> str:
        from quill.core.speech.dictation_profile import default_profile_path
        from quill.core.windows_dictation.instructions import instructions_path, read

        return read(instructions_path(default_profile_path()))

    def _review_context(self) -> str:
        return ""  # QUILL Transcribe never reads the other program

    def _review_context_offered(self) -> bool:
        return False

    def _review_context_setting(self) -> bool:
        return False

    def _review_polish_on(self) -> bool:
        """Allow polishing my dictation with AI (P3, opt-in, off by default)."""
        return bool(self._settings.dictation.get("windows_dictation_polish", False))

    def _review_set_context(self, on: bool) -> None:
        del on

    def _review_retarget(self, document: Any) -> None:
        controller = getattr(self, "_dictation", None)
        if controller is None or not controller.active:
            return
        if document is not None:
            self._review_field = controller.review_retarget(document)
        else:
            field = getattr(self, "_review_field", None)
            self._review_field = None
            if field is not None:
                controller.review_retarget(field)

    def _review_shown(self, frame: Any) -> None:
        """From the tray, Windows would only flash the taskbar: bring it forward."""
        try:
            from quill.platform.windows.foreground import force_foreground_window

            force_foreground_window(int(frame.GetHandle()))
        except Exception:  # noqa: BLE001 - not Windows, or not allowed: Raise did what it could
            pass

    def _review_mute(self, seconds: float) -> None:
        controller = getattr(self, "_dictation", None)
        if controller is not None and controller.active:
            controller.mute_for(seconds)

    def _review_insert(self, text: str, original: str) -> None:
        """Back to the locked field, then type the words there."""
        controller = getattr(self, "_dictation", None)
        if controller is not None:
            for phrase in (original, text):
                if phrase.strip():
                    controller.recent.appendleft(" ".join(phrase.split()))
        document = controller.document if controller is not None and controller.active else None
        window = document.locked_window() if hasattr(document, "locked_window") else 0
        if not window:
            self.insert_recent_phrase(text)  # type: ignore[attr-defined]
            return
        try:
            from quill.platform.windows.foreground import force_foreground_window

            force_foreground_window(window)
        except Exception:  # noqa: BLE001 - the field check below says if it did not come back
            pass
        try:
            later(_INSERT_DELAY_MS, self._review_type, text)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            self._review_type(text)

    def _review_type(self, text: str) -> None:
        from quill.core.sound_events import SoundEvent

        controller = getattr(self, "_dictation", None)
        if controller is None or not controller.active:
            self.insert_recent_phrase(text)  # type: ignore[attr-defined]
            return
        refusal = controller.insert_reviewed(text)
        if not refusal:
            self._set_status(f"Typed: {text}")  # type: ignore[attr-defined]
            return  # the screen reader echoes the typing
        self._announce(  # type: ignore[attr-defined]
            f"Nothing was typed. {refusal} Your words are in Recent Phrases: Shift+F11, "
            "then Insert Again.",
            force=True,
            sound=SoundEvent.WINDOWS_DICTATION_ERROR,
        )
