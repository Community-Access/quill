"""Shared shell for standalone companion apps (Quill Radio, Quill Cast, ...).

Each companion app is a small top-level ``wx.Frame`` that runs on its own,
outside ``MainFrame``, but reuses the exact same feature mixins QUILL itself
uses (``RadioMixin``, ``PodcastsMixin``, ...) instead of reimplementing menu
or tray logic. Those mixins only ever touch a small, fixed set of attributes
on their host (``self.frame``, ``self._wx``, ``self._safe_mode``,
``self._task_manager``, ``self._announce``, ``self._show_message_box``,
``self._set_status``, ``self.settings``, ``self.commands``,
``self._binding_for``, ``self._refresh_statusbar``) -- this class supplies
that same protocol, so ``class RadioAppFrame(AppShellFrame, RadioMixin)``
gets the whole feature (menus, commands, tray submenu, recording, favorites)
for free. See docs/planning/apps.md for the design rationale.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

import wx
import wx.adv

from quill.core.a11y_regions import RegionTracker
from quill.core.commands import CommandRegistry
from quill.core.features import FeatureManager
from quill.core.keymap import DEFAULT_KEYMAP, load_keymap
from quill.core.safety.feature_lock import load_feature_locks
from quill.core.settings import load_settings
from quill.platform.announce_engine import AnnouncementEngine
from quill.stability.task_manager import TaskManager
from quill.ui.dialog_contract import focus_primary_control, show_modal_dialog


class AppShellFrame:
    """Mixin: implements the MainFrame host protocol for standalone apps."""

    def _init_app_shell(
        self, title: str, *, safe_mode: bool = False, size: tuple[int, int] = (480, 360)
    ) -> None:
        self._wx = wx
        self._safe_mode = safe_mode
        self.frame = wx.Frame(None, title=title, size=size)
        self.frame.CreateStatusBar()
        self.settings = load_settings()
        self.keymap = dict(DEFAULT_KEYMAP) if safe_mode else load_keymap()
        self.commands = CommandRegistry()
        self._task_manager = TaskManager()
        self._region_tracker = RegionTracker()
        # Same unlock store and kill-switch cache MainFrame consults, so a
        # feature unlocked in QUILL (Help > Redeem Unlock Code...) is unlocked
        # in the companion apps too, and a safety advisory locks it everywhere.
        self.features = FeatureManager.load(persistent=not safe_mode)
        self._feature_locks = load_feature_locks()
        self._announcement_engine = AnnouncementEngine(self.settings.announcement_backend)
        self._tray_icon: wx.adv.TaskBarIcon | None = None
        self._status_message = ""

    # -- MainFrame-mixin host protocol ---------------------------------------

    def _announce(self, message: str, *, force: bool = False) -> None:
        self._status_message = message
        self._set_status(message)
        self._announcement_engine.announce(message, force_speech=force)

    def _set_status(self, message: str) -> None:
        bar = self.frame.GetStatusBar()
        if bar is not None:
            bar.SetStatusText(message)

    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        self._region_tracker.enter(caption)
        try:
            return wx.MessageBox(  # MSGBOX-OK: app_shell's own implementation
                message, caption, style, self.frame
            )
        finally:
            self._region_tracker.exit(caption)

    def _binding_for(self, command_id: str) -> str | None:
        binding = self.keymap.get(command_id)
        if binding is None:
            return DEFAULT_KEYMAP.get(command_id)
        cleaned = binding.strip()
        return cleaned or None

    def _refresh_statusbar(self) -> None:
        """Subclasses override to compose their app's own status text."""

    def _feature_enabled(self, feature_id: str) -> bool:
        locks = getattr(self, "_feature_locks", None)
        if locks is not None and locks.is_locked(feature_id):
            return False
        features = getattr(self, "features", None)
        return True if features is None else features.is_enabled(feature_id)

    def _menu_label(self, title: str, command_id: str) -> str:
        binding = self._binding_for(command_id)
        # A comma means a chord binding; wx would misparse the text after the
        # tab as a bare accelerator (#612), so chords stay off shell labels.
        if not binding or "," in binding:
            return title
        return f"{title}\t{binding}"

    def _show_modal_dialog(
        self, dialog: object, label: str, *, restore_editor_focus: bool = True
    ) -> int:
        del restore_editor_focus  # no editor in a companion app
        dialog_cls = getattr(self._wx, "Dialog", None)
        if dialog_cls is not None and type(dialog) is dialog_cls:
            focus_primary_control(dialog)
        return show_modal_dialog(
            dialog,
            label,
            enter_region=self._region_tracker.enter,
            exit_region=self._region_tracker.exit,
        )

    # -- system tray (mirrors MainFrame._ensure_tray_icon) -------------------

    def _ensure_tray_icon(self, build_menu: Callable[[wx.Menu], None], *, tooltip: str) -> None:
        if self._tray_icon is not None:
            return
        # Same limitation MainFrame documents: wx.adv.TaskBarIcon produces a
        # Dock tile on macOS, not a menu-bar extra, so there is no notification
        # -area tray to add there. Skip quietly rather than misrepresent it.
        if sys.platform == "darwin":
            return
        taskbar_icon = wx.adv.TaskBarIcon()
        icon = wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
        taskbar_icon.SetIcon(icon, tooltip)
        taskbar_icon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, lambda _e: self._restore_from_tray())
        taskbar_icon.Bind(
            wx.adv.EVT_TASKBAR_RIGHT_UP, lambda _e: self._on_tray_right_click(build_menu)
        )
        self._tray_icon = taskbar_icon

    def _remove_tray_icon(self) -> None:
        if self._tray_icon is None:
            return
        self._tray_icon.RemoveIcon()
        self._tray_icon.Destroy()
        self._tray_icon = None

    def _restore_from_tray(self) -> None:
        self.frame.Show()
        self.frame.Iconize(False)
        self.frame.Raise()

    def _on_tray_right_click(self, build_menu: Callable[[wx.Menu], None]) -> None:
        if self._tray_icon is None:
            return
        title = self.frame.GetTitle()
        menu = wx.Menu()
        show_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(show_id, f"Show {title}")
        menu.Bind(wx.EVT_MENU, lambda _e: self._restore_from_tray(), id=show_id)
        menu.AppendSeparator()
        build_menu(menu)
        menu.AppendSeparator()
        menu.Append(exit_id, f"Exit {title}")
        menu.Bind(wx.EVT_MENU, lambda _e: self.frame.Close(), id=exit_id)
        self._tray_icon.PopupMenu(menu)
        menu.Destroy()

    # -- basic per-app update check (Help > Check for Updates...) ------------

    def check_for_app_updates(self, *, repo_slug: str, current_version: str) -> None:
        """Deliberately basic: newest stable GitHub release for this app's own
        repo vs the running version, then offer to open the download page in
        the browser. The full QUILL updater (signed manifest, in-place
        download, portable swaps) stays in QUILL itself."""
        from quill.core.updates import fetch_releases, is_newer_version

        api_url = f"https://api.github.com/repos/{repo_slug}/releases"
        self._announce("Checking for updates")

        def _fetch() -> object:
            return fetch_releases(api_url)

        def _report(_name: str, releases: object) -> None:
            def _show() -> None:
                stable = [r for r in releases if not r.prerelease]
                newest = stable[0] if stable else None
                if newest is None or not is_newer_version(current_version, newest.version):
                    self._announce(f"You are up to date ({current_version}).")
                    return
                title = self.frame.GetTitle()
                answer = self._show_message_box(
                    f"{title} {newest.version} is available (you have "
                    f"{current_version}).\n\nOpen the download page in your browser?",
                    "Update Available",
                    wx.ICON_INFORMATION | wx.YES_NO,
                )
                if answer in (wx.YES, wx.ID_YES):
                    import webbrowser

                    webbrowser.open(newest.download_url)

            wx.CallAfter(_show)

        def _failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(
                self._show_message_box,
                f"Could not check for updates: {error}",
                "Check for Updates",
                wx.ICON_ERROR | wx.OK,
            )

        self._task_manager.submit(
            "app-update-check", _fetch, on_success=_report, on_failure=_failed
        )

    # -- calling back into full QUILL ----------------------------------------

    def open_in_quill(self, *paths: str) -> None:
        """Launch a full Quill process (v1: always a new process rather than
        focusing an existing one -- see docs/planning/apps.md for the
        follow-up IPC-based version)."""
        command = (
            [sys.executable, *paths]
            if getattr(sys, "frozen", False)
            else [sys.executable, "-m", "quill", *paths]
        )
        try:
            # A detached, independent GUI process, not a monitored tool
            # invocation -- run_subprocess_safely blocks on a timeout, which
            # is the wrong shape for "launch a sibling app and don't wait".
            subprocess.Popen(command, close_fds=True)  # noqa: S603
        except OSError as error:
            self._show_message_box(
                f"Could not start Quill: {error}", "Open in Quill", wx.ICON_ERROR | wx.OK
            )

    # -- lifecycle ------------------------------------------------------------
    #
    # No default EVT_CLOSE binding here: each app's own close handler already
    # needs to shut down its feature-specific controllers (player, recorder,
    # scheduler, ...) before exit, and calls self._remove_tray_icon() itself
    # as part of that -- see e.g. quill/apps/radio.py's _on_radio_app_close.
