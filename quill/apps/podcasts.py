"""QUILL Cast -- Podcasts as a standalone app.

Reuses ``PodcastsMixin`` (the exact same class ``MainFrame`` uses) unchanged:
this module only supplies the menu bar, the tray icon, and the entry point.
See docs/planning/apps.md for why this works without touching the mixin.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin

_TITLE = "QUILL Cast"
_VERSION = "1.0.0"
_REPO = "Community-Access/quill-cast"


class PodcastsAppFrame(AppShellFrame, PodcastsMixin, AdpMixin, UnlockCodesMixin):
    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 360))
        self._init_podcasts()
        self._build_menu_bar()
        self._build_main_panel()
        self._register_podcasts_commands()
        self._register_adp_commands()
        self._register_unlock_code_commands()
        self._ensure_tray_icon(self._build_podcast_tray_menu, tooltip=_TITLE)
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_cast_app_close)

    # -- main panel -------------------------------------------------------------
    #
    # A bare frame with only a menu bar leaves keyboard focus with nowhere to
    # land: Tab does nothing and a screen reader reads an empty client area.
    # The main panel gives the app a real, named, tabbable surface -- the
    # subscribed-shows list takes focus on launch, and Enter on a show opens
    # the full Podcast Manager (where all episode-level work happens).

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        self._now_playing_text = wx.StaticText(panel, label="Podcasts: stopped")
        set_accessible_name(self._now_playing_text, "Now playing")
        root.Add(self._now_playing_text, 0, wx.EXPAND | wx.ALL, 8)

        shows_label = wx.StaticText(panel, label="&Subscribed shows:")
        root.Add(shows_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._shows_list = wx.ListBox(panel)
        set_accessible_name(self._shows_list, "Subscribed shows")
        root.Add(self._shows_list, 1, wx.EXPAND | wx.ALL, 8)
        self._shows_list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.open_podcast_manager())
        self._shows_list.Bind(wx.EVT_KEY_DOWN, self._on_shows_key)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            ("Open &Manager...", lambda _e: self.open_podcast_manager()),
            ("&Add Podcast...", lambda _e: self._podcast_open_add_dialog()),
            ("&Play/Pause", lambda _e: self.podcast_toggle_play_pause()),
            ("&Stop", lambda _e: self.podcast_stop()),
        ):
            button = wx.Button(panel, label=label)
            set_accessible_name(button, label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 8)

        panel.SetSizer(root)
        self._main_panel = panel
        self._reload_shows_list()
        self._shows_list.SetFocus()

    def _on_shows_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.open_podcast_manager()
            return
        event.Skip()

    def _reload_shows_list(self) -> None:
        shows = self._podcast_library.shows
        selected = self._shows_list.GetSelection()
        self._shows_list.Set([show.title or show.feed_url for show in shows])
        if shows:
            self._shows_list.SetSelection(selected if 0 <= selected < len(shows) else 0)

    # -- menu bar -------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        subs_menu = wx.Menu()
        manager_id, add_id, import_id, export_id, settings_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        subs_menu.Append(manager_id, "&Open Podcast Manager...\tCtrl+M")
        subs_menu.Append(add_id, "&Add Podcast...")
        subs_menu.Append(import_id, "&Import OPML...")
        subs_menu.Append(export_id, "&Export OPML...")
        local_id, watched_id, acb_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        subs_menu.Append(local_id, "Add &Local Podcast...")
        subs_menu.Append(watched_id, "Scan &Watched Folders")
        subs_menu.Append(acb_id, "Subscribe to ACB Media &Podcasts")
        subs_menu.AppendSeparator()
        subs_menu.Append(settings_id, "Podcast &Settings...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_podcast_manager(), id=manager_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_add_dialog(), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_import_opml(), id=import_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_export_opml(), id=export_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._podcast_open_settings(), id=settings_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.add_local_podcast(), id=local_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.scan_watched_podcast_folders(), id=watched_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.subscribe_acb_media_podcasts(), id=acb_id)
        menu_bar.Append(subs_menu, "&Subscriptions")

        episode_menu = wx.Menu()
        self._now_playing_item_id = wx.NewIdRef()
        episode_menu.Append(self._now_playing_item_id, "Podcasts: stopped")
        episode_menu.Enable(self._now_playing_item_id, False)
        episode_menu.AppendSeparator()
        play_id, stop_id, next_id, prev_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        episode_menu.Append(play_id, "&Play/Pause\tCtrl+P")
        episode_menu.Append(stop_id, "&Stop")
        episode_menu.Append(next_id, "&Next Chapter")
        episode_menu.Append(prev_id, "P&revious Chapter")
        note_id = wx.NewIdRef()
        episode_menu.Append(note_id, "Add Episode &Note...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_toggle_play_pause(), id=play_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_stop(), id=stop_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_next_chapter(), id=next_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_previous_chapter(), id=prev_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.add_podcast_note(), id=note_id)
        menu_bar.Append(episode_menu, "&Episode")

        downloads_menu = wx.Menu()
        pause_all_id, resume_all_id = wx.NewIdRef(), wx.NewIdRef()
        downloads_menu.Append(pause_all_id, "&Pause All Downloads")
        downloads_menu.Append(resume_all_id, "&Resume All Downloads")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_pause_all_downloads(), id=pause_all_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.podcast_resume_all_downloads(), id=resume_all_id
        )
        menu_bar.Append(downloads_menu, "&Downloads")

        # Unlock-gated: a top-level Audio Description Project menu, absent
        # entirely until future.adp_assistant is unlocked (Help > Redeem
        # Unlock Code..., here or in QUILL -- they share one unlock store).
        adp_menu = self._build_adp_menu()
        if adp_menu is not None:
            menu_bar.Append(adp_menu, "A&udio Description Project")

        help_menu = wx.Menu()
        open_quill_id, redeem_id, updates_id, about_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        help_menu.Append(open_quill_id, "&Open in Quill")
        help_menu.Append(redeem_id, "Redeem &Unlock Code...")
        help_menu.Append(updates_id, "Check for Up&dates...")
        help_menu.AppendSeparator()
        help_menu.Append(about_id, "&About QUILL Cast")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_in_quill(), id=open_quill_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_redeem_unlock_code_dialog(), id=redeem_id)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self.frame.SetMenuBar(menu_bar)

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n"
            "Podcasts from Quill, as a standalone app.\n\n"
            "Runs the same podcast feature code as QUILL itself and shares "
            "its settings, subscriptions, and downloads.\n"
            f"https://github.com/{_REPO}",
            f"About {_TITLE}",
            wx.ICON_INFORMATION | wx.OK,
        )

    # -- show notes: no in-editor buffer standalone, so copy to clipboard ----

    def _podcast_send_show_notes_to_editor(self, plain_text: str) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(plain_text))
            finally:
                wx.TheClipboard.Close()
        self._announce("Show notes copied to clipboard")

    # -- status ---------------------------------------------------------------

    def _refresh_statusbar(self) -> None:
        text = self._podcast_status_text() or "Podcasts: stopped"
        self._set_status(text)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.SetLabel(int(self._now_playing_item_id), text)
        now_playing = getattr(self, "_now_playing_text", None)
        if now_playing is not None:
            now_playing.SetLabel(text)
        if getattr(self, "_shows_list", None) is not None:
            self._reload_shows_list()

    # -- lifecycle --------------------------------------------------------------

    def _on_cast_app_close(self, event: wx.CloseEvent) -> None:
        try:
            self._save_podcast_library()
        except Exception:  # noqa: BLE001 - a failed save must never block exit
            pass
        for action in (
            getattr(self._podcast_controller, "shutdown", None),
            getattr(self._podcast_download_queue, "shutdown", None),
        ):
            if action is None:
                continue
            try:
                action()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                pass
        self._task_manager.shutdown(wait=False)
        self._remove_tray_icon()
        event.Skip()


def main() -> int:
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    app = wx.App()
    frame = PodcastsAppFrame(safe_mode=safe_mode)
    frame.frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
