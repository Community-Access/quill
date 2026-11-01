"""QUILL Transcribe reaches the family's AI through an adapter, with its own sign-in.

Until codex.md Phase 3 QUILL Transcribe had no AI menu and borrowed QUILL's
ChatGPT sign-in for Review Dictation (risk R1). Now it runs the shared hosted
AI (:mod:`quill.ui.hosted_ai_commands`) the way the editors and the other apps
do, through :class:`TranscribeAiHost` -- the five things the shared code asks
of "the app" -- and :class:`TranscribeAiMixin`, the hooks. So QUILL Transcribe
gets an AI menu with Choose Your AI and all five connections, Which AI Am I
Using, the one AI Usage list, an AI line in its window, and **Ask** about your
dictation.

**Its own sign-in (decision 2).** The ChatGPT and GitHub sign-ins are made as
"QUILL Transcribe", under this app's own agent name and its own credential
entry, exactly as every family app signs in on its own. A sign-in QUILL made is
never read here any more, so nothing of another app's is reused silently: the
one-time migration of ``ai_connection`` sees only QUILL Transcribe's own
sign-in. The first time Review Dictation needs a plan it does not have, it says
so once, in one sentence (:func:`own_sign_in_notice`). What *is* carried over,
once, is the own key's provider and model name from QUILL's settings -- names,
never a key -- so somebody who reviewed with their own Gemini key keeps it.

**Ask** (Ctrl+Shift+8, AI > Ask...) is the family's conversation window
(:mod:`quill.ui.hosted_ai_app_ask`) with the transcript you last reviewed, or
this session's dictated phrases, read fresh every turn
(``app_ask_context.transcribe_context``). Never your voice: speech to text
stays on this computer, or with the speech provider you chose.

**Keys.** Ctrl+1 to Ctrl+9 are QUILL Transcribe's Window menu keys, so, as in
Quill Radio and QUILL Cast, Ask is Ctrl+Shift+8, Which AI Ctrl+F8 and Choose
Your AI Ctrl+Shift+F8 (``app_keymaps.py``, ``app_ai_keys.py``).

**Safe Mode** refuses every AI command.
"""

from __future__ import annotations

import json
from typing import Any

from quill.ui.hosted_ai_commands import HostedAiMixin

__all__ = [
    "AGENT_NAME",
    "AI_ROWS",
    "TranscribeAiHost",
    "TranscribeAiMixin",
    "own_sign_in_notice",
]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Transcribe"

_SAFE_MODE = "AI is off in Safe Mode."
_ABOUT_FACTS = (
    "the transcript you last reviewed, or this session's dictated phrases when there "
    "is none, never your voice"
)

#: The AI menu: command id, label, handler name; "" is a separator. Letters are
#: unique within the menu (A W C G O S P).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    ("tools.hosted_ai_chatgpt", "Use My Chat&GPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI U&sage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)


def own_sign_in_notice(choose_key: str) -> str:
    """The one sentence, said once, about QUILL Transcribe's own sign-in (decision 2)."""
    where = f"press {choose_key}" if choose_key else "use Choose Your AI in the AI menu"
    return (
        "QUILL Transcribe now signs in to your AI on its own and no longer uses "
        f"QUILL's sign-in; {where} to sign in as QUILL Transcribe."
    )


class TranscribeAiHost:
    """What the shared hosted-AI commands mean by "the app", in Transcribe's terms."""

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
        return self._frame._data_dir

    @property
    def settings(self) -> Any:
        """QUILL Transcribe's own settings, which hold its AI choice."""
        settings = self._frame._settings
        if not getattr(settings, "ai_seeded", True):
            _seed_from_quill(settings)
            self.save_settings()
        return settings

    def save_settings(self) -> None:
        try:
            self._frame._save()
        except Exception:  # noqa: BLE001 - a lost choice is never worth a crash
            pass

    def feature_enabled(self, name: str) -> bool:
        """Always on: the agreement, a sign-in or a key still stand between it
        and any request, and Review Dictation has its own opt-in."""
        del name
        return True

    @property
    def features(self) -> TranscribeAiHost:
        return self

    def set_enabled(self, name: str, enabled: bool) -> None:
        del name, enabled

    def save_features(self) -> None:
        """Nothing to save: there is no switch."""

    def rebuild_all_menus(self) -> None:
        """No AI row here is gated, so only the window's AI line changes."""
        refresh = getattr(self._frame, "_refresh_ai_line", None)
        if callable(refresh):
            try:
                refresh()
            except Exception:  # noqa: BLE001 - a status line is never worth a crash
                pass


def _seed_from_quill(settings: Any) -> None:
    """Copy the own key's provider and model names from QUILL's settings, once.

    Names only: the key itself stays in the Windows credential store, where every
    family app's Use My Own AI Key reads it. No sign-in or token is copied.
    """
    settings.ai_seeded = True
    try:
        from quill.core.ai.own_key import load_settings_fields
        from quill.core.settings import settings_path

        data = json.loads(settings_path().read_text(encoding="utf-8"))
        fields = load_settings_fields(data if isinstance(data, dict) else {})
    except Exception:  # noqa: BLE001 - no QUILL settings: keep the defaults
        return
    if not getattr(settings, "ai_own_key_model", ""):
        settings.ai_own_key_provider = fields["ai_own_key_provider"]
        settings.ai_own_key_model = fields["ai_own_key_model"]


class TranscribeAiMixin(HostedAiMixin):
    """The shared hosted-AI commands on QUILL Transcribe's frame: hooks, no commands."""

    #: QUILL Transcribe has no document: an answer is copied, never inserted.
    _insert_below = None

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        return self.frame  # type: ignore[attr-defined]

    def _ai_control(self) -> None:
        """No document here; nothing reads one."""
        return None

    def _ai_host(self) -> TranscribeAiHost:
        host = getattr(self, "_transcribe_ai_host", None)
        if host is None:
            host = TranscribeAiHost(self)
            self._transcribe_ai_host = host
        return host

    def _ai_switch_route(self) -> str:
        return "the AI menu"

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
        """The connection changed: the window's AI line follows."""
        super()._ai_connection_refresh()
        self._refresh_ai_line()

    def _refresh_ai_line(self) -> None:
        field = getattr(self, "_ai_text", None)
        if field is None:
            return
        try:
            value = self.ai_status_text()
            if field.GetValue() != value:
                field.SetValue(value)
        except RuntimeError:  # the window is going
            pass

    # -- Ask ------------------------------------------------------------------- #

    def _ai_app_ask(self) -> None:
        """Ask (Ctrl+Shift+8): the conversation about your dictation (10C)."""
        from quill.core.ai.family_prompt_catalogue import FAMILY_PROMPTS, quick_prompts_for
        from quill.ui.hosted_ai_app_ask import open_app_ask, rows_from_prompts

        prompts = quick_prompts_for("transcribe")
        ordered = [p for p in prompts if p not in FAMILY_PROMPTS] + list(FAMILY_PROMPTS)
        open_app_ask(
            self,
            app="transcribe",
            subject="your dictation",
            about_facts=_ABOUT_FACTS,
            facts=self._transcribe_ask_facts,
            rows=rows_from_prompts(ordered),
            local_answer=self._transcribe_what_can_i_do,
        )

    def _transcribe_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts (``app_ask_context.transcribe_context``), read fresh."""
        del question, needs
        from quill.core.ai.app_ask_context import transcribe_context

        title, text = getattr(self, "_last_transcript", None) or ("", "")
        if not text.strip():
            controller = getattr(self, "_dictation", None)
            phrases = list(getattr(controller, "recent", []) or []) if controller else []
            text = "\n".join(reversed([str(p) for p in phrases]))
            title = "This session's dictation" if text.strip() else ""
        return transcribe_context(text, title=title)

    def _transcribe_what_can_i_do(self) -> str:
        """The local answer, from QUILL Transcribe's own F1 catalogue and its menus."""
        from quill.core.ai.family_prompt_catalogue import what_can_i_do_here
        from quill.core.transcribe.surface_help import purpose_for_title
        from quill.ui.hosted_ai_app_ask import menu_routes

        return what_can_i_do_here(
            purpose_for_title("QUILL Transcribe"),
            commands=menu_routes(self.frame.GetMenuBar()),  # type: ignore[attr-defined]
        )

    # -- the menu -------------------------------------------------------------- #

    def _append_transcribe_ai_menu(self, menu_bar: Any) -> None:
        """The AI menu, on QUILL Transcribe's keys."""
        import wx

        menu = wx.Menu()
        for command_id, label, handler_name in AI_ROWS:
            if not command_id:
                menu.AppendSeparator()
                continue
            item_id = wx.NewIdRef()
            menu.Append(item_id, self._menu_label(label, command_id))  # type: ignore[attr-defined]
            handler = getattr(self, handler_name)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)  # type: ignore[attr-defined]
            self._keep_menu_ids(item_id)  # type: ignore[attr-defined]
        menu_bar.Append(menu, "&AI")
        if not getattr(self, "_transcribe_ai_registered", False):
            self._transcribe_ai_registered = True
            for command_id, label, handler_name in AI_ROWS:
                if command_id:
                    self.commands.try_register(  # type: ignore[attr-defined]
                        command_id,
                        label.replace("&", "").rstrip("."),
                        getattr(self, handler_name),
                        self._binding_for(command_id),  # type: ignore[attr-defined]
                    )
