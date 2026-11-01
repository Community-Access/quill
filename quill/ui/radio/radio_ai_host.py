"""Quill Radio reaches the family's AI through an adapter, not an AI of its own.

Until codex.md Phase 3, Quill Radio had its own assistant (Ask QUILL Radio) on
one route only, the listener's ChatGPT plan. Now it runs the shared hosted AI
(:mod:`quill.ui.hosted_ai_commands`) the way QUILL, QUILL Lite and QUILL Cast
do, through :class:`RadioAiHost` -- the five things the shared code asks of
"the app" -- and :class:`RadioAiMixin`, the hooks. So Quill Radio gets Choose
Your AI with all five connections, Which AI Am I Using, the one AI Usage list,
the AI status cell and capability gating, from the same code as everyone else.

What Radio *does* with AI -- Ask about what is playing, and describing the
video picture -- is :mod:`quill.ui.radio.radio_ai_features`; this module has no
command of its own.

**Radio's own settings.** The choice, the own key's provider and model and the
free AI's agreement are kept in :class:`~quill.core.radio.history.RadioHistory`,
Radio's own record, under the field names the editors use, and the ChatGPT and
GitHub sign-ins are made as "QUILL Radio" (the agent name Ask QUILL Radio has
always signed in under, so an existing sign-in carries straight over and the
one-time migration keeps it in use).

**Keys.** Ctrl+1 to Ctrl+9 are Quill Radio's Window menu keys on every window,
so the editors' Ctrl+4, Ctrl+6 and Ctrl+8 cannot be AI keys here; Which AI is
Ctrl+F8, Choose Your AI Ctrl+Shift+F8 and Ask keeps Ctrl+Shift+8
(``app_keymaps.py`` says why, rule 11).

**Peer windows.** Every AI window opens as a peer in Radio's window model: on
the Window menu, with Ctrl+W and the transport keys, and focus goes back where
it was when it closes.

**Safe Mode** refuses every AI command, as Ask QUILL Radio always did.
"""

from __future__ import annotations

from typing import Any

from quill.ui.hosted_ai_commands import HostedAiMixin
from quill.ui.radio.radio_ai_features import RadioAiFeaturesMixin
from quill.ui.radio.radio_ai_watch import RadioWatchMixin

__all__ = ["AGENT_NAME", "AI_ROWS", "RadioAiHost", "RadioAiMixin"]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Radio"

_SAFE_MODE = "AI is off in Safe Mode."

#: Community > AI: command id, label, handler name. Letters unique within the
#: submenu (F W C G O U P). Find and Record is the family's agent task
#: (``tools.hosted_ai_task``, codex.md 6.5), in radio_ai_features.
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_task", "&Find and Record...", "cmd_ai_task"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("radio.chatgpt_account", "Use My Chat&GPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI &Usage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)

#: Ask, the first row of the Community menu, on Ask QUILL Radio's id and key.
ASK_ROW = ("radio.ask_quill_radio", "&Ask...", "cmd_ai_chat_key")


class RadioAiHost:
    """What the shared hosted-AI commands mean by "the app", in Radio's terms."""

    ai_agent_name = AGENT_NAME

    def __init__(self, frame: Any) -> None:
        self._frame = frame
        self.ai_service: Any = None

    @property
    def ai_choose_key(self) -> str:
        """Choose Your AI's key here, for the sentences that name it."""
        try:
            return str(self._frame._binding_for("tools.hosted_ai_choose") or "")
        except Exception:  # noqa: BLE001 - a missing keymap names no key
            return ""

    @property
    def data_dir(self):  # noqa: ANN201 - Path
        from quill.core.paths import app_data_dir

        return app_data_dir()

    @property
    def settings(self) -> Any:
        """Radio's own record: the agreement, the own key and the stored choice."""
        return self._frame._radio_history

    def save_settings(self) -> None:
        try:
            self._frame._save_radio_history()
        except Exception:  # noqa: BLE001 - a history write is never worth a crash
            pass

    def feature_enabled(self, name: str) -> bool:
        """Always on: Radio's AI never had a switch, and the agreement, a sign-in
        or a key still stand between it and any request."""
        del name
        return True

    @property
    def features(self) -> RadioAiHost:
        return self

    def set_enabled(self, name: str, enabled: bool) -> None:
        del name, enabled

    def save_features(self) -> None:
        """Nothing to save: there is no switch."""

    def rebuild_all_menus(self) -> None:
        try:
            self._frame._build_menu_bar()
        except Exception:  # noqa: BLE001 - a menu rebuild is never worth a crash
            pass


class RadioAiMixin(RadioAiFeaturesMixin, RadioWatchMixin, HostedAiMixin):
    """The shared hosted-AI commands on Quill Radio's frame: hooks, no commands."""

    #: Radio has no document: an answer is copied, never inserted.
    _insert_below = None

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        return self.frame  # type: ignore[attr-defined]

    def _ai_control(self) -> None:
        """No document in Radio; nothing here reads one."""
        return None

    def _ai_host(self) -> RadioAiHost:
        host = getattr(self, "_radio_ai_host", None)
        if host is None:
            host = RadioAiHost(self)
            self._radio_ai_host = host
        return host

    def _ai_switch_route(self) -> str:
        return "Community, AI"

    def _ai_refuse_safe_mode(self) -> bool:
        if not getattr(self, "_safe_mode", False):
            return False
        self._announce(_SAFE_MODE)  # type: ignore[attr-defined]
        return True

    def _ai_switched_on(self) -> bool:
        return not self._ai_refuse_safe_mode()

    def _ai_ready(self) -> bool:
        if self._ai_refuse_safe_mode():
            return False
        return bool(super()._ai_ready())

    def _ai_connection_refresh(self) -> None:
        """The connection changed: the gated labels and the AI status cell follow."""
        super()._ai_connection_refresh()
        refresh = getattr(self, "_refresh_statusbar", None)
        if callable(refresh):
            try:
                refresh()
            except RuntimeError:  # the window is going
                pass

    def _show_ai_window(self, frame: Any) -> None:
        """Every AI window is a peer in Radio's window model (Window menu, Ctrl+W)."""
        windows = getattr(self, "_windows", None)
        if windows is not None and not getattr(frame, "_radio_peer", False):
            frame._radio_peer = True
            _install_peer(self, frame, windows)
        super()._show_ai_window(frame)

    # -- the menu -------------------------------------------------------------- #

    def _radio_ai_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_radio_ai_menu_ids", None)
        if ids is None:
            import wx

            ids = {cid: wx.NewIdRef() for cid, _label, _h in (ASK_ROW, *AI_ROWS)}
            self._radio_ai_menu_ids = ids
            self._keep_menu_ids(*ids.values())  # type: ignore[attr-defined]
        return ids

    def _append_radio_ai_rows(self, menu: Any) -> None:
        """Ask, then the AI submenu, at the top of the Community menu."""
        import wx

        ids = self._radio_ai_ids()
        ask_id, label, _handler = ASK_ROW
        menu.Append(ids[ask_id], self._menu_label(label, ask_id))  # type: ignore[attr-defined]
        sub = wx.Menu()
        for command_id, row_label, handler_name in AI_ROWS:
            shown = self._ai_gated_label(handler_name, row_label)  # codex.md 10A.8
            sub.Append(ids[command_id], self._menu_label(shown, command_id))  # type: ignore[attr-defined]
        menu.AppendSubMenu(sub, "A&I")
        if getattr(self, "_radio_ai_wired", False):
            return
        self._radio_ai_wired = True
        for command_id, _label, handler_name in (ASK_ROW, *AI_ROWS):
            handler = getattr(self, handler_name)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id])  # type: ignore[attr-defined]

    def _register_radio_ai_commands(self) -> None:
        """Every AI row in the command registry, on Radio's own keys."""
        rows = (
            (ASK_ROW[0], "Ask", ASK_ROW[2]),
            *((cid, label.replace("&", "").rstrip("."), h) for cid, label, h in AI_ROWS),
            ("radio.describe_video", "Describe the Video", "cmd_radio_describe_video"),
            ("radio.ai_watch_start", "Start Watching for Changes", "cmd_radio_watch_start"),
            ("radio.ai_watch_stop", "Stop Watching for Changes", "cmd_radio_watch_stop"),
        )
        for command_id, label, handler_name in rows:
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                label,
                getattr(self, handler_name),
                self._binding_for(command_id),  # type: ignore[attr-defined]
                feature_id="core.radio",
            )


def _install_peer(host: Any, frame: Any, windows: Any) -> None:
    """A peer window: its own menu with Close, the Window menu, transport keys."""
    import wx

    title = str(frame.GetTitle() or "AI")
    menu_bar = frame.GetMenuBar() or wx.MenuBar()
    own = wx.Menu()
    close_id = wx.NewIdRef()
    own.Append(close_id, "&Close\tCtrl+W")
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
    # F: no AI window spends it (A is Copy the Sign-In Address and Try Again).
    menu_bar.Append(own, "&File")
    windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    host._keep_menu_ids(close_id)
    try:
        from quill.ui.radio import transport_keys

        transport_keys.install(frame, host, wx=wx, extra_entries=windows.accelerator_entries())
    except Exception:  # noqa: BLE001 - the transport is a convenience here
        pass
    windows.register(frame, title)

    def on_close(event: Any) -> None:
        previous = windows.previous_key(frame)
        windows.unregister(frame)
        event.Skip()
        if previous:
            wx.CallAfter(windows.activate, previous)

    frame.Bind(wx.EVT_CLOSE, on_close)
