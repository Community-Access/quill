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
from pathlib import Path

import wx
import wx.adv

from quill.core.a11y_regions import RegionTracker
from quill.core.commands import CommandRegistry
from quill.core.features import FeatureManager
from quill.core.file_manager import reveal_command
from quill.core.keymap import DEFAULT_KEYMAP, load_keymap
from quill.core.safety.feature_lock import load_feature_locks
from quill.core.settings import load_settings
from quill.platform.announce_engine import AnnouncementEngine
from quill.stability.task_manager import TaskManager
from quill.ui import modal_stack
from quill.ui.announce_commands import AnnounceCommandsMixin
from quill.ui.announce_shim import build_announcement
from quill.ui.app_availability import CommandAvailabilityMixin
from quill.ui.app_shell_components import ComponentDownloadsMixin
from quill.ui.companion_cues import init_app_sound
from quill.ui.dialog_contract import (
    focus_primary_control,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.keybinding_parse import KeybindingParseMixin


class AppShellFrame(
    AnnounceCommandsMixin, ComponentDownloadsMixin, KeybindingParseMixin, CommandAvailabilityMixin
):
    """Mixin: implements the MainFrame host protocol for standalone apps.

    Inheriting :class:`KeybindingParseMixin` gives the companion app frames the
    same three pure keybinding parsers ``MainFrame`` uses, so the shared
    ``GlobalHotkeysMixin`` and ``KeymapEditorMixin`` resolve them via the MRO
    without a second copy.
    """

    def _init_app_shell(
        self, title: str, *, safe_mode: bool = False, size: tuple[int, int] = (480, 360)
    ) -> None:
        self._wx = wx
        self._safe_mode = safe_mode
        self.frame = wx.Frame(None, title=title, size=size)
        # F1 context help, on every shell app from day one: install the wx
        # help provider (SetHelpText stores nothing without one) and register
        # the shared handler the dialog contract binds onto every window it
        # shows; the main frame binds F1 directly since no show path wraps it.
        # An app with an authored purpose catalogue (Quill Radio) re-activates
        # with its own resolver afterwards -- last registration wins.
        from quill.ui import app_context_help

        app_context_help.activate()
        app_context_help.install(self.frame, wx=wx)
        self._app_icon = self._load_app_icon()
        if self._app_icon is not None:
            self.frame.SetIcon(self._app_icon)
        self.frame.CreateStatusBar()
        self.settings = load_settings()
        self.keymap = dict(DEFAULT_KEYMAP) if safe_mode else load_keymap()
        self.commands = CommandRegistry()
        # 11.2: see CommandAvailabilityMixin.
        self.commands.set_availability_probe(self._command_unavailable_reason)
        self._task_manager = TaskManager()
        self._region_tracker = RegionTracker()
        # Same unlock store and kill-switch cache MainFrame consults, so a
        # feature unlocked in QUILL (Help > Redeem Unlock Code...) is unlocked
        # in the companion apps too, and a safety advisory locks it everywhere.
        self.features = FeatureManager.load(persistent=not safe_mode)
        self._feature_locks = load_feature_locks()
        self._menu_id_refs: list[object] = []
        self._announcement_engine = AnnouncementEngine(self.settings.announcement_backend)
        # #1283: the standalone apps braille their announcements too -- the bug
        # was reported against Quill Radio, which lives on this shell.
        self._announcement_engine.set_braille_enabled(
            bool(getattr(self.settings, "announcement_braille", True))
        )
        # The two accessibility commands every shell is supposed to carry.
        # register_announcement_commands() shipped with no caller, so for six
        # companion apps "Repeat Last Announcement" and the Self-Test existed
        # only as dead code -- exactly the "is any of this reaching me?"
        # answer a screen-reader user needs when something goes quiet. Both
        # use try_register, so an app that registers its own copy still wins.
        self.register_announcement_commands()
        # Earcons need a loaded sound pack; only MainFrame ever started one, so
        # every companion app's SoundSink was inert until now (#1302). Safe
        # Mode stays silent here exactly as it does in QUILL.
        if not safe_mode:
            init_app_sound(self.settings)
        self._tray_icon: wx.adv.TaskBarIcon | None = None
        self._status_message = ""
        # Set by an explicit menu/tray "Exit" so the app's close handler quits for
        # real instead of honoring minimize-on-close -- otherwise Exit is swallowed
        # straight back into the tray and the app can never be closed (#1193).
        self._exit_requested = False
        # Guards against a second close (e.g. a rapid second Alt+F4) stacking a
        # second confirm dialog on top of the first -- see handle_app_close.
        self._closing_in_progress = False

    # -- MainFrame-mixin host protocol ---------------------------------------

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        """Announce on every channel this app can reach (#1299).

        One change here gives all six companion apps braille, earcons,
        notification recording and the transcript at once -- Quill Radio,
        Cast, Audio Studio, Converter, Weather and Podcasts all share this
        shell, and every injected surface (Command Palette, Table Studio,
        Reveal Codes) reaches it through the same _announce_fn.

        ``sound`` names a :class:`~quill.core.sound_events.SoundEvent` to lead
        with. It defaults to "" because most announcements are prose, but the
        sound channel is useless without it: the companion-app cue ids shipped
        in the catalogue while every announcement here was built with an empty
        event, so ``SoundSink`` returned early and the apps were silent. A cue
        also arrives *before* the words, which is what makes it a confirmation
        rather than an echo.
        """
        self._status_message = message
        self._set_status(message)
        service = self._announce_service()
        if service is None:
            self._announcement_engine.announce(message, force_speech=force)
            return
        service.announce(build_announcement(message, force=force, sound_event=sound))

    def register_announcement_commands(self) -> None:
        """Repeat Last Announcement and the Self-Test, in every app (#1304, #1305).

        Registered on the shell rather than per app so a companion app
        cannot ship without the two commands that answer "what did it
        just say?" and "is any of this reaching me?"
        """
        self.commands.try_register(
            "app.repeat_last_announcement",
            "Repeat Last Announcement",
            self.repeat_last_announcement,
            feature_id="core.accessibility",
        )
        self.commands.try_register(
            "app.announcement_self_test",
            "Announcement Self-Test...",
            self.run_announcement_self_test,
            feature_id="core.accessibility",
        )

    def _announce_service(self):
        """The announcement service for this app, built on first use."""
        service = getattr(self, "_announcement_service", None)
        if service is None:
            from quill.ui.announce_wiring import build_announcement_service

            service = build_announcement_service(self)
            self._announcement_service = service
        return service

    def _set_status(self, message: str) -> None:
        bar = self.frame.GetStatusBar()
        if bar is not None:
            bar.SetStatusText(message)

    def _show_message_box(
        self, message: str, caption: str, style: int | None = None, parent: object = None
    ) -> int:
        if style is None:  # plain OK box like wx.MessageBox; None used to crash
            style = wx.OK | wx.ICON_INFORMATION
        self._region_tracker.enter(caption)
        try:
            return wx.MessageBox(  # MSGBOX-OK: app_shell's own implementation
                message, caption, style, self._dialog_parent(parent)
            )
        finally:
            self._region_tracker.exit(caption)

    def _dialog_parent(self, parent: object = None) -> object:
        """The modal on top, else the frame. Dialogs, not just message boxes:
        a file picker opened from a dialog has the same focus problem."""
        return modal_stack.stack_of(self).parent_for(parent, fallback=self.frame)

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

    def _apply_app_keymap(self, app_id: str) -> None:
        """Merge this app's own menu accelerators in as defaults (in memory).

        App keys, not editor keys: Quill Radio has no bold, so Ctrl+B is
        Browse Stations there while QUILL keeps it for formatting. The rule
        for *which* defaults apply is pure and lives in ``core.keymap``.
        """
        from quill.core.app_keymaps import app_keymap_overrides

        self.keymap.update(app_keymap_overrides(app_id, self.keymap))

    def _menu_label(self, title: str, command_id: str) -> str:
        binding = self._binding_for(command_id)
        # A comma means a chord binding; wx would misparse the text after the
        # tab as a bare accelerator (#612), so chords stay off shell labels.
        if not binding or "," in binding:
            return title
        return f"{title}\t{binding}"

    # -- keymap editing support (Help > Keyboard Shortcuts...) ----------------
    #
    # The Keyboard Shortcuts editor (KeymapEditorMixin) and keymap import/reset
    # call these three the same way MainFrame's KeymapIoMixin does. The apps
    # bake accelerators into their menu-item labels via _menu_label (they use no
    # AcceleratorTable for menus), so re-applying a keymap edit is a menu-bar
    # rebuild plus a global-hotkey reload -- there is nothing else to refresh.

    def _set_keyboard_pack(self, pack_name: str) -> None:
        from quill.core.settings import save_settings

        self.settings.keyboard_pack = pack_name
        save_settings(self.settings)

    def _mark_keyboard_pack_custom(self) -> None:
        from quill.core.keymap import KEYBOARD_PACK_CUSTOM

        if self.settings.keyboard_pack == KEYBOARD_PACK_CUSTOM:
            return
        self._set_keyboard_pack(KEYBOARD_PACK_CUSTOM)

    def _reload_shortcuts_from_keymap(self) -> None:
        """Live-reapply a keymap change: rebuild the menu bar so the baked-in
        accelerator labels refresh, re-sync the app's dynamic status, then
        re-register the system-wide hotkeys. ``_build_menu_bar`` replaces the
        menu bar cleanly (wx deletes the old one) so nothing is duplicated."""
        build = getattr(self, "_build_menu_bar", None)
        if callable(build):
            build()
        refresh = getattr(self, "_refresh_statusbar", None)
        if callable(refresh):
            refresh()
        if hasattr(self, "_reload_global_hotkeys"):
            self._reload_global_hotkeys()

    def _show_modal_dialog(
        self, dialog: object, label: str, *, restore_editor_focus: bool = True
    ) -> int:
        del restore_editor_focus  # no editor in a companion app
        dialog_cls = getattr(self._wx, "Dialog", None)
        if dialog_cls is not None and type(dialog) is dialog_cls:
            focus_primary_control(dialog)
        stack = modal_stack.stack_of(self)
        stack.push(dialog)
        try:
            return show_modal_dialog(
                dialog,
                label,
                enter_region=self._region_tracker.enter,
                exit_region=self._region_tracker.exit,
            )
        finally:
            stack.pop(dialog)

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

    def _exit_application(self) -> None:
        """Quit for real from an explicit menu/tray "Exit".

        Flags the request so the app's EVT_CLOSE handler bypasses
        minimize-on-close (and the accidental-Alt+F4 confirm) -- a deliberate
        Exit must never bounce back into the tray (#1193). Restores the window
        first so any shutdown UI is visible rather than stuck behind the tray.
        """
        self._exit_requested = True
        if self._tray_icon is not None:
            self._restore_from_tray()
        self.frame.Close()

    def handle_app_close(
        self,
        event: object,
        *,
        close_action: str,
        protected: bool,
        confirm: Callable[[], str | None],
        shutdown: Callable[[], None],
    ) -> None:
        """Shared EVT_CLOSE flow for the standalone companion apps (Radio, Cast,
        Studio), so all three share one close path instead of three copies.

        ``close_action`` is the persisted "ask" / "exit" / "minimize" preference;
        ``protected`` says whether there is work worth confirming before losing
        (live playback, a recording, a running background job); ``confirm`` shows
        the app's own confirm dialog and returns "exit", "minimize", or ``None``
        (cancel / keep open); ``shutdown`` runs the app's teardown just before
        the window closes.

        Crucially, ``confirm`` is NEVER called from inside this handler. Showing a
        modal from within an EVT_CLOSE handler is unreliable on wxMSW: notably
        with a screen reader's low-level keyboard hook active, ShowModal can
        return without ever displaying, so the close is silently vetoed and the
        keystroke appears to do nothing (the Quill Radio "Alt+F4 does nothing
        while a station plays" bug). When a confirm is needed we veto and run it
        deferred via CallAfter, then act on the result in ``_run_close_confirm``.
        """
        if not event.CanVeto():
            # An OS log-off / shutdown (or a forced close) cannot be vetoed.
            # Honour it directly: run teardown -- recorder cleanup, resume-marker
            # clear -- then Skip so the window actually closes. Vetoing to
            # minimize or to defer a confirm would be ignored by the OS AND skip
            # shutdown, stranding a stale resume marker and leaking the recorder.
            shutdown()
            event.Skip()
            return
        if getattr(self, "_closing_in_progress", False):
            event.Veto()
            return
        if getattr(self, "_exit_requested", False):
            self._exit_requested = False  # a deliberate Exit bypasses minimize + confirm
            action = "exit"
        else:
            action = close_action
        if action == "ask":
            if not protected:
                action = "exit"  # nothing to protect -> close like a normal window
            else:
                self._closing_in_progress = True
                event.Veto()
                self._wx.CallAfter(self._run_close_confirm, confirm)
                return
        if action == "minimize":
            event.Veto()
            self._send_to_tray()
            return
        shutdown()
        event.Skip()

    def _run_close_confirm(self, confirm: Callable[[], str | None]) -> None:
        """Deferred half of :meth:`handle_app_close`: show the confirm dialog
        OUTSIDE the close handler and act on the choice. Cancel keeps the window
        open; Minimize tucks it to the tray; Exit re-enters the close path
        deliberately (``_exit_requested`` + ``frame.Close()``) so the shared
        shutdown + Skip run there. The guard set when this was scheduled clears
        once the dialog is done -- even if it raises -- so a crash can't wedge the
        app permanently closed."""
        try:
            decision = confirm()
        finally:
            self._closing_in_progress = False
        if decision is None:
            return
        if decision == "minimize":
            self._send_to_tray()
            return
        self._exit_requested = True
        self.frame.Close()

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

    def _append_sibling_app_tray_items(self, menu: wx.Menu, *, exclude: str) -> None:
        """Add 'Open QUILL / Quill Radio / Quill Weather' items so the sibling
        apps are always one click apart -- each opens in its own window and tray.
        ``exclude`` is this app's own key, which is left off the list."""
        from quill.ui.quillville_menu import append_sibling_items

        append_sibling_items(
            menu,
            frame=menu,
            exclude=exclude,
            on_launch=self._launch_sibling,
            retain=self._keep_menu_ids,
        )

    def _launch_sibling(self, key: str) -> None:
        from quill.ui.companion_offer import try_open_or_offer

        try_open_or_offer(self, key)

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
        menu.Bind(wx.EVT_MENU, lambda _e: self._exit_application(), id=exit_id)
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

    #: App-local hotkey id for the show/hide-to-tray toggle (distinct from the
    #: media-key id space above).
    _TRAY_TOGGLE_HOTKEY_ID = 0x7B00

    def _register_tray_hotkey(self, chord: str) -> None:
        """Register a unique system-wide chord that shows this app or hides it to
        the tray, so it is one keystroke away even when another window has focus.
        Best-effort and Windows-only; a chord another app owns stays theirs."""
        if not sys.platform.startswith("win") or not chord:
            return
        from quill.ui.tray_hotkey import parse_hotkey

        parsed = parse_hotkey(wx, chord)
        if parsed is None:
            return
        flags, key_code = parsed
        try:
            if not self.frame.RegisterHotKey(self._TRAY_TOGGLE_HOTKEY_ID, flags, key_code):
                return
        except Exception:  # noqa: BLE001 - a denied chord must never block startup
            return
        self.frame.Bind(
            wx.EVT_HOTKEY, lambda _e: self.toggle_window_to_tray(), id=self._TRAY_TOGGLE_HOTKEY_ID
        )
        self._tray_hotkey_registered = True

    def toggle_window_to_tray(self) -> None:
        """Hide the window to the tray if it is showing, or bring it back if it is
        hidden/minimized (the show/hide global-hotkey action)."""
        frame = self.frame
        if frame.IsShown() and not frame.IsIconized():
            frame.Hide()  # the tray icon keeps the app reachable
            self._announce(f"{frame.GetTitle()} hidden to the tray.")
        else:
            self._restore_from_tray()
            self._announce(f"{frame.GetTitle()} shown.")

    def _unregister_media_keys(self) -> None:
        if getattr(self, "_tray_hotkey_registered", False):
            try:
                self.frame.UnregisterHotKey(self._TRAY_TOGGLE_HOTKEY_ID)
            except Exception:  # noqa: BLE001 - shutdown must never block
                pass
            self._tray_hotkey_registered = False
        for hotkey_id in getattr(self, "_media_key_ids", []):
            try:
                self.frame.UnregisterHotKey(hotkey_id)
            except Exception:  # noqa: BLE001 - shutdown must never block
                pass
        self._media_key_ids = []

    # -- bundled documentation (Help > User Guide / Release Notes / PRD) --------

    def open_app_document(self, candidates: list[Path], *, title: str, cache_name: str) -> None:
        """Open a bundled doc in the system browser: the first *candidates*
        path that exists on disk wins, tried in order. A ``.html`` candidate
        opens directly (the standalone apps' own build ships pre-rendered
        HTML next to the exe, mirroring QUILL's docs-artifact pipeline); a
        ``.md`` candidate is rendered through the same markdown renderer
        QUILL's own ``open_user_guide`` uses and cached under
        ``app_data_dir()/cache_name`` so repeat opens don't re-render.
        Missing entirely (a dev checkout with no sibling doc repo, or a
        stripped-down build) is a quiet announcement, never an error dialog.
        """
        import webbrowser

        path: Path | None = None
        for candidate in candidates:
            try:
                if candidate.is_file():
                    path = candidate
                    break
            except OSError:
                continue
        if path is None:
            self._announce(f"{title} was not found in this build.")
            return
        if path.suffix.lower() == ".html":
            target = path
        else:
            import os

            from quill.core.paths import app_data_dir

            try:
                text = path.read_text(encoding="utf-8")
            except OSError as error:
                self._announce(f"Could not read {title}: {error}")
                return
            from quill.core.browser_preview import render_preview_html

            html_content = render_preview_html(title, text, "markdown")
            target_dir = app_data_dir() / cache_name
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / f"{path.stem}.html"
                temp_path = target.with_suffix(".tmp")
                temp_path.write_text(html_content, encoding="utf-8")
                os.replace(temp_path, target)
            except OSError as error:
                self._announce(f"Could not write {title}: {error}")
                return
        if webbrowser.open(target.as_uri()):
            self._announce(f"Opened {title} in browser")
        else:
            self._announce(f"{title} saved to {target}")

    def _doc_candidates(self, repo_dir_name: str, stem: str) -> list[Path]:
        """Where *stem* (``"userguide"``, ``"release-notes-1.0"``, ``"prd"``)
        might live, in order: a packaged build's own ``docs\\`` next to the exe
        (HTML preferred, Markdown as fallback), this checkout's
        ``standalone/<app>/docs``, then the historical sibling doc repo. The
        in-repo path matters because the standalone apps were consolidated into
        ``standalone/``, so the sibling layout (``D:\\quill-weather`` beside
        ``D:\\QUILL``) no longer exists and a dev run found no docs at all.
        Best-effort: a stem resolving nowhere is a quiet announcement."""
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / "docs" / f"{stem}.html")
            candidates.append(exe_dir / "docs" / f"{stem}.md")
        repo_root = Path(__file__).resolve().parents[2]
        app = repo_dir_name.removeprefix("quill-")  # quill-weather -> weather
        for root in (repo_root / "standalone" / app, repo_root.parent / repo_dir_name):
            candidates.append(root / "docs" / f"{stem}.html")
            candidates.append(root / "docs" / f"{stem}.md")
        return candidates

    # -- report a bug ------------------------------------------------------------

    def report_bad_station(
        self, station: object, *, source_app: str = "", app_version: str = ""
    ) -> None:
        """Report a station that would not play (#1218).

        Composes a station-scoped report (name, source, UUID, stream URL,
        format) and hands it to the normal Report a Bug flow pre-filled, so the
        user does not have to describe the station by hand. Station metadata
        only -- no user or machine details -- so it is safe on the clipboard or
        in a browser issue form.

        ``source_app`` defaults to this app's window title (e.g. "Quill Radio"),
        so shared surfaces can call it without re-stating the product name."""
        from quill.core.radio.bad_station_report import build_bad_station_report

        summary, body = build_bad_station_report(station)
        frame = getattr(self, "frame", None)
        app = source_app or (frame.GetTitle() if frame is not None else "Quill Radio")
        self.report_app_bug(
            source_app=app,
            app_version=app_version,
            prefill_summary=summary,
            prefill_body=body,
        )

    def report_app_bug(
        self,
        *,
        source_app: str,
        app_version: str = "",
        prefill_summary: str = "",
        prefill_body: str = "",
    ) -> None:
        """Report a Bug, same shape as QUILL's: the in-app feedback-hub form
        when a GitHub token is available, else the online support form
        (opened in the browser and copied to the clipboard) -- a missing or
        failing token never leaves the user with no path.

        Reports carry THIS app's identity and version ("Quill Radio 1.0.0"),
        not the underlying quill package version, so triage always knows
        which product the user was actually running.

        ``prefill_summary``/``prefill_body`` (used by Report Bad Station) go
        straight into the online issue form. The in-app feedback-hub dialog
        takes no per-call defaults, so when a body is supplied it is staged on
        the clipboard and the user is told to paste it into the description."""
        from quill.core.feedback_token import github_token_present

        version = f"{source_app} {app_version}" if app_version else source_app
        if not github_token_present():
            self._report_app_bug_online(
                source_app,
                app_version,
                "Direct bug reporting isn't set up in this build. You can still "
                "file the report on the online support form.",
                prefill_summary=prefill_summary,
                prefill_body=prefill_body,
            )
            return
        if prefill_body:
            self._copy_to_clipboard(prefill_body)
            self._announce(
                "The station's details are on your clipboard. Paste them into the "
                "description with Control V, then submit."
            )
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
            try:
                result = self._show_modal_dialog(dialog, "Report an Issue")
            finally:
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

    def _copy_to_clipboard(self, text: str) -> bool:
        """Best-effort copy; a clipboard we can't open is never fatal.

        Returns True when the text reached the clipboard. #1282: this used to
        return None while ``MainFrame._copy_to_clipboard`` returned a bool, and
        the shared radio mixin branches on that value -- so in the standalone
        apps a copy that actually worked announced "Could not copy to the
        clipboard." Same contract in both hosts now.
        """
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                finally:
                    wx.TheClipboard.Close()
                return True
        except Exception:  # noqa: BLE001 - clipboard failures must not strand the user
            pass
        return False

    def _report_app_bug_online(
        self,
        source_app: str,
        app_version: str,
        reason: str,
        *,
        prefill_summary: str = "",
        prefill_body: str = "",
    ) -> None:
        import webbrowser

        from quill.core.diagnostics import build_support_issue_url, collect_environment_info

        issue_url = build_support_issue_url(
            {"summary": prefill_summary or f"Bug report: {source_app}", "body": prefill_body},
            source_app=source_app,
            version=app_version or "0.0.0",
            platform_label=str(collect_environment_info()["platform"]),
        )
        opened = False
        try:
            opened = bool(webbrowser.open(issue_url))
        except Exception:  # noqa: BLE001 - a browser failure falls back to the clipboard
            opened = False
        self._copy_to_clipboard(issue_url)
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

        # binding_for: a companion app registers most commands with no binding,
        # so without it the palette listed every command with no keystroke.
        dialog = CommandPaletteDialog(
            self.frame,
            self.commands,
            self.features,
            announce_fn=self._announce,
            binding_for=self._binding_for,
        )
        dialog.show_modal_and_run()

    # -- per-app update check (Help > Check for Updates...) ------------------

    def _running_portable_build(self) -> bool:
        """True when this is the extracted portable bundle, not an install.

        Asked of the *app's* folder, not of ``sys.executable``: on the shared
        runtime that is QuillVilleRuntime.exe in %LOCALAPPDATA%, which has no
        uninstaller beside it, so every installed listener answered True and
        was offered the portable .zip on every update (#1100; reported again
        2026-08-16). See :mod:`quill.core.install_edition`.
        """
        from quill.core.install_edition import PORTABLE, detect

        return detect() == PORTABLE

    def check_for_app_updates(
        self,
        *,
        repo_slug: str,
        current_version: str,
        silent_no_update: bool = False,
        app_key: str = "",
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
        from quill.core.updates import fetch_app_releases, fetch_releases, is_newer_version

        api_url = f"https://api.github.com/repos/{repo_slug}/releases"
        if not silent_no_update:
            self._announce("Checking for updates")
        prefer_portable = self._running_portable_build()
        # When an app_key is given the apps share one repo (Community-Access/quill)
        # and each resolves ITS OWN release asset (Quill-Radio-*, Quill-Weather-*,
        # ...) so every QuillVille app updates independently. Without it, fall back
        # to the legacy per-repo, platform-suffix pick.
        app_prefix = ""
        if app_key:
            from quill.core.companion_install import ASSET_PREFIX

            app_prefix = ASSET_PREFIX.get(app_key, "")

        def _fetch(**_kw: object) -> object:
            # Absorb the task manager's injected kwargs (cancellation_token, ...).
            if app_prefix:
                return fetch_app_releases(app_prefix, api_url, prefer_portable=prefer_portable)
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
            download_release_asset(
                url,
                target,
                progress=_progress,
                expected_sha256=str(getattr(release, "download_digest", "") or ""),
            )

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
        applyable = str(target).lower().endswith((
            ".exe",
            ".msi",
            ".zip",
        )) and sys.platform.startswith("win")
        if applyable:
            action_line = (
                "Select 'Install and restart now' to update and relaunch "
                "automatically -- your settings and data are kept -- or "
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
        if applyable:
            apply_btn = wx.Button(dialog, wx.ID_OK, label="Install and restart now")
            apply_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
            apply_btn.SetDefault()
            buttons.Add(apply_btn, 0)
        else:
            close_btn.SetDefault()
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        dialog.SetSizer(sizer)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.CentreOnParent()
        result = self._show_modal_dialog(dialog, "Update downloaded")
        dialog.Destroy()
        if result == wx.ID_OPEN:
            subprocess.Popen(reveal_command(target))  # noqa: S603 - shared, tested argv
            return
        if result == wx.ID_OK and applyable:
            self._apply_update_and_restart(release, Path(str(target)))

    def _apply_update_and_restart(self, release: object, target: Path) -> None:
        """Apply the downloaded update and relaunch (one-click). On any failure
        the app stays open and the user can still Open folder to update by hand."""
        from quill.core.paths import app_data_dir
        from quill.ui.update_apply import apply_update_and_restart

        if apply_update_and_restart(
            target=target,
            portable=self._running_portable_build(),
            version=str(getattr(release, "version", "")),
            app_data_dir=app_data_dir(),
            announce=self._announce,
            show_error=lambda msg: self._show_message_box(msg, "Update", wx.ICON_ERROR | wx.OK),
        ):
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
