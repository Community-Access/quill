"""Tools > AI: four commands, and the rule that AI never edits on its own.

The feature is switched off until somebody turns it on, so most of what this
module does is open one of the windows in :mod:`quill.apps.lite_ai_dialogs` and
get out of the way. Three things are decided here rather than there, because
they are about the *document* and the windows deliberately know nothing about
one:

**What the command acts on.** The selection, else the paragraph, else the
section -- resolved in :mod:`quill.core.ai.gateway_context` and never the whole
file. A summary of an entire document is rarely what somebody pressing Summarize
on a paragraph wanted, and it is the expensive answer as well as the wrong one.

**Whether an answer may still be applied.** A request runs in the background
while the editor stays live, so by the time an answer arrives the selection it
came from may have been typed over, deleted, or be in a different document. The
range is captured when the request goes out and checked again before anything is
written, so Replace either puts the answer where it belongs or says plainly that
it cannot.

**That nothing is applied without a keystroke.** Every edit here is the user
pressing a button in the result window, and every one goes in through the
ordinary undo stack so Control Z takes it back like any other edit.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["DocumentAiMixin"]


class DocumentAiMixin:
    """The Tools > AI commands. Mixed into QuillLite's document window."""

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #

    def cmd_ai_assistant(self) -> None:
        """Open the pad on whatever the cursor is in."""
        self._open_ai_pad()

    def cmd_ai_ask_document(self) -> None:
        """Open the pad ready to ask a question about this document.

        The one command whose input is a question rather than the selection,
        which is why it is worth a chord of its own rather than one more row to
        arrow down to.
        """
        self._open_ai_pad(action="document_qna")

    def cmd_ai_usage(self) -> None:
        if not self._ai_ready():
            return
        from quill.apps.lite_ai_dialogs import AiUsageFrame

        if not self._ai_service().signed_in:
            self._announce(
                "This computer is not connected to QUILL's free AI. "
                "Choose Tools, AI, Sign In or Out to connect it."
            )
            return
        self._show_ai_window(AiUsageFrame(self, self._ai_service(), self._announce))

    def cmd_ai_sign_in(self) -> None:
        if not self._ai_ready():
            return
        from quill.apps.lite_ai_dialogs import AiSignInFrame

        self._show_ai_window(AiSignInFrame(self, self._ai_service(), self._announce))

    # ------------------------------------------------------------------ #
    # Plumbing
    # ------------------------------------------------------------------ #

    def _ai_service(self) -> Any:
        """The app's one AI service, made on first use.

        Built lazily rather than at startup: an install with the area switched
        on but never used should cost nothing, and constructing this reads the
        credential store.
        """
        service = getattr(self.app, "ai_service", None)
        if service is None:
            from quill.apps.lite_ai import AiService

            service = AiService(self.app)
            self.app.ai_service = service
        return service

    def cmd_ai_privacy(self) -> None:
        """Read the agreement, and accept or withdraw it.

        One of three doors to the same decision -- the others are Preferences
        and Customize Features -- because whoever wants to check what they
        agreed to will look in whichever of the three they already know. All
        three read and write the same stored version, so none of them can
        disagree with the others.
        """
        if self._ai_privacy_accepted():
            self._withdraw_ai_privacy()
            return
        if self._ask_ai_privacy():
            self._light_up_ai()

    # ------------------------------------------------------------------ #
    # The agreement
    # ------------------------------------------------------------------ #

    def _ai_privacy_accepted(self) -> bool:
        from quill.core.ai.gateway_privacy import is_accepted

        return is_accepted(int(getattr(self.app.settings, "ai_privacy_accepted_version", 0)))

    def _ask_ai_privacy(self) -> bool:
        """Show the agreement. Returns whether it is now accepted.

        Stored immediately rather than at the next settings save: a decision
        somebody made and a crash lost is a decision they have to make again,
        and this is the one decision in the app it would be rude to ask twice.
        """
        from quill.apps.lite_ai_dialogs import ask_ai_privacy_agreement
        from quill.core.ai.gateway_privacy import AGREEMENT_VERSION

        if not ask_ai_privacy_agreement(self, self._announce):
            return False
        self.app.settings.ai_privacy_accepted_version = AGREEMENT_VERSION
        self.app.save_settings()
        return True

    def _light_up_ai(self) -> None:
        """Switch the area on, because accepting here means accepting here.

        Whichever of the three doors somebody came through, saying yes should
        leave them with a working feature. Arriving at the agreement from a menu
        that is visible while the area is off -- and it is visible, deliberately --
        and then being told to go and find a second switch would be a yes that
        did nothing.
        """
        features = getattr(self.app, "features", None)
        if features is None or self.app.feature_enabled("hosted_ai"):
            return
        features.set_enabled("hosted_ai", True)
        self.app.save_features()
        self.app.rebuild_all_menus()
        self._announce("AI help is on. Choose Tools, AI, Sign In or Out to connect this computer.")

    def _withdraw_ai_privacy(self) -> None:
        """Take the agreement back, and the sign-in with it.

        Leaving a token on disk for a service somebody has just said they do not
        agree to use would be keeping the credential for exactly the thing they
        withdrew from.
        """
        self.app.settings.ai_privacy_accepted_version = 0
        self.app.save_settings()
        service = getattr(self.app, "ai_service", None)
        if service is not None and service.signed_in:
            service.sign_out()
        self._announce(
            "AI help is off and this computer is signed out. Nothing is sent "
            "anywhere. Choose Tools, AI, Privacy Agreement to turn it on again."
        )

    def _offer_ai_privacy_on_enable(self) -> None:
        """Ask for the agreement right after somebody switches the area on.

        Door two of three. This is the one where the question is most likely to
        be a surprise -- applying the "Everything" profile turns the area on
        along with seventeen others -- so it says what just happened before it
        asks anything, and an answer of no changes nothing else about the
        features that were just saved.
        """
        if self._ai_privacy_accepted():
            return
        if not self._ask_ai_privacy():
            self._announce(
                "AI help is in the menus but will not send anything until you "
                "accept the agreement. Tools, AI, Privacy Agreement has it again."
            )

    def _ai_ready(self) -> bool:
        """Whether AI may run: the area is on **and** the agreement is accepted.

        Two separate questions, deliberately. The area answers "does this
        feature exist in my copy"; the agreement answers "have I agreed to what
        it does". An area switched on by a profile, by a settings import, or by
        somebody else using this machine is not consent, so the second question
        has to be asked on its own.

        A missing agreement is an offer rather than a refusal. Somebody who
        pressed the AI key wants AI, and the next thing they need is the
        decision itself -- not a message telling them they cannot have it.
        """
        if not self.app.feature_enabled("hosted_ai"):
            self._announce("AI help is switched off. Turn it on in Tools, Customize Features.")
            return False
        if not self._ai_privacy_accepted():
            return self._ask_ai_privacy()
        return True

    def _show_ai_window(self, frame: wx.Frame) -> None:
        """Show a window and actually give it focus.

        The focus half is deferred to the next idle cycle rather than done here,
        because wx has not finished realising the window yet -- and a frame
        parented to an MDI child is not activated by ``Show()`` the way a dialog
        is. Without it the window appears, the caret stays in the document, and
        a screen-reader user is told nothing at all about the thing that just
        opened.
        """
        from quill.apps.lite_ai_dialogs import take_focus

        frame.Show()
        frame.Raise()
        self._last_shown_ai_window = frame
        # Deferred through CallAfter when there is a running app, and called
        # straight through when there is not. ``wx.CallAfter`` *asserts* without
        # one rather than degrading, so the guard is not a test accommodation:
        # it is the difference between a missed focus and a crash in any context
        # that has a window but no loop yet.
        if wx.GetApp() is not None:
            wx.CallAfter(take_focus, frame)
        else:
            take_focus(frame)

    def _open_ai_pad(self, action: str = "") -> None:
        if not self._ai_ready():
            return

        service = self._ai_service()
        if not service.signed_in:
            self._announce(
                "This computer is not connected to QUILL's free AI. "
                "Choose Tools, AI, Sign In or Out to connect it."
            )
            self.cmd_ai_sign_in()
            return

        # One lazy fetch of what the service currently allows, so the size
        # check and the excerpt count match the server rather than a constant
        # compiled in months ago.
        service.refresh_limits()

        from quill.apps.lite_ai_pad import AiPadFrame

        start, end = self.control.GetSelection()
        document = self.control.GetValue()
        selection = document[start:end] if end > start else ""

        pad = AiPadFrame(
            self,
            service,
            document_text=document,
            selection=selection,
            position=self.control.GetInsertionPoint(),
            announce=self._announce,
            on_result=lambda feature, text, used: self._show_ai_result(
                feature, text, used, start, end, selection, action
            ),
            initial_action=action,
        )
        self._show_ai_window(pad)

    def _show_ai_result(
        self,
        feature: str,
        text: str,
        used: str,
        start: int,
        end: int,
        original: str,
        action: str,
    ) -> None:
        from quill.apps.lite_ai_pad import AiResultFrame

        can_replace = bool(original) and self._selection_unchanged(start, end, original)

        frame = AiResultFrame(
            self,
            action=feature,
            text=text,
            used=used,
            on_replace=(
                (lambda answer: self._replace_range(start, end, answer)) if can_replace else None
            ),
            on_insert=self._insert_below,
            on_again=lambda: self._open_ai_pad(action=action),
            announce=self._announce,
        )
        self._show_ai_window(frame)

    def _selection_unchanged(self, start: int, end: int, original: str) -> bool:
        """Is the text this answer came from still exactly where it was?

        The editor stayed live while the request ran, so it may not be. Writing
        an answer over whatever happens to occupy those offsets now would be a
        silent, wrong edit -- the worst kind, because the undo stack would show
        it as something the user did.
        """
        try:
            current = self.control.GetValue()
        except Exception:  # noqa: BLE001 - a closed control is "changed"
            return False
        return 0 <= start <= end <= len(current) and current[start:end] == original

    def _replace_range(self, start: int, end: int, answer: str) -> None:
        """Write *answer* over ``[start, end)`` as one undoable edit.

        Reachable only when the range still held the text this answer came from
        -- ``_show_ai_result`` does not offer Replace otherwise -- so there is no
        second check here. One check, at the point where the button is decided
        on, rather than two that could disagree.
        """
        replace_as_one_undo(self.control, start, end, answer)

    def _insert_below(self, answer: str) -> None:
        """Put the answer under the paragraph the cursor is in.

        Under rather than at the caret: an answer dropped mid-sentence is an
        answer somebody has to tidy up, and summaries and answers usually want
        to live beside the text rather than inside it.
        """
        text = self.control.GetValue()
        position = self.control.GetInsertionPoint()
        end = self._paragraph_end(text, position)
        replace_as_one_undo(self.control, end, end, f"\n\n{answer}")

    @staticmethod
    def _paragraph_end(text: str, position: int) -> int:
        """Where the paragraph containing *position* stops."""
        if not text:
            return 0
        position = max(0, min(position, len(text)))
        break_at = text.find("\n\n", position)
        return len(text) if break_at < 0 else break_at
