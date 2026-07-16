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
from quill.ui.dialog_contract import (
    focus_primary_control,
    set_accessible_name,
    show_modal_dialog,
)


class AppShellFrame:
    """Mixin: implements the MainFrame host protocol for standalone apps."""

    def _init_app_shell(
        self, title: str, *, safe_mode: bool = False, size: tuple[int, int] = (480, 360)
    ) -> None:
        self._wx = wx
        self._safe_mode = safe_mode
        self.frame = wx.Frame(None, title=title, size=size)
        self._app_icon = self._load_app_icon()
        if self._app_icon is not None:
            self.frame.SetIcon(self._app_icon)
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
        self._menu_id_refs: list[object] = []
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

    def _load_app_icon(self) -> object | None:
        """The frozen exe's own embedded icon (PyInstaller stamps it into
        QuillRadio.exe / QUILLCast.exe), used for the title bar, Alt+Tab,
        and the tray. None in a dev run or off Windows -- callers fall back
        to the stock art."""
        if not getattr(sys, "frozen", False) or not sys.platform.startswith("win"):
            return None
        try:
            icon = wx.Icon(wx.IconLocation(sys.executable, 0))
            return icon if icon.IsOk() else None
        except Exception:  # noqa: BLE001 - a bad icon must never block startup
            return None

    def _keep_menu_ids(self, *refs: object) -> None:
        """Pin wx.NewIdRef objects for the frame's lifetime.

        A NewIdRef reserves its id only while the Python reference lives; menu
        builders that let their id refs go out of scope hand the same numeric
        id to whatever allocates one next (a tray popup, a favorites submenu
        entry), and that item's wxEVT_MENU then also matches the original
        frame binding -- the 'About opens at random' bug. Every menu builder
        passes its id refs here."""
        self._menu_id_refs.extend(refs)

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
        icon = self._app_icon or wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
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

    # -- hardware media keys ---------------------------------------------------

    _MEDIA_KEY_CODES = {
        "play_pause": 0xB3,  # VK_MEDIA_PLAY_PAUSE
        "stop": 0xB2,  # VK_MEDIA_STOP
        "next": 0xB0,  # VK_MEDIA_NEXT_TRACK
        "previous": 0xB1,  # VK_MEDIA_PREV_TRACK
    }

    def _register_media_keys(self, handlers: dict[str, Callable[[], None]]) -> None:
        """Keyboard media keys drive this app even from the tray (Windows).

        RegisterHotKey is system-wide, so while the app runs it owns the
        media keys it registers -- exactly the appliance behavior asked for.
        Keys are released automatically when the frame is destroyed; a key
        another app already grabbed simply stays theirs (registration fails
        quietly rather than fighting over it)."""
        if not sys.platform.startswith("win"):
            return
        self._media_key_ids: list[int] = []
        base = 0x7A00  # arbitrary app-local hotkey-id space
        for offset, (action, handler) in enumerate(sorted(handlers.items())):
            keycode = self._MEDIA_KEY_CODES.get(action)
            if keycode is None:
                continue
            hotkey_id = base + offset
            try:
                if not self.frame.RegisterHotKey(hotkey_id, 0, keycode):
                    continue
            except Exception:  # noqa: BLE001 - a denied key must never block startup
                continue
            self.frame.Bind(wx.EVT_HOTKEY, lambda _e, h=handler: h(), id=hotkey_id)
            self._media_key_ids.append(hotkey_id)

    def _unregister_media_keys(self) -> None:
        for hotkey_id in getattr(self, "_media_key_ids", []):
            try:
                self.frame.UnregisterHotKey(hotkey_id)
            except Exception:  # noqa: BLE001 - shutdown must never block
                pass
        self._media_key_ids = []

    # -- ffmpeg safety net (Help > Get FFmpeg...) --------------------------------

    def download_ffmpeg_component(self) -> None:
        """Recovery path for a missing ffmpeg: the installer and portable zip
        both bundle it, but if it ever goes missing this fetches QUILL's
        verified official build into the shared %APPDATA%\\Quill\\tools\\ffmpeg
        that every app searches. Announced milestones, no dialog to babysit."""
        from quill.core.speech.ffmpeg import ffmpeg_available
        from quill.core.speech.ffmpeg_install import (
            FFmpegInstallError,
            ffmpeg_install_supported,
            install_ffmpeg,
        )

        if self._safe_mode:
            self._announce("Downloading components is disabled in Safe Mode.")
            return
        if ffmpeg_available():
            self._announce("FFmpeg is already installed and working.")
            return
        if not ffmpeg_install_supported():
            self._announce("Automatic FFmpeg download is Windows-only.")
            return
        self._announce("Downloading FFmpeg (about 90 megabytes)...")
        last_milestone = {"value": -1}

        def _progress(fraction: float, _message: str) -> None:
            percent = int(max(0.0, min(1.0, fraction)) * 100)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone in (25, 50, 75):
                last_milestone["value"] = milestone
                wx.CallAfter(self._announce, f"FFmpeg download {milestone} percent")

        def _install(**_kw: object) -> object:
            # QuillTaskManager always passes cancellation_token/operation_id/
            # progress_callback; absorb them (same idiom as MainFrame's tasks).
            return install_ffmpeg(_progress)

        def _done(_name: str, _result: object) -> None:
            wx.CallAfter(self._announce, "FFmpeg is installed. Recording is ready to use.")

        def _failed(_name: str, error: BaseException) -> None:
            message = (
                str(error)
                if isinstance(error, FFmpegInstallError)
                else f"FFmpeg could not be downloaded: {error}"
            )
            wx.CallAfter(self._show_message_box, message, "Get FFmpeg", wx.ICON_ERROR | wx.OK)

        self._task_manager.submit(
            "app-ffmpeg-install", _install, on_success=_done, on_failure=_failed
        )

    # -- report a bug ------------------------------------------------------------

    def report_app_bug(self, *, source_app: str, app_version: str = "") -> None:
        """Report a Bug, same shape as QUILL's: the in-app feedback-hub form
        when a GitHub token is available, else the online support form
        (opened in the browser and copied to the clipboard) -- a missing or
        failing token never leaves the user with no path.

        Reports carry THIS app's identity and version ("Quill Radio 1.0.0"),
        not the underlying quill package version, so triage always knows
        which product the user was actually running."""
        from quill.core.feedback_token import github_token_present

        version = f"{source_app} {app_version}" if app_version else source_app
        if not github_token_present():
            self._report_app_bug_online(
                source_app,
                app_version,
                "Direct bug reporting isn't set up in this build. You can still "
                "file the report on the online support form.",
            )
            return
        try:
            from pathlib import Path

            from feedback_hub import load_schema
            from feedback_hub.wx_dialog import FeedbackDialog

            from quill.core.feedback_token import effective_github_token

            schema_path = Path(__file__).parent.parent / "core" / "schemas" / "feedback.json"
            dialog = FeedbackDialog(
                self.frame,
                schema=load_schema(schema_path),
                app_version=version,
                github_token=effective_github_token(),
            )
            result = self._show_modal_dialog(dialog, "Report an Issue")
            dialog.Destroy()
            if result == wx.ID_OK:
                self._announce("Thanks -- your report was submitted.")
        except Exception:  # noqa: BLE001 - never strand the user without a path
            import logging

            logging.getLogger(__name__).warning("feedback_hub bug report failed", exc_info=True)
            self._report_app_bug_online(
                source_app,
                app_version,
                "The issue form could not be submitted. You can file the report "
                "on the online support form instead.",
            )

    def _report_app_bug_online(self, source_app: str, app_version: str, reason: str) -> None:
        import webbrowser

        from quill.core.diagnostics import build_support_issue_url, collect_environment_info

        issue_url = build_support_issue_url(
            {"summary": f"Bug report: {source_app}", "body": ""},
            source_app=source_app,
            version=app_version or "0.0.0",
            platform_label=str(collect_environment_info()["platform"]),
        )
        opened = False
        try:
            opened = bool(webbrowser.open(issue_url))
        except Exception:  # noqa: BLE001 - a browser failure falls back to the clipboard
            opened = False
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(issue_url))
            finally:
                wx.TheClipboard.Close()
        tail = (
            "Your browser is opening it now; the link is also on your clipboard."
            if opened
            else "The link is on your clipboard -- paste it into your browser."
        )
        message = f"{reason}\n\n{tail}"
        self._announce(message)
        self._show_message_box(message, "Report a Bug", wx.OK | wx.ICON_INFORMATION)

    # -- command palette -------------------------------------------------------

    def open_command_palette(self) -> None:
        """The same Command Palette QUILL has, naturally scoped: a companion
        app's registry holds only its own commands (radio/podcasts, media,
        ADP, unlock codes), so the palette lists exactly this app's features."""
        from quill.ui.palette import CommandPaletteDialog

        dialog = CommandPaletteDialog(
            self.frame, self.commands, self.features, announce_fn=self._announce
        )
        dialog.show_modal_and_run()

    # -- per-app update check (Help > Check for Updates...) ------------------

    def _running_portable_build(self) -> bool:
        """True when this frozen app is the extracted portable folder rather
        than an Inno-installed copy (which always has unins000.exe beside the
        exe). Dev runs report False and get the installer path, harmlessly."""
        if not getattr(sys, "frozen", False):
            return False
        from pathlib import Path

        return not (Path(sys.executable).resolve().parent / "unins000.exe").is_file()

    def check_for_app_updates(
        self, *, repo_slug: str, current_version: str, silent_no_update: bool = False
    ) -> None:
        """The same in-app experience QUILL gives: check this app's own GitHub
        releases, download the installer in-app with spoken progress
        milestones, then offer Install now / Open folder. Only QUILL's extras
        (signed manifest feed, portable zip swaps, version skipping) stay in
        QUILL itself.

        ``silent_no_update`` is for the automatic startup check (mirrors
        MainFrame's ``check_for_updates(silent_no_update=True)``): the
        "Checking..."/"up to date"/error paths stay quiet -- a launch is not
        the place to announce nothing happened -- but a genuine available
        update still shows the same interactive prompt either way, since
        these small apps have no notification-center equivalent to defer to.
        """
        from quill.core.updates import fetch_releases, is_newer_version

        api_url = f"https://api.github.com/repos/{repo_slug}/releases"
        if not silent_no_update:
            self._announce("Checking for updates")
        prefer_portable = self._running_portable_build()

        def _fetch(**_kw: object) -> object:
            # Absorb the task manager's injected kwargs (cancellation_token, ...).
            return fetch_releases(api_url, prefer_portable=prefer_portable)

        def _report(_name: str, releases: object) -> None:
            def _show() -> None:
                stable = [r for r in releases if not r.prerelease]
                newest = stable[0] if stable else None
                if newest is None or not is_newer_version(current_version, newest.version):
                    if not silent_no_update:
                        # A manual check deserves a real dialog, not just a spoken
                        # announcement that's easy to miss over other app noise.
                        self._show_message_box(
                            f"You are up to date ({current_version}).",
                            "Check for Updates",
                            wx.ICON_INFORMATION | wx.OK,
                        )
                    return
                title = self.frame.GetTitle()
                answer = self._show_message_box(
                    f"{title} {newest.version} is available (you have "
                    f"{current_version}).\n\nDownload it now?",
                    "Update Available",
                    wx.ICON_INFORMATION | wx.YES_NO,
                )
                if answer in (wx.YES, wx.ID_YES):
                    self._download_app_update(newest)

            wx.CallAfter(_show)

        def _failed(_name: str, error: BaseException) -> None:
            if silent_no_update:
                return
            wx.CallAfter(
                self._show_message_box,
                f"Could not check for updates: {error}",
                "Check for Updates",
                wx.ICON_ERROR | wx.OK,
            )

        self._task_manager.submit(
            "app-update-check", _fetch, on_success=_report, on_failure=_failed
        )

    def _app_update_check_due(self, last_check: str, *, interval_hours: int = 24) -> bool:
        """True when enough time has passed since the last update check.

        Mirrors ``MainFrame._update_check_due``: throttles only the silent
        startup check so a companion app doesn't hit the network on every
        single launch. Manual checks (Help > Check for Updates) always run.
        """
        from datetime import UTC, datetime, timedelta

        last = last_check.strip()
        if not last:
            return True
        try:
            previous = datetime.fromisoformat(last)
        except ValueError:
            return True
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=UTC)
        return datetime.now(UTC) - previous >= timedelta(hours=interval_hours)

    def _download_app_update(self, release: object) -> None:
        """Download the release asset off-thread to <app data>/updates with
        coarse spoken progress (25/50/75 percent), then offer install actions.
        A release with no downloadable asset falls back to its web page."""
        from quill.core.paths import app_data_dir
        from quill.core.updates import download_release_asset

        url = str(getattr(release, "download_url", "") or "")
        if "/releases/download/" not in url:
            import webbrowser

            if url and webbrowser.open(url):
                self._announce(f"Opened download page for {release.version}")
            else:
                self._announce("No downloadable update asset found.")
            return

        target_dir = app_data_dir() / "updates"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (url.rsplit("/", 1)[-1] or f"update-{release.version}")
        self._announce(f"Downloading update {release.version}")
        last_milestone = {"value": -1}

        def _progress(done: int, total: int) -> None:
            if total <= 0:
                return
            percent = int(done * 100 / total)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone in (25, 50, 75):
                last_milestone["value"] = milestone
                wx.CallAfter(self._announce, f"Update download {milestone} percent")

        def _download(**_kw: object) -> None:
            # Absorb the task manager's injected kwargs (cancellation_token, ...).
            download_release_asset(url, target, progress=_progress)

        def _downloaded(_name: str, _result: object) -> None:
            wx.CallAfter(self._offer_app_update_install, release, target)

        def _failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(
                self._show_message_box,
                f"Update download failed: {error}",
                "Check for Updates",
                wx.ICON_ERROR | wx.OK,
            )

        self._task_manager.submit(
            "app-update-download", _download, on_success=_downloaded, on_failure=_failed
        )

    def _offer_app_update_install(self, release: object, target: object) -> None:
        """Post-download: Install now (closes this app and runs the installer),
        Open folder, or Close -- the same shape as QUILL's own dialog."""
        from quill.ui.dialog_contract import apply_modal_ids

        self._announce(f"Update {release.version} downloaded")
        runnable = str(target).lower().endswith((".exe", ".msi")) and sys.platform.startswith("win")
        if runnable:
            action_line = "Select 'Install now' to close this app and run the installer, or "
        elif str(target).lower().endswith(".zip"):
            action_line = (
                "This is the portable version: close this app, extract the zip "
                "over (or beside) your current folder, and start it again. "
            )
        else:
            action_line = ""
        dialog = wx.Dialog(
            self.frame, title="Update downloaded", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        dialog.SetSize((500, 240))
        sizer = wx.BoxSizer(wx.VERTICAL)
        body = wx.TextCtrl(
            dialog,
            value=(
                f"Update {release.version} downloaded.\n\n"
                f"Saved to: {target}\n\n"
                f"{action_line}Select 'Open folder' to find it."
            ),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            name="update_body",
        )
        set_accessible_name(body, "Update details, read-only")
        sizer.Add(body, 1, wx.EXPAND | wx.ALL, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
        folder_btn = wx.Button(dialog, wx.ID_OPEN, label="Open folder")
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
        folder_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OPEN))
        buttons.Add(close_btn, 0, wx.RIGHT, 6)
        buttons.Add(folder_btn, 0, wx.RIGHT, 6)
        if runnable:
            install_btn = wx.Button(dialog, wx.ID_OK, label="Install now...")
            install_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
            install_btn.SetDefault()
            buttons.Add(install_btn, 0)
        else:
            close_btn.SetDefault()
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        dialog.SetSizer(sizer)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.CentreOnParent()
        result = self._show_modal_dialog(dialog, "Update downloaded")
        dialog.Destroy()
        if result == wx.ID_OPEN:
            subprocess.Popen(["explorer", "/select,", str(target)])  # noqa: S603,S607
            return
        if result == wx.ID_OK and runnable:
            import os

            os.startfile(str(target))  # noqa: S606 - user chose Install now
            self.frame.Close()

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
