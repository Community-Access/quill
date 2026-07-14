"""Manage a folder's podcast feed: every master an episode, regenerated on demand.

Opened from the Publish dialog. The show settings (title, author, description,
media URL base, feed URL, cover URL) and per-episode titles/descriptions
persist in ``<folder>/.quill/feed.json`` (via ``core.publish.feed_folder``),
so after every new build one button rewrites ``feed.rss`` with all episodes.
Everything is local file IO; uploading stays the SFTP destination's job.
Unavailable in Safe Mode along with the rest of publishing.
"""

from __future__ import annotations

from pathlib import Path

import wx

from quill.core.i18n import _
from quill.core.publish.feed_folder import (
    FeedFolderConfig,
    discover_masters,
    load_feed_config,
    save_feed_config,
    write_folder_feed,
    write_show_notes,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box


class FolderFeedDialog(wx.Dialog):
    """The whole show from one folder: settings, episodes, feed, show notes."""

    def __init__(self, parent: wx.Window, folder: Path) -> None:
        super().__init__(
            parent,
            title=str(_("Folder Podcast Feed")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.folder_feed",
        )
        self._folder = folder
        self._config: FeedFolderConfig = load_feed_config(folder)
        self._masters: list[Path] = discover_masters(folder)

        root = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self,
            label=_("Podcast feed for {folder} ({count} episode(s) found)").format(
                folder=folder.name, count=len(self._masters)
            ),
            name="audio_studio.folder_feed_heading",
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        root.Add(heading, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1, 1)
        self._title = self._field(grid, _("Show ti&tle:"), self._config.title or folder.name)
        self._author = self._field(grid, _("&Author:"), self._config.author)
        self._description = self._field(grid, _("Show &description:"), self._config.description)
        self._media_base = self._field(
            grid, _("&Media URL base (where the audio will live):"), self._config.media_base
        )
        self._feed_url = self._field(grid, _("&Feed URL (optional):"), self._config.feed_url)
        self._cover_url = self._field(
            grid, _("Cover image &URL (optional):"), self._config.cover_url
        )
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        root.Add(
            wx.StaticText(self, label=_("&Episodes (oldest first = episode 1):")),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self._episode_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self._episode_list.SetName(_("Episodes"))
        self._episode_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_pick_episode())
        root.Add(self._episode_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        ep_grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        ep_grid.AddGrowableCol(1, 1)
        self._ep_title = self._field(ep_grid, _("Episode t&itle (blank = from the file's tags):"))
        self._ep_description = self._field(ep_grid, _("Episode descri&ption:"))
        root.Add(ep_grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        apply_btn = wx.Button(self, label=_("App&ly to selected episode"))
        apply_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_apply_episode())
        root.Add(apply_btn, 0, wx.LEFT | wx.TOP, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        feed_btn = wx.Button(self, label=_("&Write feed.rss now"))
        feed_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_write_feed())
        notes_btn = wx.Button(self, label=_("Write show &notes page"))
        notes_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_write_notes())
        close_btn = wx.Button(self, wx.ID_CANCEL, label=_("Close"))
        btn_row.Add(feed_btn, 0, wx.RIGHT, 6)
        btn_row.Add(notes_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self._refresh_episode_list()
        if self._masters:
            self._episode_list.SetSelection(0)
            self._on_pick_episode()

        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)
        self.SetMinSize(wx.Size(680, 560))
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()

    # -- helpers -----------------------------------------------------------------

    def _field(self, grid: wx.FlexGridSizer, label: str, value: str = "") -> wx.TextCtrl:
        grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.TextCtrl(self, value=value)
        ctrl.SetName(label.replace("&", "").rstrip(":"))
        grid.Add(ctrl, 0, wx.EXPAND)
        return ctrl

    def collect_config(self) -> FeedFolderConfig:
        """The show settings as currently typed (episode overrides included)."""
        self._config.title = self._title.GetValue().strip()
        self._config.author = self._author.GetValue().strip()
        self._config.description = self._description.GetValue().strip()
        self._config.media_base = self._media_base.GetValue().strip()
        self._config.feed_url = self._feed_url.GetValue().strip()
        self._config.cover_url = self._cover_url.GetValue().strip()
        return self._config

    def _refresh_episode_list(self) -> None:
        rows: list[str] = []
        for index, path in enumerate(self._masters, start=1):
            override = self._config.episodes.get(path.name)
            described = bool(override is not None and override.description)
            label = _("{n}. {name}").format(n=index, name=path.name)
            if override is not None and override.title:
                label += f" — {override.title}"
            if described:
                label += " " + str(_("(described)"))
            rows.append(label)
        selection = self._episode_list.GetSelection()
        self._episode_list.Set(rows)
        if 0 <= selection < len(rows):
            self._episode_list.SetSelection(selection)

    def _selected_master(self) -> Path | None:
        idx = self._episode_list.GetSelection()
        if not (0 <= idx < len(self._masters)):
            return None
        return self._masters[idx]

    def _on_pick_episode(self) -> None:
        master = self._selected_master()
        if master is None:
            return
        override = self._config.episodes.get(master.name)
        self._ep_title.SetValue(override.title if override is not None else "")
        self._ep_description.SetValue(override.description if override is not None else "")

    def _on_apply_episode(self) -> None:
        master = self._selected_master()
        if master is None:
            return
        episode = self._config.episode(master.name)
        episode.title = self._ep_title.GetValue().strip()
        episode.description = self._ep_description.GetValue().strip()
        self._refresh_episode_list()
        self._save()

    def _save(self) -> None:
        try:
            save_feed_config(self._folder, self.collect_config())
        except OSError:
            pass  # a read-only folder still gets its one-off feed written below

    def _on_write_feed(self) -> None:
        config = self.collect_config()
        if not config.media_base:
            self._message(
                _("Give the media URL base first — the public address where the audio will live."),
                error=True,
            )
            return
        self._save()
        try:
            written, count = write_folder_feed(self._folder, config)
        except (OSError, ValueError) as exc:
            self._message(str(exc), error=True)
            return
        self._message(
            _(
                "Wrote {name} with {count} episode(s). Upload it (and the audio)"
                " to your server; subscribers see every episode."
            ).format(name=written.name, count=count)
        )

    def _on_write_notes(self) -> None:
        self._save()
        try:
            written = write_show_notes(self._folder, self.collect_config())
        except OSError as exc:
            self._message(str(exc), error=True)
            return
        self._message(_("Wrote {name} next to the feed.").format(name=written.name))

    def _message(self, message: str, *, error: bool = False) -> None:
        show_message_box(
            str(message),
            str(_("Folder Podcast Feed")),
            wx.OK | (wx.ICON_ERROR if error else wx.ICON_INFORMATION),
            self,
        )
