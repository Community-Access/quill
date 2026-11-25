"""Release-update host adapter for apps with custom main frames."""

from __future__ import annotations

from typing import Any

import wx


class ProductUpdateHost:
    """Give a custom wx frame the same release controls as ``AppShellFrame``."""

    @property
    def frame(self) -> Any:
        return self

    def _announce(self, message: str) -> None:
        self.announcer.say(message)

    def _show_message_box(self, message: str, caption: str, style: int = wx.OK) -> int:
        from quill.ui.dialog_contract import show_message_box

        return show_message_box(message, caption, style, self.frame, announce=self._announce)

    def _show_modal_dialog(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return show_modal_dialog(dialog, label, announce=self._announce)

    def _running_portable_build(self) -> bool:
        from quill.core.install_edition import PORTABLE, detect

        return detect() == PORTABLE

    def _update_app_name(self) -> str:
        return str(self.frame.GetTitle() or "").strip()

    def _ensure_release_task_manager(self) -> Any:
        manager = getattr(self, "_task_manager", None)
        if manager is None:
            from quill.stability.task_manager import TaskManager

            manager = TaskManager()
            self._task_manager = manager
        return manager

    def check_product_updates(self, app_key: str, *, silent_no_update: bool = False) -> None:
        """Run the shared companion update path for one catalogue product."""
        from quill.ui.app_shell import AppShellFrame
        from quill.ui.updates.shell import installed_app_version

        self._ensure_release_task_manager()
        AppShellFrame.check_for_app_updates(
            self,
            repo_slug="Community-Access/quill",
            current_version=installed_app_version(app_key),
            silent_no_update=silent_no_update,
            app_key=app_key,
        )

    def open_product_release_channel(self, app_key: str, check_menu_id: Any) -> None:
        from quill.ui.updates.shell import open_for_shell

        open_for_shell(self, app_key, check_menu_id=check_menu_id)

    def _download_app_update(self, release: object) -> None:
        from quill.core.release_catalog import data_dir
        from quill.ui.update_download import download_and_offer_install

        key = str(self._release_app_key)
        download_and_offer_install(
            self.frame,
            release=release,
            target_dir=data_dir(key) / "updates",
            portable=self._running_portable_build(),
            announce=self._announce,
            show_message_box=self._show_message_box,
            show_modal_dialog=self._show_modal_dialog,
            submit=self._ensure_release_task_manager().submit,
            close_app=self.frame.Close,
        )

    def _shutdown_release_tasks(self) -> None:
        manager = getattr(self, "_task_manager", None)
        if manager is not None:
            manager.shutdown(wait=False)


__all__ = ["ProductUpdateHost"]
