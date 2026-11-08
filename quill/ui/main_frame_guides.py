"""Help > Open User Guide and Help > Open GitHub Guide, in QUILL's Help menu.

The rows, the GitHub Guide's command and binding, and the GitHub windows' F1
button are one place here; finding and opening the guides is
:mod:`quill.ui.guide_opener`, which QUILL Lite's Help rows use too. Open User
Guide keeps its command, handler and binding where they were
(``main_frame_commands.py``, ``main_frame.py``, ``main_frame_menu_bindings.py``);
only its menu row moved, so the two guides sit together.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GuidesMenuMixin"]


class GuidesMenuMixin:
    """The two guide rows, mixed into ``MainFrame``."""

    _wx: Any
    frame: Any
    commands: Any

    def _append_guide_rows(self, help_menu: Any) -> None:
        """Open User Guide (Ctrl+Shift+F1), then Open GitHub Guide (no key, Alt+H, I)."""
        from quill.core.i18n import _
        from quill.ui.guide_opener import register_github_guide_help

        wx = self._wx
        host: Any = self
        help_menu.Append(
            host._id_open_user_guide,
            host._menu_label(_("Open User &Guide"), "help.open_user_guide"),
        )
        self.commands.try_register(
            "help.github_guide",
            "Open GitHub Guide",
            self.open_github_guide,
            host._binding_for("help.github_guide"),
        )
        self._id_open_github_guide = wx.NewIdRef()
        help_menu.Append(
            self._id_open_github_guide,
            host._menu_label(_("Open GitHub Gu&ide"), "help.github_guide"),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_github_guide(), id=self._id_open_github_guide
        )
        # F1 in GitHub Items, Explore GitHub and the review window offers it too.
        register_github_guide_help("quill", host._set_status)

    def open_github_guide(self) -> None:
        """Help > Open GitHub Guide: the shipped GitHub Guide, in the browser."""
        from quill.ui.guide_opener import open_guide

        host: Any = self
        open_guide("quill", "github", report=host._set_status)
