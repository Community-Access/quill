"""Choose Your AI's commands, shared by QUILL and QUILL Lite (codex.md 10A).

A base of :class:`quill.ui.hosted_ai_commands.HostedAiMixin`, like the ChatGPT
commands, so both editors get every handler here the moment they get the rest
and QUILL's adapter keeps having no commands of its own.

* **Which AI Am I Using** (Ctrl+8) speaks one line: the connection, the model,
  and one usage clause. Pressed twice within half a second -- the window
  QUILL's Spoken Echo double press has always used -- it opens the window.
* **Choose Your AI** (Ctrl+4) opens :mod:`quill.ui.hosted_ai_connections`.
* **Usage** opens the one usage list (:mod:`quill.ui.hosted_ai_usage`).
* **Use My Own AI Key**, **Use My ChatGPT Subscription** and **Connect or Sign
  Out** keep their keys and ids (rule 5) and open the window on their own row
  with its sign-in step ready.

**Capability gating (10A.8).** Every gated AI command stays listed and keyed;
its label says what it needs, and pressing it sends nothing and offers the
switch in one Yes/No whose default is Yes. No AI in use at all (decision 15)
opens the window and says so once.
"""

from __future__ import annotations

import time
from typing import Any

__all__ = ["DOUBLE_PRESS_WINDOW", "ChooseAiMixin"]

#: Seconds between two presses of Which AI that open the window instead. The
#: same half second as ``MainFrame._ECHO_DOUBLE_PRESS_WINDOW``, so the family's
#: one double-press habit has one speed.
DOUBLE_PRESS_WINDOW = 0.5

_CHOOSE_WINDOW = "choose"


class ChooseAiMixin:
    """Which AI, Choose Your AI, Usage, the three account doors and the gate."""

    # -- the commands ------------------------------------------------------ #

    def cmd_ai_which(self) -> None:
        """Say which AI is in use; pressed twice, open Choose Your AI."""
        now = time.monotonic()
        last = getattr(self, "_ai_which_pressed_at", None)
        self._ai_which_pressed_at = now
        if last is not None and now - last <= DOUBLE_PRESS_WINDOW:
            self._ai_which_pressed_at = None  # a third press speaks again
            self.cmd_ai_choose()
            return
        if not self._ai_switched_on():
            return
        service = self._ai_service()
        later = getattr(service, "which_ai_later", None)
        if callable(later):  # GitHub's count is fetched off the UI thread
            later(self._announce)
            return
        which = getattr(service, "which_ai", None)
        if callable(which):
            self._announce(which())

    def cmd_ai_choose(self) -> None:
        """Open Choose Your AI on the row in use."""
        self._ai_open_choose()

    def cmd_ai_usage(self) -> None:
        """One read-only list of every connection's usage, and Manage Usage."""
        if not self._ai_switched_on():
            return
        from quill.ui.hosted_ai_usage import UsageFrame

        service = self._ai_service()
        fetch = bool(getattr(service, "signed_in", False)) and self._ai_privacy_accepted()
        facts = getattr(service, "connection_facts", None)
        copilot = bool(callable(facts) and facts().copilot_signed_in)
        self._open_ai_window(
            "usage",
            lambda: UsageFrame(
                self._ai_parent(),
                service,
                self._announce,
                fetch_free=fetch,
                fetch_copilot=copilot,
            ),
        )

    def cmd_ai_own_key(self) -> None:
        """Use My Own AI Key (Alt+F2): the window, on its row, with the key dialog up."""
        if self._ai_choosable():
            self._ai_open_choose("own_key", sign_in=True)
            return
        # An app with no stored choice yet (Cast, until Phase 3): the dialog alone.
        if not self._ai_switched_on():
            return
        service = self._ai_service()
        note = getattr(service, "note_readiness", None)
        if callable(note):
            note()
        outcome = self._ai_own_key_dialog()
        if outcome:
            self._ai_route_changed("own_key")  # saving a key here chooses it (10A.5)
            self._announce(outcome)

    def cmd_ai_sign_in(self) -> None:
        """Connect or Sign Out: the window, on the free AI's row.

        Connect is offered only when this computer is not connected yet, and
        only because somebody pressed this (decision 23).
        """
        if not self._ai_choosable():
            self._ai_open_connect()  # an app with no stored choice yet (Cast)
            return
        service = self._ai_service() if self._ai_host().feature_enabled("hosted_ai") else None
        connected = bool(getattr(service, "signed_in", False))
        self._ai_open_choose("free", sign_in=not connected)

    # -- the window ----------------------------------------------------------- #

    def _ai_choosable(self) -> bool:
        """Whether this app stores a choice (``ai_connection``). QUILL and QUILL
        Lite do; an app whose turn comes in Phase 3 keeps its old windows."""
        settings = getattr(self._ai_host(), "settings", None)
        return hasattr(settings, "ai_connection")

    def _ai_safe_mode(self) -> bool:
        flag = getattr(self, "_safe_mode", None)
        if flag is not None:
            return bool(flag)
        import os
        import sys

        from quill.stability.safe_mode import should_enable_safe_mode

        return should_enable_safe_mode(sys.argv, os.environ)

    def _ai_open_choose(self, select: str = "", *, sign_in: bool = False) -> None:
        """Open (or raise) Choose Your AI on *select*, its sign-in step ready if asked."""
        if not self._ai_switched_on():
            return
        from quill.ui.hosted_ai_connections import ChooseAiFrame, ChooseAiHooks

        service = self._ai_service()
        hooks = ChooseAiHooks(
            announce=self._announce,
            connect_free=self._ai_open_connect,
            own_key=self._ai_own_key_dialog,
            changed=self._ai_connection_refresh,
            app_name=str(getattr(self._ai_host(), "ai_agent_name", "") or "QUILL"),
            safe_mode=self._ai_safe_mode(),
        )
        self._open_ai_window(
            _CHOOSE_WINDOW,
            lambda: ChooseAiFrame(self._ai_parent(), service, hooks, select=select),
        )
        frame = getattr(self, "_ai_windows", {}).get(_CHOOSE_WINDOW)
        if frame is None:
            return
        if select and callable(getattr(frame, "select", None)):
            frame.select(select)
        if sign_in and callable(getattr(frame, "start_sign_in", None)):
            self._ai_later(frame.start_sign_in, select)

    def _ai_later(self, func: Any, *args: Any) -> None:
        """Run *func* once the window is on screen, so a modal step opens over it."""
        import wx

        if wx.GetApp() is not None:
            wx.CallAfter(func, *args)
        else:
            func(*args)

    def _ai_open_connect(self) -> None:
        """The free AI's Connect step: the agreement, then the code (decision 23)."""
        if not self._ai_ready():
            return
        from quill.ui.hosted_ai_dialogs import AiSignInFrame

        self._open_ai_window(
            "sign_in", lambda: AiSignInFrame(self._ai_parent(), self._ai_service(), self._announce)
        )

    def _ai_own_key_dialog(self) -> str:
        """Use My Own AI Key's dialog. Returns what to say, or "" on Cancel."""
        import wx

        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.hosted_ai_own_key import OwnKeyDialog

        settings = self._ai_host().settings
        dialog = OwnKeyDialog(self._ai_parent(), settings, self._announce)
        try:
            if show_modal_dialog(dialog, "Use My Own AI Key") != wx.ID_OK:
                return ""
            outcome = dialog.apply(settings)
        finally:
            dialog.Destroy()
        self._ai_host().save_settings()
        return str(outcome)

    # -- after a change --------------------------------------------------------- #

    def _ai_connection_refresh(self) -> None:
        """The connection changed: gated labels, and the AI status cell, follow."""
        host = self._ai_host()
        host._ai_status_text = None
        try:
            host.rebuild_all_menus()
        except Exception:  # noqa: BLE001 - a menu rebuild is never worth a crash
            pass
        for frame in list(getattr(host, "frames", None) or [self]):
            touch = getattr(frame, "_touch_status", None) or getattr(
                frame, "_schedule_statusbar_refresh", None
            )
            if callable(touch):
                try:
                    touch()
                except RuntimeError:  # a window mid-teardown
                    pass

    def ai_status_text(self) -> str:
        """The AI status cell (decision 19): "AI: ChatGPT plan". Cached on the host
        until the connection changes, because the bar refreshes on every pause."""
        host = self._ai_host()
        cached = getattr(host, "_ai_status_text", None)
        if cached:
            return str(cached)
        try:
            if not host.feature_enabled("hosted_ai"):
                text = "AI: off"
            else:
                cell = getattr(self._ai_service(), "status_cell", None)
                text = str(cell()) if callable(cell) else "AI"
        except Exception:  # noqa: BLE001 - a status cell never takes the bar down
            text = "AI"
        host._ai_status_text = text
        return text

    # -- capability gating ------------------------------------------------------ #

    def _ai_needs_suffix(self, capability: str) -> str:
        """What a gated label adds after its name, or "" when the connection can."""
        try:
            if not self._ai_host().feature_enabled("hosted_ai"):
                return ""
            label = getattr(self._ai_service(), "needs_label", None)
            return str(label(capability)) if callable(label) else ""
        except Exception:  # noqa: BLE001 - a label is never worth a crash
            return ""

    def _ai_gated_label(self, handler: str, label: str) -> str:
        """*label* with what *handler* needs, when the connection in use cannot."""
        from quill.core.ai.connection_words import COMMAND_NEEDS, with_needs

        needs = COMMAND_NEEDS.get(handler)
        return with_needs(label, self._ai_needs_suffix(needs)) if needs else label

    def _ai_capable(self, capability: str) -> bool:
        """Whether a command needing *capability* may go on (10A.8).

        No AI in use: open the window and say so once. A connection that cannot:
        send nothing, and offer the switch in one Yes/No whose default is Yes,
        because the person just asked for this. Yes is a choice, not a fallback.
        """
        service = self._ai_service()
        if not hasattr(service, "connection_in_use"):
            return True  # a stand-in service that predates Choose Your AI
        if not service.connection_in_use:
            from quill.core.ai.connection_choice import NO_AI_IN_USE

            self._ai_open_choose()
            self._announce(NO_AI_IN_USE)
            return False
        if service.can_do(capability):
            return True
        from quill.ui.hosted_ai_connections import ask_yes_no

        offer = service.capability_offer(capability)
        if not (offer.target or offer.open_row) or not self._ai_choosable():
            self._announce(offer.sentence)
            return False
        if not ask_yes_no(self._ai_parent(), offer.sentence, default_yes=True):
            return False
        if offer.target and service.choose(offer.target):
            self._ai_connection_refresh()
            return True
        self._ai_open_choose(offer.open_row)
        return False

    # -- Ask (10C.3) ------------------------------------------------------------- #

    def _ai_ask_context(self) -> list[str]:
        """This turn's facts: the passage, the title and the outline."""
        from quill.core.ai.ask_context import ask_context, facts_block

        control = self._ai_control()
        try:
            text = control.GetValue()
            start, end = control.GetSelection()
            position = control.GetInsertionPoint()
        except RuntimeError:  # the document closed under the conversation
            return []
        selection = text[start:end] if end > start else ""
        return facts_block(ask_context(text, selection, position, self._ai_document_title()))
