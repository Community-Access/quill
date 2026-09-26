"""QUILL's half of the hosted AI: the free service, as the *default* AI.

The hosted service -- QUILL's own gateway, free, nothing to configure, no key to
paste -- shipped in QUILL Lite first. That was backwards twice over. The family
rule says the small editor is never ahead of the big one, and the practical
version of that rule is sharper than the principle: **nobody opens QUILL and
notices the absence of something they have only ever seen elsewhere.** A missing
feature files no bug. So the windows moved into ``quill/ui`` and QUILL reaches
them here.

It is not merely added, it is the **front door**. QUILL's AI menu has four
pillars, seven submenus, an Hub, a Library and an agent catalogue, all of which
assume you have already decided which company should see your writing and found
somewhere to paste an API key. That is a reasonable surface for somebody who
wants it and an absurd one for somebody who wants a paragraph summarised. So the
five hosted-AI rows are what the menu opens with, and everything else is behind
**Show advanced AI features** -- one checkbox, in the same menu, remembered.

Two objects live here:

* :class:`QuillAiHost` -- the adapter. :mod:`quill.ui.hosted_ai_commands` needs
  five things from "the app": a data directory, settings it can read and write,
  a feature switch it can read and turn on, and a way to rebuild the menus.
  QUILL Lite's ``app`` answers all five directly; QUILL's equivalents are spread
  across ``self.settings``, ``save_settings`` and the Use AI switch in
  ``model_manager``. This maps one to the other so that neither editor has to
  learn the other's vocabulary and the shared module does not have to know which
  one it is running in.
* :class:`HostedAiCommandsMixin` -- the three hooks, and nothing else. Every
  command, every refusal and every announcement is the shared module's. If this
  class ever grows a command of its own, the capability has forked and the rule
  above has been broken quietly.
"""

from __future__ import annotations

from typing import Any

from quill.ui.hosted_ai_commands import HostedAiMixin

__all__ = ["HostedAiCommandsMixin", "QuillAiHost"]

#: The feature name the shared module asks about. QUILL Lite has a real feature
#: area by this name; QUILL has the Use AI master switch, which answers the same
#: question -- "does AI exist in my copy" -- so the adapter maps the one name
#: onto it rather than inventing a second switch for people to find and
#: disagree with.
_HOSTED_AI_FEATURE = "hosted_ai"


class QuillAiHost:
    """What the shared hosted-AI commands mean by "the app", in QUILL's terms.

    Deliberately thin and deliberately dumb. It holds no state of its own beyond
    the one cached service, so there is nothing here that can drift out of step
    with the settings it is reading -- every question goes to the live object.
    """

    def __init__(self, frame: Any) -> None:
        self._frame = frame
        #: The shared module stores the one :class:`AiService` here, on first
        #: use. Held on the adapter rather than on ``MainFrame`` so that the
        #: attribute the shared code looks for is the one it created.
        self.ai_service: Any = None

    # -- where things are stored ------------------------------------------ #

    @property
    def data_dir(self):  # noqa: ANN201 - Path
        from quill.core.paths import app_data_dir

        return app_data_dir()

    @property
    def settings(self) -> Any:
        return self._frame.settings

    def save_settings(self) -> None:
        """Write the settings now, swallowing a read-only profile.

        Now rather than at the next save, because the one thing stored through
        here is a privacy decision, and a decision somebody made and a crash
        lost is a decision they have to make again. Swallowing the failure is
        the same trade the font code makes: the choice still holds for this
        session, and refusing it because a file is locked would be the worst
        possible answer to "I agree".
        """
        from quill.core.settings import save_settings

        try:
            save_settings(self._frame.settings)
        except Exception:  # noqa: BLE001 - a settings write is never worth a crash
            pass

    # -- the feature switch ----------------------------------------------- #

    def feature_enabled(self, name: str) -> bool:
        from quill.core.ai.model_manager import load_ai_enabled

        if name != _HOSTED_AI_FEATURE:
            return True
        return load_ai_enabled()

    @property
    def features(self) -> QuillAiHost:
        """The shared code calls ``app.features.set_enabled(...)``; that is this.

        Returning ``self`` rather than building a second object: there is one
        switch and one place it is written, and an adapter that hands out a
        sub-adapter would be two things to keep honest.
        """
        return self

    def set_enabled(self, name: str, enabled: bool) -> None:
        from quill.core.ai.model_manager import save_ai_enabled

        if name == _HOSTED_AI_FEATURE:
            save_ai_enabled(bool(enabled))

    def save_features(self) -> None:
        """Nothing to do: :meth:`set_enabled` already wrote the switch.

        Present because the shared code calls it, and honest about being empty
        rather than pretending to a second write QUILL does not have.
        """

    def rebuild_all_menus(self) -> None:
        """Rebuild the menu bar so the AI rows appear or disappear at once.

        The rows are appended once while the menu is built and gated on the
        switch, so a contextual refresh -- which only enables and disables what
        is already there -- would never add or remove one.
        """
        try:
            self._frame._build_menu()
        except Exception:  # noqa: BLE001 - a menu rebuild is never worth a crash
            pass


class HostedAiCommandsMixin(HostedAiMixin):
    """The shared hosted-AI commands, wired to QUILL's frame, editor and settings.

    Three overrides and no commands. That is the whole point: QUILL and QUILL Lite
    run the same code for the same five keys, so a fix to one is a fix to both
    and neither can word an announcement the other does not.
    """

    def _ai_parent(self):  # noqa: ANN201 - wx.Window
        """QUILL's ``MainFrame`` is a controller, not a window; its frame is.

        Getting this wrong is not cosmetic. A frame parented to ``None`` is one
        Windows will happily bury behind the editor with no keyboard route back
        to it, which for a modeless window somebody is waiting on an answer in
        is the difference between a feature and a lost window.
        """
        return self.frame

    def _ai_control(self):  # noqa: ANN201 - a text control
        return self.editor

    def _ai_switch_route(self) -> str:
        """QUILL's switch is the Use AI item in the AI menu, not a feature area."""
        return "the AI menu, Use Artificial Intelligence"

    def _own_key_menu_id(self) -> Any:
        """The Use My Own OpenAI Key row's id, made once so a rebuilt menu reuses
        the id its binding was made against."""
        menu_id = getattr(self, "_hosted_ai_own_key_id", None)
        if menu_id is None:
            import wx

            menu_id = wx.NewIdRef()
            self._hosted_ai_own_key_id = menu_id
        return menu_id

    def _append_own_key_row(self, ai_menu: Any) -> None:
        """The sixth row: the same shared command QUILL Lite has, on the same key.

        Registered and bound here, once, rather than in main_frame_commands.py
        and main_frame_menu_bindings.py, which are at their size budgets.
        """
        import wx

        from quill.core.i18n import _

        menu_id = self._own_key_menu_id()
        ai_menu.Append(
            menu_id, self._menu_label(_("Use My &Own OpenAI Key..."), "tools.hosted_ai_own_key")
        )
        if not getattr(self, "_hosted_ai_own_key_wired", False):
            self._hosted_ai_own_key_wired = True
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.cmd_ai_own_key(), id=menu_id)
            self.commands.try_register(
                "tools.hosted_ai_own_key",
                "Use My Own OpenAI Key",
                self.cmd_ai_own_key,
                self._binding_for("tools.hosted_ai_own_key"),
            )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping["tools.hosted_ai_own_key"] = self._own_key_menu_id()
        return mapping

    def _ai_host(self) -> QuillAiHost:
        host = getattr(self, "_quill_ai_host", None)
        if host is None:
            host = QuillAiHost(self)
            self._quill_ai_host = host
        return host
