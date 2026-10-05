"""Settings for This Podcast: everything one podcast can decide, by category.

Most of what Cast can be told is only meaningful one podcast at a time. "Keep
the newest three ready" is right for a daily news show and wrong for a weekly
three-hour interview; "check hourly" is right for the news show and wasteful for
an archive; "say the podcast's name in every row" is right for a mixed list and
noise in this show's own. A single shared value for any of them would be a value
nobody wants, which is why this window exists -- and why, as of the per-podcast
settings work, it covers seventy-odd settings rather than a dozen.

**The controls are generated from the catalogue**
(``core/podcasts/settings_catalog.py``, built by ``show_settings_panel.py``).
Hand-building seventy controls would have meant seventy chances to forget a
label, a help string or an inherited value, and a seventy-first setting next
month needing all three again.

Four behaviours are worth knowing before reading the code:

* **A category at a time.** Seventy controls in one scroll is not a window
  anybody can use by ear. The Choice at the top picks one of five -- Arrival,
  Playback, Storage, Announcements, Curation -- and the panel below is only ever
  that many controls.
* **Every control shows the value in force**, inherited or not, and its help
  says which level answered. A window that opened on blanks would misreport
  every setting it exists to change.
* **Saving writes only what you changed.** The old window cloned the whole
  settings record, which froze every *other* setting at whatever the shared
  default happened to be that day -- the bug that made changing a shared
  default stop reaching the podcasts that needed it most.
* **Follow is not the same as setting the default.** Where this podcast has an
  opinion, a Follow button beside the control drops it, so the podcast goes
  back to its folder or the shared default rather than being pinned to today's
  value of it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import episode_filter_maintenance as maintenance
from quill.core.podcasts import episode_filters as filters
from quill.core.podcasts import settings_catalog, settings_help
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.settings_types import (
    CATEGORY_LABELS,
    LEVEL_SHOW,
    SettingDef,
)
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.show_settings_panel import (
    SettingControl,
    apply_controls,
    build_control,
    follow_again,
)

__all__ = ["ShowSettingsWindow", "open_show_settings", "per_podcast_settings"]


def per_podcast_settings(category: str) -> tuple[SettingDef, ...]:
    """The rows this window shows for *category*.

    Everything a podcast may set, less what Preferences never shows either
    (``preferences_window.section_of`` answers "" for it): the three legacy
    refresh rows that the refresh schedule replaced. Shown here they read as a
    second way to say when this podcast is checked, beside "Check for new
    episodes", which is the one that answers.
    """
    from quill.ui.podcasts.preferences_window import section_of

    return tuple(
        definition
        for definition in settings_catalog.for_category(category, level=LEVEL_SHOW)
        if section_of(definition)
    )


class ShowSettingsWindow:
    """Edits one podcast's settings -- a peer window (qc.md Phase 4).

    Made once. Save writes what you changed and the window stays open, so a
    setting can be tried and changed again; Close (or Escape) leaves anything
    not saved as it was. Asked for again while it is showing the same podcast
    it is only raised; otherwise it is rebuilt from what is stored, for the
    podcast asked about.
    """

    TITLE = "Settings for"
    MENU_TITLE = "Settin&gs"

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        show: PodcastShow,
        announce_cb: Callable[[str], None] | None = None,
        on_saved: Callable[[], None] | None = None,
        host: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._host = host
        self._body: Any = None
        self.frame = wx.Frame(parent, title="Settings for", size=(660, 760))
        self.frame.SetMinSize((620, 620))
        self.frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.load(library=library, show=show, on_saved=on_saved)
        self.frame.CentreOnParent()

    def load(
        self,
        *,
        library: PodcastLibrary,
        show: PodcastShow,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        """Build the window's contents for *show*, from what is stored."""
        wx = self._wx
        self._library = library
        self._show = show
        self._on_saved = on_saved
        self._changed = False
        self._controls: list[SettingControl] = []
        self._categories = settings_catalog.categories_with_settings()
        self._title = f"Settings for {show.title}"

        self.frame.SetTitle(self._title)
        self.TITLE = self._title  # what "Entered" and "Exited" say
        if self._body is not None:
            self._body.Destroy()
        self._body = body = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            body,
            label=(
                f"These apply to {show.title} only. Anything you do not change here "
                "keeps following its folder and your shared defaults, so changing "
                "one of those later still reaches this podcast."
            ),
        )
        intro.Wrap(580)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(body, label="&Category:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._category = wx.Choice(
            body,
            choices=[CATEGORY_LABELS.get(name, name) for name in self._categories],
        )
        self._category.SetName("Category")
        self._category.SetHelpText(
            "Which group of settings is shown below. Seventy controls in one list "
            "is not a list anybody can work through by ear, so this shows one "
            "group at a time. It hides nothing -- every group is one keystroke away."
        )
        self._category.SetSelection(0)
        root.Add(self._category, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._panel = wx.ScrolledWindow(body, style=wx.VSCROLL | wx.BORDER_SIMPLE)
        self._panel.SetScrollRate(0, 12)
        root.Add(self._panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # The three things that are not settings: two flags that live on the
        # podcast record itself, and the filter, which is a rule set with its
        # own gated window rather than a value.
        self._favorite = wx.CheckBox(body, label="A &favorite podcast")
        self._favorite.SetValue(show.is_favorite)
        self._favorite.SetHelpText(
            "Puts this podcast in the Favorites view. It is a mark, not a folder: "
            "the podcast stays exactly where it is filed."
        )
        root.Add(self._favorite, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._route_inbox = wx.CheckBox(body, label="&Route new episodes to the Inbox")
        self._route_inbox.SetValue(show.route_to_inbox)
        self._route_inbox.SetHelpText(settings_help.HELP["inbox_mode"])
        root.Add(self._route_inbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._auto_queue = wx.CheckBox(body, label="New episodes go straight to the Play &Queue")
        self._auto_queue.SetValue(show.auto_queue)
        self._auto_queue.SetHelpText(settings_help.SHOW_HELP["auto_queue"])
        root.Add(self._auto_queue, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._filters_btn = wx.Button(body, label="Episode Fi&lters...")
        self._filters_btn.SetHelpText(
            settings_help.FILTER_HELP["enabled"]
            + " "
            + filters.describe_configuration(maintenance.filter_for(library, show))
        )
        clear_btn = wx.Button(body, label="Use Shared &Defaults")
        clear_btn.SetHelpText(settings_help.SHOW_HELP["reset"])
        changed_btn = wx.Button(body, label="What Have I C&hanged?")
        changed_btn.SetHelpText(
            "Lists only the settings this podcast answers for itself, out of all "
            "of them. It changes nothing -- it is the question a settings window "
            "full of controls cannot answer."
        )
        buttons.Add(self._filters_btn, 0, wx.RIGHT, 6)
        buttons.Add(clear_btn, 0, wx.RIGHT, 6)
        buttons.Add(changed_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        ok_btn = wx.Button(body, label="Save")
        ok_btn.SetHelpText(
            "Saves what you changed, and only what you changed, and keeps this "
            "window open. Anything you left alone keeps following its folder and "
            "the shared defaults. Ctrl+S does the same from anywhere in the window."
        )
        cancel_btn = wx.Button(body, label="Close")
        cancel_btn.SetHelpText(
            "Closes this window and returns to where you were. Anything not saved "
            "is left as it was; an Episode Filter saved in its own window stays saved."
        )
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, cancel_btn, modeless=True)
        row.Add(ok_btn, 0, wx.RIGHT, 6)
        row.Add(cancel_btn)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        body.SetSizer(root)
        sizer = self.frame.GetSizer()
        sizer.Clear()
        sizer.Add(body, 1, wx.EXPAND)
        self._category.Bind(wx.EVT_CHOICE, self._on_category)
        self._filters_btn.Bind(wx.EVT_BUTTON, self._on_episode_filters)
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_overrides)
        changed_btn.Bind(wx.EVT_BUTTON, self._on_what_changed)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        self._fill_panel()
        self.frame.Layout()

    def focus_target(self) -> Any:
        return self._category

    def menu_rows(self) -> list[tuple[str, Callable[[], None]]]:
        # A frame has no default button, so Save gets a key of its own.
        return [("&Save" + chr(9) + "Ctrl+S", lambda: self._on_ok(None))]

    def shows(self, show: PodcastShow) -> bool:
        """Whether this window is up, on *show*."""
        return bool(self.frame.IsShown()) and self._show.id == show.id

    # -- the generated panel -------------------------------------------------

    def _current_category(self) -> str:
        index = max(0, self._category.GetSelection())
        return self._categories[index] if index < len(self._categories) else self._categories[0]

    def _fill_panel(self) -> None:
        """Rebuild the panel for the chosen category.

        Rebuilt rather than shown and hidden: a hidden control is still in the
        tab order on some platforms, and a settings window where Tab visits
        seventy invisible controls is worse than one that rebuilds.
        """
        wx = self._wx
        self._panel.DestroyChildren()
        self._controls = []
        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        for definition in per_podcast_settings(self._current_category()):
            self._controls.append(
                build_control(
                    self._panel,
                    grid,
                    definition,
                    library=self._library,
                    show=self._show,
                    wx=wx,
                    on_edit=self._on_edit_opaque,
                )
            )
        for built in self._controls:
            if built.follow_button is not None:
                built.follow_button.Bind(
                    wx.EVT_BUTTON, lambda _e, b=built: self._on_follow(b.definition)
                )
        self._panel.SetSizer(grid)
        self._panel.Layout()
        self._panel.FitInside()

    def _on_category(self, _event: object) -> None:
        self._fill_panel()
        # The count, not the name: the reader has already said the name of the
        # choice that just changed, and what it cannot say is how much is now
        # below it.
        label = CATEGORY_LABELS.get(self._current_category(), "")
        self._announce(f"{len(self._controls)} {label} settings.")

    # -- verbs ---------------------------------------------------------------

    def _on_follow(self, definition: SettingDef) -> None:
        if follow_again(self._library, self._show, definition):
            self._changed = True
            self._fill_panel()
            self._announce(
                f"{definition.label_text().rstrip(':')} now follows the folder or "
                "the shared default again."
            )

    def _on_edit_opaque(self, definition: SettingDef) -> None:
        """Open the window that owns a setting the catalogue cannot draw.

        A rule list, a set of labels, a chapter-skip pattern list: each is its
        own editor, and each writes through the resolver like everything else.
        """
        from quill.ui.podcasts.show_list_editor import edit_opaque_setting

        if edit_opaque_setting(
            self.frame,
            library=self._library,
            show=self._show,
            definition=definition,
            announce=self._announce,
        ):
            self._changed = True
            self._fill_panel()

    def _on_episode_filters(self, _event: object) -> None:
        """Open this podcast's Episode Filters on top of this window.

        Written straight to the library rather than held until this dialog's
        OK: the two are different objects, the filter window has its own gated
        save, and making Cancel here silently undo a filter somebody had just
        confirmed applying to their queue would be a genuine surprise.
        """
        from quill.ui.podcasts.episode_filters_dialog import open_episode_filters

        def _saved() -> None:
            self._changed = True
            if self._on_saved is not None:
                self._on_saved()

        open_episode_filters(
            self._host if self._host is not None else self,
            self._show,
            library=self._library,
            parent=self.frame,
            on_saved=_saved,
        )

    def _on_what_changed(self, _event: object) -> None:
        """List only the settings this podcast answers for itself."""
        from quill.ui.dialog_contract import show_message_box

        entries = settings_catalog.changed(self._library, show=self._show)
        summary = settings_catalog.changed_summary(entries, subject=self._show.title)
        body = summary
        if entries:
            body += "\n\n" + "\n".join(entry.label() for entry in entries)
        show_message_box(
            body,
            "What Have I Changed?",
            self._wx.OK | self._wx.ICON_INFORMATION,
            self.frame,
            announce=None,
        )

    def _on_clear_overrides(self, _event: object) -> None:
        from quill.core.podcasts.settings_resolver import clear_scope
        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        entries = settings_catalog.changed(self._library, show=self._show)
        own = [entry for entry in entries if entry.level == LEVEL_SHOW]
        answer = show_message_box(
            f"Drop {self._show.title}'s own answer to "
            f"{len(own)} setting{'' if len(own) == 1 else 's'} and follow its folder "
            "and the shared defaults again?\n\nIt changes settings only -- no "
            "episode, download or queue entry is touched.",
            "Use Shared Defaults",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.frame,
            announce=None,
        )
        if answer != wx.YES:
            return
        dropped = clear_scope(self._library, level=LEVEL_SHOW, scope_id=self._show.id)
        self._changed = True
        self._announce(
            f"{self._show.title} now follows the shared defaults; "
            f"{dropped} setting{'' if dropped == 1 else 's'} dropped."
        )
        self._close_ok()

    def _on_ok(self, _event: object) -> None:
        changed = apply_controls(self._library, self._show, self._controls)
        show = self._show
        show.is_favorite = self._favorite.GetValue()
        show.route_to_inbox = self._route_inbox.GetValue()
        show.auto_queue = self._auto_queue.GetValue()
        self._changed = True
        if changed:
            first = changed[0].say(
                next(b.read() for b in self._controls if b.definition is changed[0])
            )
            self._announce(
                f"Saved {len(changed)} setting{'' if len(changed) == 1 else 's'} for "
                f"{show.title}. {first}"
            )
        else:
            self._announce(f"Saved settings for {show.title}. Nothing was changed.")
        self._close_ok()

    def _close_ok(self) -> None:
        """Saved: tell the caller, show the new state, and stay open."""
        if self._on_saved is not None:
            self._on_saved()
        self._fill_panel()


def open_show_settings(
    host: Any,
    show: PodcastShow,
    *,
    library: PodcastLibrary,
    parent: object,
    on_saved: Callable[[], None] | None = None,
    opener: Any = None,
) -> ShowSettingsWindow:
    """Open, or raise, the one Settings for This Podcast window, on *show*."""
    from quill.ui.podcasts.peer_window import open_peer

    content = {"library": library, "show": show, "on_saved": on_saved}
    existing = getattr(host, "_show_settings_window", None)
    if existing is not None and existing.frame and not existing.shows(show):
        existing.load(**content)

    def _make(owner: Any) -> ShowSettingsWindow:
        return ShowSettingsWindow(parent, announce_cb=owner._announce, host=owner, **content)

    window: ShowSettingsWindow = open_peer(host, "_show_settings_window", _make, opener=opener)
    return window
