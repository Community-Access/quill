"""The family's AI in a small QuillVille app: one adapter, hooks only (codex.md Phase 3).

Quill Radio, QUILL Cast, QUILL Studio and QUILL Transcribe each reach the shared
hosted AI (:mod:`quill.ui.hosted_ai_commands`) through an adapter of their own.
Quill Weather, Quill Converter, Quill Media Player, Quill Inkwell and QuillBeacon
need exactly the same five answers -- who the app is, where its settings live,
which window is its parent, what its AI line says, and what Ask is about -- so
they share this one, and each app's own module is a few constants and its facts.

* :class:`AppAiHost` is what the shared code means by "the app": the app's own
  agent name ("QUILL Weather"), so its ChatGPT and GitHub sign-ins are its own
  and never another app's; its own settings file
  (:mod:`quill.core.ai.app_ai_settings`), seeded once with the own key's names
  from QUILL's settings; and the AI line and gated labels to refresh.
* :class:`AppAiMixin` is the hooks: Safe Mode refusing every AI command, the AI
  menu (from the app's ``_AI_ROWS``, on its keys from ``APP_KEYMAPS``), the
  read-only AI line (decision 19's status cell, for a window whose status bar
  cannot take focus), Ask with the app's own facts, and a single-request helper
  every app feature sends through. It defines no command: the shared mixins
  hold every ``cmd_ai_*`` handler, and each app's own feature lives in its own
  features mixin (a test holds every adapter to that).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.hosted_ai_commands import HostedAiMixin

__all__ = ["SAFE_MODE", "AppAiHost", "AppAiMixin", "ai_row_letters"]

SAFE_MODE = "AI is off in Safe Mode."
_LINE_HELP = (
    "Which AI is in use, as Which AI Am I Using says it. Press Enter to open Choose Your AI."
)


def ai_row_letters(rows: tuple[tuple[str, str, str], ...]) -> list[str]:
    """The access letters an AI menu's rows claim, for the uniqueness tests."""
    letters = []
    for command_id, label, _handler in rows:
        if command_id and "&" in label:
            letters.append(label[label.index("&") + 1].upper())
    return letters


class AppAiHost:
    """What the shared hosted-AI commands mean by "the app", for one small app."""

    def __init__(self, frame: Any, *, app: str, agent_name: str) -> None:
        self._frame = frame
        self._app = app
        self.ai_agent_name = agent_name
        self.ai_service: Any = None
        self._settings: Any = None

    @property
    def ai_choose_key(self) -> str:
        """Choose Your AI's key here, for the sentences that name it."""
        try:
            return str(self._frame._ai_binding("tools.hosted_ai_choose") or "")
        except Exception:  # noqa: BLE001 - a missing keymap names no key
            return ""

    @property
    def data_dir(self):  # noqa: ANN201 - Path
        from quill.core.paths import app_data_dir

        return app_data_dir()

    @property
    def settings(self) -> Any:
        """The app's own AI choice (``<app>-ai.json``), read once and kept."""
        if self._settings is None:
            from quill.core.ai.app_ai_settings import load_app_ai_settings, seed_from_quill

            self._settings = load_app_ai_settings(self.data_dir, self._app)
            try:
                from quill.core.settings import settings_path

                quill_settings = settings_path()
            except Exception:  # noqa: BLE001 - no QUILL settings path: nothing to copy
                quill_settings = None
            if quill_settings is not None and seed_from_quill(self._settings, quill_settings):
                self.save_settings()
        return self._settings

    def save_settings(self) -> None:
        if self._settings is None:
            return
        try:
            from quill.core.ai.app_ai_settings import save_app_ai_settings

            save_app_ai_settings(self.data_dir, self._app, self._settings)
        except Exception:  # noqa: BLE001 - a lost choice is never worth a crash
            pass

    def feature_enabled(self, name: str) -> bool:
        """Always on: the agreement, a sign-in or a key still stand between it
        and any request, and none of these apps ever had an AI switch."""
        del name
        return True

    @property
    def features(self) -> AppAiHost:
        return self

    def set_enabled(self, name: str, enabled: bool) -> None:
        del name, enabled

    def save_features(self) -> None:
        """Nothing to save: there is no switch."""

    def rebuild_all_menus(self) -> None:
        """Only gated labels and the AI line can change, so only they are rewritten."""
        for name in ("_app_ai_relabel", "_refresh_ai_line"):
            refresh = getattr(self._frame, name, None)
            if callable(refresh):
                try:
                    refresh()
                except Exception:  # noqa: BLE001 - a label is never worth a crash
                    pass


class AppAiMixin(HostedAiMixin):
    """The shared hosted-AI commands on a small app's frame: hooks, no commands.

    An app sets the class constants and supplies ``_app_ask_facts(question,
    needs)`` (an ``AppFacts``) and ``_app_ai_purpose()`` (its window's authored
    F1 purpose).
    """

    #: The app id: ``APP_KEYMAPS`` key and settings file name.
    _AI_APP = ""
    #: What OpenAI and GitHub show on their consent pages for this app.
    _AI_AGENT_NAME = ""
    #: The AI rows: command id, label, handler name; "" is a separator.
    _AI_ROWS: tuple[tuple[str, str, str], ...] = ()
    #: Ask's subject ("this forecast") and what goes with every message.
    _AI_SUBJECT = ""
    _AI_ABOUT_FACTS = ""

    #: No document here: an answer is copied, never inserted.
    _insert_below = None

    # -- the hooks -------------------------------------------------------------- #

    def _ai_frame(self) -> Any:
        """The app's top-level window: ``self.frame`` on the app shell, else self."""
        return getattr(self, "frame", None) or self

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        return self._ai_frame()

    def _ai_control(self) -> None:
        """No document here; nothing reads one."""
        return None

    def _ai_host(self) -> AppAiHost:
        host = getattr(self, "_app_ai_host", None)
        if host is None:
            host = AppAiHost(self, app=self._AI_APP, agent_name=self._AI_AGENT_NAME)
            self._app_ai_host = host
        return host

    def _ai_switch_route(self) -> str:
        return "the AI menu"

    def _ai_refuse_safe_mode(self) -> bool:
        if not self._ai_safe_mode():
            return False
        self._announce(SAFE_MODE)  # type: ignore[attr-defined]
        return True

    def _ai_switched_on(self) -> bool:
        return not self._ai_refuse_safe_mode()

    def _ai_ready(self) -> bool:
        if self._ai_refuse_safe_mode():
            return False
        return bool(super()._ai_ready())

    def _ai_connection_refresh(self) -> None:
        """The connection changed: gated labels and the AI line follow."""
        super()._ai_connection_refresh()
        self._refresh_ai_line()

    # -- keys -------------------------------------------------------------------- #

    def _ai_binding(self, command_id: str) -> str:
        """The key *command_id* answers to here: the user's, else the app's default."""
        binding_for = getattr(self, "_binding_for", None)
        if callable(binding_for):
            return str(binding_for(command_id) or "")
        from quill.core.app_keymaps import APP_KEYMAPS
        from quill.core.keymap import DEFAULT_KEYMAP

        return str(
            APP_KEYMAPS.get(self._AI_APP, {}).get(command_id) or DEFAULT_KEYMAP.get(command_id, "")
        )

    def _ai_menu_label(self, label: str, command_id: str) -> str:
        menu_label = getattr(self, "_menu_label", None)
        if callable(menu_label):
            return str(menu_label(label, command_id))
        binding = self._ai_binding(command_id)
        return f"{label}\t{binding}" if binding and "," not in binding else label

    # -- the menu ----------------------------------------------------------------- #

    def _append_app_ai_rows(self, menu: Any) -> None:
        """The AI rows, appended to *menu* (a new AI menu, or Beacon's Assist)."""
        import wx

        frame = self._ai_frame()
        self._app_ai_menu = menu
        self._app_ai_items: dict[str, tuple[int, str, str]] = {}
        refs = getattr(self, "_app_ai_refs", None)
        if refs is None:
            refs = []
            self._app_ai_refs = refs
        for command_id, label, handler_name in self._AI_ROWS:
            if not command_id:
                menu.AppendSeparator()
                continue
            item_id = wx.NewIdRef()
            refs.append(item_id)
            shown = self._ai_gated_label(handler_name, label)  # codex.md 10A.8
            menu.Append(item_id, self._ai_menu_label(shown, command_id))
            self._app_ai_items[handler_name] = (int(item_id), label, command_id)
            handler = getattr(self, handler_name)
            frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)
        keep = getattr(self, "_keep_menu_ids", None)
        if callable(keep):
            keep(*refs)
        self._register_app_ai_commands()

    def _append_app_ai_menu(self, menu_bar: Any, title: str = "&AI") -> Any:
        """A top-level AI menu holding the rows; returns it."""
        import wx

        menu = wx.Menu()
        self._append_app_ai_rows(menu)
        menu_bar.Append(menu, title)
        return menu

    def _register_app_ai_commands(self) -> None:
        """Every AI row in the command registry, once, where the app has one."""
        commands = getattr(self, "commands", None)
        if commands is None or getattr(self, "_app_ai_registered", False):
            return
        self._app_ai_registered = True
        for command_id, label, handler_name in self._AI_ROWS:
            if command_id:
                commands.try_register(
                    command_id,
                    label.replace("&", "").rstrip("."),
                    getattr(self, handler_name),
                    self._ai_binding(command_id) or None,
                )

    def _app_ai_relabel(self) -> None:
        """Rewrite the gated rows' labels after the connection changed (10A.8)."""
        menu = getattr(self, "_app_ai_menu", None)
        if menu is None:
            return
        for handler_name, (item_id, label, command_id) in getattr(
            self, "_app_ai_items", {}
        ).items():
            try:
                item = menu.FindItemById(item_id)
                if item is not None:
                    shown = self._ai_gated_label(handler_name, label)
                    item.SetItemLabel(self._ai_menu_label(shown, command_id))
            except RuntimeError:  # the window is going
                return

    # -- the AI line -------------------------------------------------------------- #

    def _build_ai_line(self, panel: Any, sizer: Any, *, border: int = 8) -> Any:
        """The read-only AI line (decision 19): "AI: ChatGPT plan"; Enter opens Choose.

        No access key: a label sharing a menu's letter would take it from the
        menu (GATE-14), and Tab reaches it.
        """
        import wx

        label = wx.StaticText(panel, label="AI:")
        field = wx.TextCtrl(panel, style=wx.TE_READONLY)
        field.SetName("AI")
        field.SetHelpText(_LINE_HELP)
        field.Bind(wx.EVT_KEY_DOWN, self._on_ai_line_key)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(field, 1)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border)
        self._ai_text = field
        self._refresh_ai_line()
        return field

    def _on_ai_line_key(self, event: Any) -> None:
        import wx

        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.cmd_ai_choose()
            return
        event.Skip()

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

    # -- Ask ------------------------------------------------------------------------ #

    def _ai_app_ask(self) -> None:
        """Ask: the family's conversation window, with this app's facts (10C)."""
        from quill.core.ai.family_prompt_catalogue import FAMILY_PROMPTS, quick_prompts_for
        from quill.ui.hosted_ai_app_ask import open_app_ask, rows_from_prompts

        prompts = quick_prompts_for(self._AI_APP)
        ordered = [p for p in prompts if p not in FAMILY_PROMPTS] + list(FAMILY_PROMPTS)
        open_app_ask(
            self,
            app=self._AI_APP,
            subject=self._AI_SUBJECT,
            about_facts=self._AI_ABOUT_FACTS,
            facts=self._app_ask_facts,
            rows=rows_from_prompts(ordered),
            local_answer=self._app_what_can_i_do,
        )

    def _app_ask_facts(self, question: str, needs: str) -> Any:  # pragma: no cover - per app
        raise NotImplementedError

    def _app_ai_purpose(self) -> str:  # pragma: no cover - per app
        return ""

    def _app_what_can_i_do(self) -> str:
        """The local answer, from the app's own F1 catalogue and its menus."""
        from quill.core.ai.family_prompt_catalogue import what_can_i_do_here
        from quill.ui.hosted_ai_app_ask import menu_routes

        return what_can_i_do_here(
            self._app_ai_purpose(),
            commands=menu_routes(self._ai_frame().GetMenuBar()),
        )

    # -- one request ------------------------------------------------------------------ #

    def _app_ai_request(
        self,
        prompt: str,
        on_answer: Callable[[str], None],
        *,
        working: str = "Working.",
        feature: str = "ask",
    ) -> bool:
        """Send one text request to the connection in use, if AI may run. True if sent.

        Behind Safe Mode, the agreement and the capability gate (GATE-CAPS: the
        service asks again before anything leaves). A failure is said, never
        retried and never switched.
        """
        if not self._ai_ready() or not self._ai_capable("text"):
            return False
        service = self._ai_service()
        self._announce(working)  # type: ignore[attr-defined]
        service.ask(
            feature,
            prompt,
            None,
            on_done=lambda text, _quota: on_answer(str(text or "").strip()),
            on_error=lambda sentence: self._announce(sentence),  # type: ignore[attr-defined]
            requires=("text",),
        )
        return True

    def _app_ai_show(self, answer: str, *, title: str = "") -> None:
        """An answer: said, because focus stays where it was, and kept to read again."""
        from quill.ui.hosted_ai_app_ask import show_app_answer

        show_app_answer(self, answer, title=title)
