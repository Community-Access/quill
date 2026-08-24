"""Opening the podcast dialogs (Manager, Add, Settings, OPML export).

Split out of ``main_frame_podcasts.py`` under GATE-11. These are the wiring
methods -- construct a dialog with the shared library, player, and callbacks,
show it, and put the result back -- and none of them share state with the
player, the download queue, or the refresh path that module owns.

The Manager gets the most arguments of anything here, and each one is a
policy decision it should not own itself: the Quick Actions order, whether the
Winamp letter keys are live, and where the playing episode's chapter-skip
marks live. Passing them in keeps the dialog free of any opinion about where
preferences are stored.
"""

from __future__ import annotations

from quill.core.podcasts import opml as opml_module

_SAFE_MODE_MESSAGE = "Podcasts are disabled in Safe Mode. Restart QUILL normally to use them."


class PodcastDialogsMixin:
    """Opens the podcast dialogs."""

    def open_podcast_manager(self) -> None:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Podcasts", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        from quill.ui.podcasts.manager_dialog import PodcastManagerDialog

        dialog = PodcastManagerDialog(
            self.frame,
            library=self._podcast_library,
            download_queue=self._podcast_download_queue,
            controller=self._podcast_controller,
            download_root=self._podcast_download_root(),
            safe_mode=self._safe_mode,
            task_manager=self._task_manager,
            announce_cb=self._announce,
            winamp_keys_enabled=lambda: bool(
                getattr(self._podcast_history, "winamp_playback_keys", True)
            ),
            quick_actions=self.podcast_quick_actions(),
            on_library_changed=self._save_podcast_library,
            on_open_add_podcast=self._podcast_open_add_dialog,
            on_open_import_opml=self._podcast_open_import_opml,
            on_export_opml=self._podcast_export_opml,
            on_refresh_feed=self.refresh_podcast_feed,
            on_open_settings=self._podcast_open_settings,
            on_send_show_notes=self._podcast_send_show_notes_to_editor,
            chapter_skip_state=self.podcast_chapter_skip_state,
            # So the transport keys work inside the manager too, not only from
            # the main window's menu bar.
            transport_host=self,
        )
        self._podcast_manager_dialog = dialog
        try:
            dialog.show()
        finally:
            self._podcast_manager_dialog = None
        self._refresh_statusbar()

    def _podcast_send_show_notes_to_editor(self, plain_text: str) -> None:
        self._power_tools_open_text_in_new_buffer(plain_text, "Opened podcast show notes")

    def _podcast_open_settings(self) -> None:
        from quill.ui.podcasts.podcast_settings_dialog import PodcastSettingsDialog

        dialog = PodcastSettingsDialog(
            self.frame, settings=self._podcast_library.settings, announce_cb=self._announce
        )
        updated = dialog.show()
        if updated is None:
            return
        self._podcast_library.settings = updated
        self._save_podcast_library()
        self._announce("Podcast settings saved")

    def _podcast_open_add_dialog(self) -> None:
        from quill.ui.podcasts.add_podcast_dialog import AddPodcastDialog

        dialog = AddPodcastDialog(
            self.frame,
            library=self._podcast_library,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_library_changed=self._save_podcast_library,
            # 11.6: when a feed is already followed, land the cursor on the row
            # the listener already has rather than only refusing.
            on_reveal_show=self._podcast_reveal_show,
        )
        dialog.show()

    def _podcast_reveal_show(self, show_id: str) -> bool:
        """Land the cursor on *show_id* in whichever list is open. True if it did.

        The Podcast Manager first (it is what the Add dialog usually opens
        over), then the app's own library tree. False where neither is up --
        which is honest, and makes the spoken refusal say "Nothing was added"
        instead of promising a move that did not happen.
        """
        manager = getattr(self, "_podcast_manager_dialog", None)
        select = getattr(manager, "select_show", None)
        if callable(select):
            try:
                if bool(select(show_id)):
                    return True
            except Exception:  # noqa: BLE001 - a reveal that fails is not fatal
                pass
        reload_tree = getattr(self, "_reload_library_tree", None)
        if callable(reload_tree):
            try:
                reload_tree(keep_key=("show", show_id))
                return True
            except Exception:  # noqa: BLE001
                return False
        return False

    def _podcast_open_import_opml(self) -> None:
        # AddPodcastDialog already offers Import OPML...; reuse the same
        # dialog so there is one place that owns the file picker + parsing.
        self._podcast_open_add_dialog()

    def podcast_import_opml_file(self, path: object) -> None:
        """Open the bulk-import flow on *path*, already chosen.

        The command-line half of the ``.opml`` association: somebody who
        exported a subscription list from another app double-clicks it, and the
        app opens on the import rather than on an empty library with a menu to
        find. The whole import still runs where it always did, off the UI
        thread -- a real subscription list is thousands of entries.
        """
        from pathlib import Path

        from quill.core.podcasts.opml_cli import describe_opened_file
        from quill.ui.podcasts.opml_import_dialog import OpmlImportDialog

        target = Path(str(path))
        if not target.is_file():
            self._announce(f"That subscription list could not be found: {target.name}")
            return
        self._announce(describe_opened_file(target))
        OpmlImportDialog(
            self.frame,
            library=self._podcast_library,
            path=target,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_library_changed=self._save_podcast_library,
        ).show()

    def _podcast_export_opml(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Export OPML",
            wildcard="OPML files (*.opml)|*.opml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
        text = opml_module.export_opml(self._podcast_library)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as error:
            self._set_status(f"Could not export OPML: {error}")
            return
        self._announce("Exported OPML")
