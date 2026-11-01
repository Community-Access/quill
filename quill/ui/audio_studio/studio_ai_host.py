"""QUILL Studio reaches the family's AI through an adapter, not an AI of its own.

Until codex.md Phase 3 Studio had its own picture chooser
(``studio_vision_route``): its own ChatGPT sign-in, or the AI provider set up
in QUILL, with a question between the two. Now it runs the shared hosted AI
(:mod:`quill.ui.hosted_ai_commands`) the way the editors, Quill Radio and QUILL
Cast do, through :class:`StudioAiHost` -- the five things the shared code asks
of "the app" -- and :class:`StudioAiMixin`, the hooks. So Studio gets Choose
Your AI with all five connections, Which AI Am I Using, the one AI Usage list,
the AI status cell and capability gating, from the same code as everyone else,
and every picture it sends goes to the connection chosen there.

What Studio *does* with AI -- Ask about the recording, Describe a Picture, and
the Screenshot Inspector's questions -- is
:mod:`quill.ui.audio_studio.studio_ai_features`; this module has no command of
its own. Make a Picture keeps its own key and its own-key route (decision 13),
and Set Up AI stays for cloud voices, chapter titles and translation.

**Studio's own settings** are :mod:`quill.core.audio_studio.ai_settings`, under
the editors' field names, and the ChatGPT sign-in is made as "QUILL Studio" --
the name Studio's own sign-in always used, so an existing sign-in carries
straight over and the one-time migration keeps it in use.

**Keys.** Studio has no Window menu, so the editors' keys hold: Ask Ctrl+6,
Which AI Ctrl+8 (pressed twice, Choose Your AI) and Choose Your AI Ctrl+4.

**Safe Mode** and the family's AI Off refuse every AI command.
"""

from __future__ import annotations

from typing import Any

from quill.ui.audio_studio.studio_ai_features import StudioAiFeaturesMixin
from quill.ui.audio_studio.studio_ai_watch import StudioWatchMixin
from quill.ui.hosted_ai_commands import HostedAiMixin

__all__ = ["AGENT_NAME", "AI_ROWS", "StudioAiHost", "StudioAiMixin"]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Studio"

_SAFE_MODE = "AI is off in Safe Mode."

#: The AI menu: command id, label, handler name; "" is a separator. Letters are
#: unique within the menu (A W C R N D H T G O S P, and U for Set Up AI).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    # The agent tasks (codex.md 6.1 and 6.8), in studio_ai_features: R and N.
    ("tools.hosted_ai_task", "&Recording Pre-flight Check...", "cmd_ai_task"),
    ("studio.ai_narrative", "&Narrate a Recording...", "cmd_studio_ai_narrative"),
    ("studio.describe_picture", "&Describe a Picture...", "cmd_studio_describe_picture"),
    # Tell me when this changes (decision 25): studio_ai_watch, H and T.
    ("studio.ai_watch_start", "Start Watching for C&hanges", "cmd_studio_watch_start"),
    ("studio.ai_watch_stop", "S&top Watching for Changes", "cmd_studio_watch_stop"),
    ("", "", ""),
    ("studio.chatgpt_account", "Use My Chat&GPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI U&sage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)


class StudioAiHost:
    """What the shared hosted-AI commands mean by "the app", in Studio's terms."""

    ai_agent_name = AGENT_NAME

    def __init__(self, frame: Any) -> None:
        self._frame = frame
        self.ai_service: Any = None
        self._settings: Any = None

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
        """Studio's own AI choice (``studio-ai.json``), read once and kept."""
        if self._settings is None:
            from quill.core.audio_studio.ai_settings import load_ai_settings

            self._settings = load_ai_settings(self.data_dir)
        return self._settings

    def save_settings(self) -> None:
        try:
            from quill.core.audio_studio.ai_settings import save_ai_settings

            save_ai_settings(self.data_dir, self.settings)
        except Exception:  # noqa: BLE001 - a lost choice is never worth a crash
            pass

    def feature_enabled(self, name: str) -> bool:
        """The family's AI Off switch (QUILL's Use AI), which Studio always honoured."""
        del name
        try:
            from quill.core.ai.model_manager import load_ai_enabled

            return bool(load_ai_enabled())
        except Exception:  # noqa: BLE001 - unreadable is the default, on
            return True

    @property
    def features(self) -> StudioAiHost:
        return self

    def set_enabled(self, name: str, enabled: bool) -> None:
        del name, enabled

    def save_features(self) -> None:
        """Nothing to save: the switch is QUILL's."""

    def rebuild_all_menus(self) -> None:
        """Only the gated row's label can change, so only it is rewritten."""
        relabel = getattr(self._frame, "_studio_ai_relabel", None)
        if callable(relabel):
            try:
                relabel()
            except Exception:  # noqa: BLE001 - a label is never worth a crash
                pass


class StudioAiMixin(StudioAiFeaturesMixin, StudioWatchMixin, HostedAiMixin):
    """The shared hosted-AI commands on Studio's frame: hooks, no commands."""

    #: Studio has no document: an answer is copied, never inserted.
    _insert_below = None

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        return self.frame  # type: ignore[attr-defined]

    def _ai_control(self) -> None:
        """No document in Studio; nothing here reads one."""
        return None

    def _ai_host(self) -> StudioAiHost:
        host = getattr(self, "_studio_ai_host", None)
        if host is None:
            host = StudioAiHost(self)
            self._studio_ai_host = host
        return host

    def _ai_switch_route(self) -> str:
        return "QUILL's AI menu, Use AI"

    def _ai_refuse_safe_mode(self) -> bool:
        if not getattr(self, "_safe_mode", False):
            return False
        self._announce(_SAFE_MODE)  # type: ignore[attr-defined]
        return True

    def _ai_switched_on(self) -> bool:
        if self._ai_refuse_safe_mode():
            return False
        return bool(super()._ai_switched_on())

    def _ai_ready(self) -> bool:
        if self._ai_refuse_safe_mode():
            return False
        return bool(super()._ai_ready())

    def _ai_connection_refresh(self) -> None:
        """The connection changed: the gated label and the AI status cell follow."""
        super()._ai_connection_refresh()
        refresh = getattr(self, "_refresh_statusbar", None)
        if callable(refresh):
            try:
                refresh()
            except RuntimeError:  # the window is going
                pass

    # -- the menu -------------------------------------------------------------- #

    def _append_studio_ai_menu(self, menu_bar: Any) -> list[tuple[Any, Any]]:
        """The AI menu: Ask, Which AI, Choose, Describe, the accounts, Set Up AI.

        Returns ``(id, handler)`` pairs for the frame's one binding loop.
        """
        import wx

        menu = wx.Menu()
        bindings: list[tuple[Any, Any]] = []
        self._studio_ai_items: dict[str, tuple[Any, str]] = {}
        for command_id, label, handler_name in AI_ROWS:
            if not command_id:
                menu.AppendSeparator()
                continue
            item_id = wx.NewIdRef()
            shown = self._ai_gated_label(handler_name, label)  # codex.md 10A.8
            menu.Append(item_id, self._menu_label(shown, command_id))  # type: ignore[attr-defined]
            self._studio_ai_items[handler_name] = (item_id, label)
            bindings.append((item_id, getattr(self, handler_name)))
        menu.AppendSeparator()
        setup_id = wx.NewIdRef()
        menu.Append(
            setup_id,
            "Set &Up AI...\tCtrl+Alt+Shift+A",
            "Connect an AI provider for cloud voices, chapter titles, and translation",
        )
        bindings.append((setup_id, self.open_ai_setup))  # type: ignore[attr-defined]
        menu_bar.Append(menu, "&AI")
        self._studio_ai_menu = menu
        return bindings

    def _studio_ai_relabel(self) -> None:
        """Rewrite the gated rows' labels after the connection changed (10A.8)."""
        menu = getattr(self, "_studio_ai_menu", None)
        if menu is None:
            return
        for handler_name, (item_id, label) in getattr(self, "_studio_ai_items", {}).items():
            command_id = next(cid for cid, _l, h in AI_ROWS if h == handler_name)
            item = menu.FindItemById(int(item_id))
            if item is not None:
                shown = self._ai_gated_label(handler_name, label)
                item.SetItemLabel(self._menu_label(shown, command_id))  # type: ignore[attr-defined]

    def _register_studio_ai_commands(self) -> None:
        """Every AI row in the command registry, on Studio's keys."""
        for command_id, label, handler_name in AI_ROWS:
            if not command_id:
                continue
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                label.replace("&", "").rstrip("."),
                getattr(self, handler_name),
                self._binding_for(command_id),  # type: ignore[attr-defined]
            )
