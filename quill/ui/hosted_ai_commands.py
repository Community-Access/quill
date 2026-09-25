"""The hosted-AI commands, shared by QUILL and QUILL Lite.

Five commands -- the pad, Ask About This Document, Usage, Sign In or Out and the
Privacy Agreement -- plus the rule that AI never edits on its own.

**Both editors mix this in.** Three things differ between them and nothing else
does, so those three are hooks: which window a new frame is parented to, which
text control the document lives in, and which object holds the settings and the
feature switch. Everything about what the commands *do* -- what they act on,
when an answer may still be applied, what is announced -- is here once. See
:meth:`_ai_parent`, :meth:`_ai_control` and :meth:`_ai_host`.

The feature is switched off until somebody turns it on, so most of what this
module does is open one of the windows in :mod:`quill.ui.hosted_ai_dialogs` and
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

__all__ = ["HostedAiMixin"]


class HostedAiMixin:
    """The hosted-AI commands. Mixed into both editors' document windows."""

    # ------------------------------------------------------------------ #
    # The three hooks -- the only things the two editors do differently
    # ------------------------------------------------------------------ #

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        """The window new AI frames are parented to.

        QUILL Lite's document window *is* a ``wx.Frame``, so it is its own
        parent. QUILL's ``MainFrame`` is a controller that owns one, so it
        overrides this with ``self.frame``. Parenting matters more than it
        looks: a frame parented to nothing is a frame Windows can bury behind
        the editor with no way back to it by keyboard.
        """
        return self

    def _ai_control(self):  # noqa: ANN201 - a text control
        """The control the document is in. ``self.control`` in QUILL Lite,
        ``self.editor`` in QUILL."""
        return self.control

    def _ai_host(self):  # noqa: ANN201 - the app-ish object
        """Whatever holds the settings, the feature switch and the data dir.

        QUILL Lite passes its ``app``. QUILL passes a small adapter
        (:class:`~quill.ui.main_frame_hosted_ai.QuillAiHost`) that answers the
        same five questions against QUILL's own settings and its Use AI switch,
        so neither editor has to learn the other's vocabulary and this module
        does not have to know which one it is running in.
        """
        return self.app

    def _ai_switch_route(self) -> str:
        """Where the switch that turns this feature on lives, in words.

        The one sentence in this module that cannot be written once for both
        editors, because the switch genuinely is in two different places: a
        feature area in QUILL Lite's Customize Features, and the Use AI item in
        QUILL's own AI menu. Every *other* route sentence here names a row that
        exists in both ("Connect or Sign Out in the AI menu"), which is why this
        is the only hook of its kind.
        """
        return "Tools, Customize Features"

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
        from quill.ui.hosted_ai_dialogs import AiUsageFrame

        if not self._ai_service().signed_in:
            self._announce(
                "This computer is not connected to QUILL's free AI. "
                "Choose Connect or Sign Out in the AI menu to connect it."
            )
            return
        self._open_ai_window(
            "usage", lambda: AiUsageFrame(self._ai_parent(), self._ai_service(), self._announce)
        )

    def cmd_ai_sign_in(self) -> None:
        if not self._ai_ready():
            return
        from quill.ui.hosted_ai_dialogs import AiSignInFrame

        self._open_ai_window(
            "sign_in", lambda: AiSignInFrame(self._ai_parent(), self._ai_service(), self._announce)
        )

    # ------------------------------------------------------------------ #
    # Plumbing
    # ------------------------------------------------------------------ #

    def _ai_service(self) -> Any:
        """The app's one AI service, made on first use.

        Built lazily rather than at startup: an install with the area switched
        on but never used should cost nothing, and constructing this reads the
        credential store.
        """
        service = getattr(self._ai_host(), "ai_service", None)
        if service is None:
            from quill.ui.hosted_ai_service import AiService

            service = AiService(self._ai_host())
            self._ai_host().ai_service = service
        return service

    def ai_support_id(self) -> str:
        """This computer's QUILL AI support ID, or "" when it is not connected.

        For About and Get Help from Support, so the number support asks for is
        somewhere a person already looks rather than only in AI Usage. Never
        raises: both callers are windows about something else, and a credential
        store that cannot be read means there is no ID to show.
        """
        try:
            service = self._ai_service()
            return str(service.support_id) if service.signed_in else ""
        except Exception:  # noqa: BLE001 - no ID is an answer, not an error
            return ""

    def ai_support_facts(self) -> dict[str, str]:
        """The support ID as a support-message fact, or nothing.

        Read by :func:`quill.ui.support_dialog.open_support_message` from
        whichever host opened it, so every Get Help from Support carries it
        without each app having to remember to pass it.
        """
        support_id = self.ai_support_id()
        return {"QUILL AI support ID": support_id} if support_id else {}

    def ai_about_usage(self, field: Any) -> None:
        """Add this computer's AI support ID and usage to an About window's text.

        Both About windows call this with their read-only text field just before
        they are shown. Nothing is added when this computer is not connected.
        The support ID is known here and goes in at once; the usage comes from
        the server every time -- limits can be raised or lowered there at any
        moment -- so a placeholder goes in and is replaced when the answer
        arrives, which it does while the About window is still open. The caret
        stays where it was: somebody may already be reading.
        """
        support_id = self.ai_support_id()
        if not support_id:
            return
        placeholder = "Asking QUILL's free AI how much is left..."
        where = field.GetInsertionPoint()
        field.AppendText(
            f"\n\nQUILL's free AI\nSupport ID for this computer: {support_id}\n\n{placeholder}"
        )
        field.SetInsertionPoint(where)

        def fill(text: str) -> None:
            try:
                if not field:
                    return
                value = field.GetValue()
                if placeholder not in value:
                    return
                # The whole value rather than Replace(): a plain multi-line edit
                # counts a line break as two positions and GetValue as one, so an
                # offset found in the string lands in the wrong place.
                caret = field.GetInsertionPoint()
                field.SetValue(value.replace(placeholder, text))
                field.SetInsertionPoint(min(caret, field.GetLastPosition()))
            except RuntimeError:  # the About window closed while we waited
                pass

        from quill.core.ai.gateway_quota_text import describe_quota

        self._ai_service().fetch_quota(
            on_done=lambda quota: fill(describe_quota(quota)),
            on_error=lambda message: fill(f"Usage could not be checked just now. {message}"),
        )

    def cmd_ai_privacy(self) -> None:
        """Read the agreement, and accept or withdraw it.

        One of three doors to the same decision -- the others are Preferences
        and Customize Features -- because whoever wants to check what they
        agreed to will look in whichever of the three they already know. All
        three read and write the same stored version, so none of them can
        disagree with the others.
        """
        if self._ai_privacy_accepted():
            # Show it again; only an explicit Withdraw withdraws. Keeping says
            # nothing: nothing changed, and the reader announces the return.
            from quill.ui.hosted_ai_dialogs import ask_ai_privacy_agreement

            if ask_ai_privacy_agreement(self._ai_parent(), accepted=True):
                self._withdraw_ai_privacy()
            return
        if self._ask_ai_privacy():
            self._light_up_ai()
            # Declining says nothing at all: nothing changed, and the reader
            # announces the caret arriving back.
            self._after_ai_accepted()

    # ------------------------------------------------------------------ #
    # The agreement
    # ------------------------------------------------------------------ #

    def _ai_privacy_accepted(self) -> bool:
        from quill.core.ai.gateway_privacy import is_accepted

        return is_accepted(int(getattr(self._ai_host().settings, "ai_privacy_accepted_version", 0)))

    def _ask_ai_privacy(self) -> bool:
        """Show the agreement. Returns whether it is now accepted.

        Stored immediately rather than at the next settings save: a decision
        somebody made and a crash lost is a decision they have to make again,
        and this is the one decision in the app it would be rude to ask twice.

        **The dialog says nothing; its caller does.** The agreement is reached
        through three doors and on the way to two commands, and what happens
        next is different at every one of them -- so the sentence belongs to
        whoever knows. Announcing it here told somebody who had chosen Sign In
        to "choose Connect or Sign Out in the AI menu", said the same sentence twice
        the Privacy door accepted it, and spoke on a plain Escape, which changes
        nothing and is exactly what GATE-13 says not to say.
        """
        from quill.core.ai.gateway_privacy import AGREEMENT_VERSION
        from quill.ui.hosted_ai_dialogs import ask_ai_privacy_agreement

        self._ai_agreement_just_asked = True
        if not ask_ai_privacy_agreement(self._ai_parent()):
            return False
        self._ai_host().settings.ai_privacy_accepted_version = AGREEMENT_VERSION
        self._ai_host().save_settings()
        return True

    def _after_ai_accepted(self) -> None:
        """Go straight on to connecting, once the agreement is accepted.

        Accepting and then being told to go and find Connect in a menu was a
        yes that stopped halfway: nobody accepts the agreement for any reason
        other than to connect. So a computer that is not connected yet lands in
        the Connect window, whose opening the reader announces; one that already
        is has nothing left to do, and hears that the feature is on.
        """
        if self._ai_service().signed_in:
            self._announce("AI help is on.")
            return
        self.cmd_ai_sign_in()

    def _light_up_ai(self) -> None:
        """Switch the area on, because accepting here means accepting here.

        Whichever of the three doors somebody came through, saying yes should
        leave them with a working feature. Arriving at the agreement from a menu
        that is visible while the area is off -- and it is visible, deliberately --
        and then being told to go and find a second switch would be a yes that
        did nothing.

        Silent: the caller says what changed, because "the area was already on
        and only the agreement is new" is still a change worth hearing, and a
        sentence in here could not be said in that case.
        """
        features = getattr(self._ai_host(), "features", None)
        if features is None or self._ai_host().feature_enabled("hosted_ai"):
            return
        features.set_enabled("hosted_ai", True)
        self._ai_host().save_features()
        self._ai_host().rebuild_all_menus()

    def _withdraw_ai_privacy(self) -> None:
        """Take the agreement back, and the sign-in with it.

        Leaving a token on disk for a service somebody has just said they do not
        agree to use would be keeping the credential for exactly the thing they
        withdrew from.
        """
        self._ai_host().settings.ai_privacy_accepted_version = 0
        self._ai_host().save_settings()
        service = getattr(self._ai_host(), "ai_service", None)
        if service is not None and service.signed_in:
            service.sign_out()
        self._announce(
            "AI help is off and this computer is signed out. Nothing is sent "
            "anywhere. Choose Privacy Agreement in the AI menu to turn it on again."
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
        if self._ask_ai_privacy():
            self._after_ai_accepted()
            return
        self._announce(
            "AI help is in the menus but will not send anything until you "
            "accept the agreement. Privacy Agreement in the AI menu has it again."
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
        if not self._ai_host().feature_enabled("hosted_ai"):
            self._announce(f"AI help is switched off. Turn it on in {self._ai_switch_route()}.")
            return False
        if not self._ai_privacy_accepted():
            return self._ask_ai_privacy()
        return True

    def _open_ai_window(self, name: str, build: Any) -> None:
        """Open one of the *named* AI windows, and only one of each.

        Choosing Sign In a second time built a **second** Sign-In window over
        the first. A frame opening where a frame already is announces nothing,
        so the second press was indistinguishable by ear from a key that is not
        bound. An already-open window is raised and focused instead, which the
        reader does announce.

        Only the windows that are *about this computer* rather than about this
        selection are named: the pad and the result window are built from what
        was selected when the command ran, so a second press must build a second
        one rather than raise a stale one.
        """
        windows = getattr(self, "_ai_windows", None)
        if windows is None:
            windows = {}
            self._ai_windows = windows
        already = windows.get(name)
        if already:
            from quill.ui.hosted_ai_dialogs import take_focus

            take_focus(already)
            return

        def _open() -> None:
            frame = build()
            windows[name] = frame

            def _forget(event: Any) -> None:
                windows.pop(name, None)
                event.Skip()

            frame.Bind(wx.EVT_CLOSE, _forget)
            self._show_ai_window(frame)

        self._after_agreement(_open)

    def _after_agreement(self, open_window: Any) -> None:
        """Run *open_window* once the agreement dialog is fully out of the way.

        The agreement is the one modal surface in this family, and wxMSW hands
        focus back to the **parent** as it tears a modal dialog down -- after a
        focus call made in the same turn of the event loop. A window opened in
        that turn appeared with the caret still in the document: nothing was
        announced, and what the person heard was the command they had just run
        dropping them back where they started.

        Only when the agreement was actually asked for. Every other press opens
        the window straight away, because a deferred window is a window that
        opens after the next keystroke.
        """
        asked = getattr(self, "_ai_agreement_just_asked", False)
        self._ai_agreement_just_asked = False
        if asked and wx.GetApp() is not None:
            wx.CallAfter(open_window)
            return
        open_window()

    def _show_ai_window(self, frame: wx.Frame) -> None:
        """Show a window and actually give it focus.

        The focus half is deferred to the next idle cycle rather than done here,
        because wx has not finished realising the window yet -- and a frame
        parented to an MDI child is not activated by ``Show()`` the way a dialog
        is. Without it the window appears, the caret stays in the document, and
        a screen-reader user is told nothing at all about the thing that just
        opened.
        """
        from quill.ui.hosted_ai_dialogs import take_focus

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
                "Choose Connect or Sign Out in the AI menu to connect it."
            )
            self.cmd_ai_sign_in()
            return

        # One lazy fetch of what the service currently allows, so the size
        # check and the excerpt count match the server rather than a constant
        # compiled in months ago.
        service.refresh_limits()

        from quill.ui.hosted_ai_pad import AiPadFrame

        start, end = self._ai_control().GetSelection()
        document = self._ai_control().GetValue()
        selection = document[start:end] if end > start else ""

        pad = AiPadFrame(
            self._ai_parent(),
            service,
            document_text=document,
            selection=selection,
            position=self._ai_control().GetInsertionPoint(),
            announce=self._announce,
            on_result=lambda feature, text, used: self._show_ai_result(
                feature, text, used, start, end, selection, action
            ),
            initial_action=action,
        )
        # Built now, shown once the agreement (if one was just asked for) has
        # finished handing focus back: the pad reads the selection as it is at
        # the moment the command ran, not at the next idle cycle.
        self._after_agreement(lambda: self._show_ai_window(pad))

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
            current = self._ai_control().GetValue()
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
        replace_as_one_undo(self._ai_control(), start, end, answer)

    def _insert_below(self, answer: str) -> None:
        """Put the answer under the paragraph the cursor is in.

        Under rather than at the caret: an answer dropped mid-sentence is an
        answer somebody has to tidy up, and summaries and answers usually want
        to live beside the text rather than inside it.
        """
        text = self._ai_control().GetValue()
        position = self._ai_control().GetInsertionPoint()
        end = self._paragraph_end(text, position)
        replace_as_one_undo(self._ai_control(), end, end, f"\n\n{answer}")

    @staticmethod
    def _paragraph_end(text: str, position: int) -> int:
        """Where the paragraph containing *position* stops."""
        if not text:
            return 0
        position = max(0, min(position, len(text)))
        break_at = text.find("\n\n", position)
        return len(text) if break_at < 0 else break_at
