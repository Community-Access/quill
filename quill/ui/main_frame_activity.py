"""QUILL's side of Activity and Repeat Last Result (qc.md F-10).

The window and the result model are shared (:mod:`quill.ui.activity_window`,
:mod:`quill.core.activity`); this adapter only gives them QUILL's Help menu
rows, its keys (F9 and Shift+F9, the same in every QuillVille app) and its
command registry. Registered and bound here rather than in
main_frame_commands.py / main_frame_menu_bindings.py, which are at their
GATE-11 budgets -- the same shape as the hosted-AI adapter.
"""

from __future__ import annotations

from typing import Any

from quill.ui.activity_window import ActivityMixin


class MainFrameActivityMixin(ActivityMixin):
    """Help > Activity... and Help > Repeat Last Result, on QUILL's frame."""

    def _activity_menu_ids(self) -> tuple[Any, Any]:
        ids = getattr(self, "_activity_ids", None)
        if ids is None:
            import wx

            ids = (wx.NewIdRef(), wx.NewIdRef())
            self._activity_ids = ids
        return ids

    def _append_activity_rows(self, help_menu: Any) -> None:
        """The two rows, beside Status Page: what happened, and say it again."""
        import wx

        from quill.core.i18n import _

        activity_id, repeat_id = self._activity_menu_ids()
        help_menu.Append(
            activity_id,
            self._menu_label(_("Activit&y..."), "app.activity"),  # type: ignore[attr-defined]
        )
        help_menu.Append(
            repeat_id,
            self._menu_label(_("Repeat Last Res&ult"), "app.repeat_last_result"),  # type: ignore[attr-defined]
        )
        if not getattr(self, "_activity_wired", False):
            self._activity_wired = True
            frame: Any = self.frame  # type: ignore[attr-defined]
            frame.Bind(wx.EVT_MENU, lambda _e: self.open_activity(), id=activity_id)
            frame.Bind(wx.EVT_MENU, lambda _e: self.repeat_last_result(), id=repeat_id)
            self._register_activity_commands()
            # qc.md F-01: QUILL's settings writes report their outcome here.
            # Installed with the menu because that is the one hook every
            # MainFrame runs exactly once, and main_frame.py is at budget.
            from quill.ui.persistence_reporting import install

            self._stop_write_reports = install(self)

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        activity_id, repeat_id = self._activity_menu_ids()
        mapping["app.activity"] = activity_id
        mapping["app.repeat_last_result"] = repeat_id
        return mapping


__all__ = ["MainFrameActivityMixin"]
