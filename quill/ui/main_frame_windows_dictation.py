"""QUILL's half of Windows Dictation: the hooks and the wiring, and no commands.

Windows Dictation was designed for QUILL Lite, and the family rule is that the
small editor is never ahead of the big one -- a feature nobody has seen in QUILL
is one nobody files a bug about missing. So the commands live in
:mod:`quill.ui.windows_dictation_commands`, QUILL Lite mixes them in directly,
and QUILL reaches the same two commands on the same two chords through this
adapter.

It sits beside QUILL's own Locked Dictation (Ctrl+F9, offline Whisper) rather
than replacing it, and it is mixed in *through* that feature's mixin
(:class:`~quill.ui.main_frame_dictation_hotkeys.DictationHotkeysMixin`), which
is where QUILL's dictation lives. The two answer different needs: Locked
Dictation records a passage and transcribes it with a model you download;
Windows Dictation needs nothing downloaded and writes each phrase as you pause.

Two kinds of method here. The hooks map each question the shared module asks
onto QUILL's own vocabulary. The wiring -- the menu rows, their ids, the command
registration -- is here rather than in ``main_frame_menu.py`` and
``main_frame_commands.py`` because those are at their size budgets (GATE-11),
and a feature's wiring in one small file is easier to read than spread across
four large ones. If this class ever grows a *command* of its own, the capability
has forked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.windows_dictation_commands import WindowsDictationMixin

__all__ = ["WindowsDictationCommandsMixin"]

_TOGGLE = "tools.windows_dictation_toggle"
_SETTINGS = "tools.windows_dictation_settings"


class WindowsDictationCommandsMixin(WindowsDictationMixin):
    """The shared Windows Dictation commands, wired to QUILL's frame and editor."""

    # -- hooks ------------------------------------------------------------ #

    def _dictation_control(self):  # noqa: ANN201 - the active tab's editor
        return self.editor

    def _dictation_parent(self):  # noqa: ANN201 - QUILL's MainFrame owns a frame
        return self.frame

    def _dictation_settings(self) -> Any:
        return self.settings

    def _dictation_save_settings(self) -> None:
        from quill.core.settings import save_settings

        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - the choice still holds for this session
            pass

    def _dictation_say(self, text: str) -> None:
        # Forced past the verbosity gate: every sentence dictation speaks is
        # either something the user asked to hear read back or a failure.
        self._announce(text, force=True)

    def _dictation_status(self, text: str) -> None:
        self._set_status_quiet(text)

    def _dictation_cue(self, event: str) -> None:
        self._play_speech_sound(event)

    def _dictation_run_modal(self, dialog: Any, label: str) -> int:
        return int(self._show_modal_dialog(dialog, label))

    def _dictation_top_window(self):  # noqa: ANN201 - QUILL's one top-level frame
        return self.frame

    def _dictation_current_host(self) -> Any:
        return self

    def _dictation_profile_path(self) -> Path:
        """QUILL's own ``dictation.md`` -- the one Locked Dictation reads too, so
        one set of words serves both kinds of dictation."""
        from quill.core.speech.dictation_profile import default_profile_path

        return default_profile_path()

    def _dictation_open_file(self, path: Path) -> None:
        self.open_file(path)

    # -- wiring ----------------------------------------------------------- #

    def _windows_dictation_ids(self) -> tuple[Any, Any]:
        """The two menu ids, made once: a menu rebuild must reuse them, because
        the bindings were made against the first pair."""
        ids = getattr(self, "_windows_dictation_menu_ids", None)
        if ids is None:
            import wx

            ids = (wx.NewIdRef(), wx.NewIdRef())
            self._windows_dictation_menu_ids = ids
        return ids

    def _append_windows_dictation_menu(self, speech_menu: Any) -> None:
        """Tools > Speech > Live Dictation. Its own submenu beside Locked
        Dictation, because the two are different engines and a row that did not
        say which would be a guess."""
        import wx

        from quill.core.i18n import _

        toggle_id, settings_id = self._windows_dictation_ids()
        menu = wx.Menu()
        menu.Append(toggle_id, self._menu_label(_("Start or Stop &Dictation"), _TOGGLE))
        menu.Append(settings_id, self._menu_label(_("Dictation &Settings..."), _SETTINGS))
        speech_menu.AppendSubMenu(menu, _("L&ive Dictation"))

    def _bind_windows_dictation_menu(self) -> None:
        import wx

        toggle_id, settings_id = self._windows_dictation_ids()
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.cmd_toggle_dictation(), id=toggle_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.cmd_dictation_settings(), id=settings_id)
        # And follow the frame's activation, for the wake phrase.
        self._dictation_install()

    def _register_windows_dictation_commands(self) -> None:
        self.commands.try_register(
            _TOGGLE,
            "Start or Stop Live Dictation",
            self.cmd_toggle_dictation,
            self._binding_for(_TOGGLE),
        )
        self.commands.try_register(
            _SETTINGS,
            "Live Dictation Settings",
            self.cmd_dictation_settings,
            self._binding_for(_SETTINGS),
        )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        toggle_id, settings_id = self._windows_dictation_ids()
        mapping[_TOGGLE] = toggle_id
        mapping[_SETTINGS] = settings_id
        return mapping
