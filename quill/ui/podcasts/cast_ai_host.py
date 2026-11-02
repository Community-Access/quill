"""QUILL Cast reaches the shared hosted AI through an adapter, not an AI of its own.

ear.md A1 (qc.md, Cast follow-on integrations: ChatGPT). QUILL and QUILL Lite
already run one hosted-AI implementation (:mod:`quill.ui.hosted_ai_commands`)
through one adapter each; that module's own rule is that an adapter that grows
a command of its own has forked the capability quietly. So Cast gets exactly
what QUILL got: :class:`CastAiHost`, answering the five things the shared code
asks of "the app", and :class:`CastAiMixin`, three hooks and no commands.
A test asserts the absence of commands here the way QUILL's does.

What the shared commands act on in Cast is the **show notes pane** under the
library tree (:mod:`quill.ui.notes_reader`): the free AI Assistant summarises,
explains or rewrites the notes of the episode you are on, Ask About This
Document asks about them, Ask About an Image (a ChatGPT plan or a Gemini key)
describes a picture, and the ChatGPT subscription, own key, usage and privacy
windows are the family's. The notes are read only, so nothing here ever
writes into Cast: Replace My Selection and Insert Below say so and offer Copy.

The switch is **AI help** in Preferences (``PodcastHistory.ai_help_enabled``,
off), and the agreement is the shared one -- both, not either, as QUILL Lite's
docstring says: an area switched on by an import is not consent. The OpenAI
consent page names "QUILL Cast", because each app signs in on its own.

**Choose Your AI** (codex.md Phase 3): Cast stores its own ``ai_connection``
in the history record, so it gets the window with all five connections, Which
AI Am I Using, the one AI Usage list, the AI status cell and capability gating
from the shared code, and **Ask** with Cast's own facts
(:mod:`quill.ui.podcasts.cast_ai_ask`). Ctrl+1 to Ctrl+9 are Cast's Window menu
keys (and an episode list's Quick Actions), so Ask is Ctrl+Shift+8, Which AI
Ctrl+F8 and Choose Your AI Ctrl+Shift+F8, as in Quill Radio
(:mod:`quill.core.app_ai_keys`).
"""

from __future__ import annotations

from typing import Any

from quill.ui.hosted_ai_commands import HostedAiMixin

__all__ = ["CastAiHost", "CastAiMixin", "AI_ROWS"]

_FEATURE = "hosted_ai"

#: The submenu's rows: command id, label, handler name. Mnemonics are unique
#: within the submenu (A M R E N K G C Y O U L, and cast_ai_features' own).
#: Find and Follow is the family's agent task (codex.md 6.5); its handler is
#: cast_ai_features', because this adapter has no command of its own. Every
#: other letter of "Find and Follow" is taken in this submenu, so it is Fo&llow
#: (Build Me a Listening Run moved to the free B to give up the L).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "Which AI A&m I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "Choose You&r AI...", "cmd_ai_choose"),
    ("tools.hosted_ai_task", "Find and Fo&llow...", "cmd_ai_task"),
    ("", "", ""),
    ("tools.hosted_ai_assistant", "Fr&ee AI Assistant...", "cmd_ai_assistant"),
    ("tools.hosted_ai_ask_document", "Ask About These Show &Notes...", "cmd_ai_ask_document"),
    ("tools.hosted_ai_image", "As&k About an Image...", "cmd_ai_image"),
    ("", "", ""),
    ("tools.hosted_ai_usage", "AI Usa&ge...", "cmd_ai_usage"),
    ("tools.hosted_ai_sign_in", "&Connect or Sign Out...", "cmd_ai_sign_in"),
    ("tools.hosted_ai_privacy", "Privac&y Agreement...", "cmd_ai_privacy"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_chatgpt", "Use My ChatGPT S&ubscription...", "cmd_ai_chatgpt"),
)


class CastAiHost:
    """What the shared hosted-AI commands mean by "the app", in Cast's terms.

    Thin and stateless beyond the one cached service: every question goes to
    the live ``PodcastHistory``, which is where Cast keeps everything the
    listener chose, so nothing here can drift from what is saved.
    """

    ai_agent_name = "QUILL Cast"

    @property
    def ai_choose_key(self) -> str:
        """Choose Your AI's key here, for the sentences that name it."""
        try:
            return str(self._frame._binding_for("tools.hosted_ai_choose") or "")
        except Exception:  # noqa: BLE001 - a missing keymap names no key
            return ""

    def __init__(self, frame: Any) -> None:
        self._frame = frame
        self.ai_service: Any = None

    @property
    def data_dir(self):  # noqa: ANN201 - Path
        from quill.core.paths import app_data_dir

        return app_data_dir()

    @property
    def settings(self) -> Any:
        """The history record: it carries the agreement version, the own key's
        provider and model, and the switch."""
        return self._frame._podcast_history

    def save_settings(self) -> None:
        try:
            self._frame._save_podcast_history()
        except Exception:  # noqa: BLE001 - a history write is never worth a crash
            pass

    def feature_enabled(self, name: str) -> bool:
        if name != _FEATURE:
            return True
        return bool(getattr(self.settings, "ai_help_enabled", False))

    @property
    def features(self) -> CastAiHost:
        return self

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name == _FEATURE:
            self.settings.ai_help_enabled = bool(enabled)

    def save_features(self) -> None:
        self.save_settings()

    def rebuild_all_menus(self) -> None:
        try:
            self._frame._build_menu_bar()
        except Exception:  # noqa: BLE001 - a menu rebuild is never worth a crash
            pass


class CastAiMixin(HostedAiMixin):
    """The shared hosted-AI commands on Cast's frame: hooks only, no commands."""

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        return self.frame  # type: ignore[attr-defined]

    def _ai_control(self):  # noqa: ANN201 - a text control
        """The show notes pane: what the AI commands read in Cast."""
        pane = getattr(self, "_notes_pane", None)
        return pane.field if pane is not None else None

    def _ai_host(self) -> CastAiHost:
        host = getattr(self, "_cast_ai_host", None)
        if host is None:
            host = CastAiHost(self)
            self._cast_ai_host = host
        return host

    def _ai_switch_route(self) -> str:
        return "Preferences, AI help"

    def _ai_connection_refresh(self) -> None:
        """The connection changed: the gated labels and the AI status cell follow."""
        super()._ai_connection_refresh()
        refresh = getattr(self, "_refresh_statusbar", None)
        if callable(refresh):
            try:
                refresh()
            except RuntimeError:  # the window is going
                pass

    # The notes are read only: an answer never goes into Cast.
    def _replace_range(self, start: int, end: int, answer: str) -> None:
        del start, end, answer
        self._announce(
            "Show notes cannot be changed in QUILL Cast. Copy puts the answer on the clipboard."
        )  # type: ignore[attr-defined]

    def _insert_below(self, answer: str) -> None:
        del answer
        self._announce(
            "Show notes cannot be changed in QUILL Cast. Copy puts the answer on the clipboard."
        )  # type: ignore[attr-defined]

    # -- the menu -------------------------------------------------------------- #

    def _cast_ai_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_cast_ai_ids", None)
        if ids is None:
            import wx

            ids = {cid: wx.NewIdRef() for cid, _label, _h in AI_ROWS if cid}
            self._cast_ai_ids = ids
        return ids

    def _append_cast_ai_submenu(self, parent_menu: Any) -> None:
        """Help > AI Features: the shared rows, on the family's chords where Cast
        has them free (``APP_KEYMAPS["cast"]``). Bound and registered once."""
        import wx

        ids = self._cast_ai_menu_ids()
        sub = wx.Menu()
        for command_id, label, handler_name in AI_ROWS:
            if not command_id:
                sub.AppendSeparator()
                continue
            shown = self._ai_gated_label(handler_name, label)  # codex.md 10A.8
            sub.Append(ids[command_id], self._menu_label(shown, command_id))  # type: ignore[attr-defined]
        # Cast's own domain verbs (ear.md A2-A9) live in cast_ai_features, not
        # here: this adapter has no command of its own.
        extra = getattr(self, "_append_cast_ai_feature_rows", None)
        if callable(extra):
            extra(sub)
        parent_menu.AppendSubMenu(sub, "AI &Features")
        if not getattr(self, "_cast_ai_wired", False):
            self._cast_ai_wired = True
            for command_id, label, handler_name in AI_ROWS:
                if not command_id:
                    continue
                handler = getattr(self, handler_name)
                self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id])  # type: ignore[attr-defined]
                self.commands.try_register(  # type: ignore[attr-defined]
                    command_id,
                    label.replace("&", "").rstrip("."),
                    handler,
                    self._binding_for(command_id),  # type: ignore[attr-defined]
                )
