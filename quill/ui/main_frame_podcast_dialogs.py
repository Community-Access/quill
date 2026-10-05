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

from typing import Any

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
        """A peer window (qc.md Phase 4): made once, raised when asked again."""
        from quill.ui.podcasts.add_podcast_dialog import AddPodcastWindow
        from quill.ui.podcasts.peer_window import open_peer

        def _make(host: Any) -> AddPodcastWindow:
            return AddPodcastWindow(
                host.frame,
                library=host._podcast_library,
                task_manager=host._task_manager,
                safe_mode=host._safe_mode,
                announce_cb=host._announce,
                on_library_changed=host._podcast_library_added_to,
                # 11.6: when a feed is already followed, land the cursor on the
                # row the listener already has rather than only refusing.
                on_reveal_show=host._podcast_reveal_show,
            )

        window = open_peer(self, "_add_podcast_window", _make)
        address = getattr(self, "_clipboard_feed_address", lambda: "")()
        if address:
            import wx

            window.prefill_address(address)  # qc.md section 18 item 8
            wx.CallAfter(window.land_on_prefill)

    def _podcast_library_added_to(self) -> None:
        """Add Podcast followed something. Save, and redraw QUILL's Podcast
        Manager if it is open underneath -- the window stays open now, so the
        Manager no longer waits for it to close before it looks again."""
        self._save_podcast_library()
        refresh = getattr(getattr(self, "_podcast_manager_dialog", None), "refresh_tree", None)
        if callable(refresh):
            refresh()

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
            from quill.ui.podcasts.failure_report import report_failure

            report_failure(self, f"Could not export OPML: {error}", subject="Export OPML")
            return
        from pathlib import Path

        from quill.ui.outcome_report import report_outcome

        count = len(self._podcast_library.shows)
        report_outcome(
            self,
            "Export OPML",
            f"Exported {count} podcast{'' if count == 1 else 's'} to {Path(path).name}.",
            path=path,
        )

    # -- settings dialogs --------------------------------------------------
    #
    # Moved here from main_frame_podcasts.py under GATE-11 (extract, never
    # rebaseline) when the now-playing card arrived. They are what this
    # module is already for: construct a dialog, show it, put the result
    # back, and own no player state.

    def open_podcast_sound_enhancements(self) -> None:
        """Playback > Sound Enhancements...: three EQ bands + a compressor +
        Smart Speed. Edits the currently-playing show's own override if one
        is loaded, otherwise the shared default -- see
        PodcastLibrary.apply_show_override.

        A peer window (qc.md section 6, Phase 4), reviewable while playing:
        Apply puts the values into effect and the window stays open; asked
        for again it is raised and re-read for whatever is playing now."""
        from quill.ui.podcasts.sound_enhance_window import open_sound_enhancements_window

        open_sound_enhancements_window(self)

    def _podcast_apply_sound_enhancements(self, show: Any, result: tuple[Any, ...]) -> None:
        """Save and hear the Sound Enhancements window's values for *show*
        (or the shared default when *show* is None)."""
        bass_db, mid_db, treble_db, compressor_enabled, smart_speed_enabled = result
        if show is not None:
            self._podcast_library.apply_show_override(
                show,
                eq_bass_db=bass_db,
                eq_mid_db=mid_db,
                eq_treble_db=treble_db,
                compressor_enabled=compressor_enabled,
                smart_speed_enabled=smart_speed_enabled,
            )
            self._save_podcast_library()
            target = show.title
        else:
            self._podcast_library.settings.eq_bass_db = bass_db
            self._podcast_library.settings.eq_mid_db = mid_db
            self._podcast_library.settings.eq_treble_db = treble_db
            self._podcast_library.settings.compressor_enabled = compressor_enabled
            self._podcast_library.settings.smart_speed_enabled = smart_speed_enabled
            self._save_podcast_library()
            target = "the shared default"
        self._podcast_controller.set_enhancement(
            bass_db=bass_db,
            mid_db=mid_db,
            treble_db=treble_db,
            compressor_enabled=compressor_enabled,
            smart_speed_enabled=smart_speed_enabled,
        )
        self._announce(
            f"Sound Enhancements for {target}: Bass {bass_db:+.0f}, Mid {mid_db:+.0f}, "
            f"Treble {treble_db:+.0f}"
            + (", Even Out Volume on" if compressor_enabled else "")
            + (", Smart Speed on" if smart_speed_enabled else "")
        )

    def open_podcast_skip_settings(self) -> None:
        """Episode > Skip Settings...: Skip Forward/Back seconds, plus (only
        when a show is loaded) auto-skip intro/outro. Edits the currently
        loaded show's own override if one is loaded, otherwise the shared
        default -- see PodcastLibrary.apply_show_override. Mirrors
        open_podcast_sound_enhancements exactly."""
        from quill.ui.podcasts.skip_settings_dialog import SkipSettingsDialog

        show = self._podcast_enhance_context_show()
        settings = (
            self._podcast_library.effective_settings(show)
            if show
            else self._podcast_library.settings
        )
        dialog = SkipSettingsDialog(
            self.frame,
            skip_forward_seconds=settings.skip_forward_seconds,
            skip_back_seconds=settings.skip_back_seconds,
            auto_skip_intro_seconds=settings.auto_skip_intro_seconds,
            auto_skip_outro_seconds=settings.auto_skip_outro_seconds,
            show_title=show.title if show is not None else None,
            announce_cb=self._announce,
        )
        result = dialog.show()
        if result is None:
            return
        forward_seconds, back_seconds, intro_seconds, outro_seconds = result
        if show is not None:
            self._podcast_library.apply_show_override(
                show,
                skip_forward_seconds=forward_seconds,
                skip_back_seconds=back_seconds,
                auto_skip_intro_seconds=intro_seconds,
                auto_skip_outro_seconds=outro_seconds,
            )
            self._save_podcast_library()
            target = show.title
        else:
            self._podcast_library.settings.skip_forward_seconds = forward_seconds
            self._podcast_library.settings.skip_back_seconds = back_seconds
            self._save_podcast_library()
            target = "the shared default"
        self._announce(
            f"Skip Settings for {target}: forward {forward_seconds}s, back {back_seconds}s"
        )
