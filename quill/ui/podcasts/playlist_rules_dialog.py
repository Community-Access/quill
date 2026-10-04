"""Playlists > New Smart Playlist... / Edit Rules... -- the filters a Smart
Playlist auto-resolves against: which shows, episode status, how recent,
how long, and how to order the result. Every field's "no restriction"
value (no shows checked, 0 days/minutes, "Any status") means that field
doesn't narrow anything -- an untouched dialog describes "every episode of
every subscribed show," the same as the built-in pinned views' own scope.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts.models import PLAYLIST_STATUS_MODES, PlaylistRules, PodcastShow
from quill.core.podcasts.sorting import EPISODE_SORT_MODES

_STATUS_LABELS = ("Any status", "Unplayed", "In progress", "Played")
_SORT_LABELS = (
    "Newest first",
    "Oldest first",
    "Title A-Z",
    "Longest first",
    "Shortest first",
    "Unheard first",
)


class PlaylistRulesWindow:
    """Edits one Smart Playlist's rules -- a peer window (qc.md Phase 4).

    Save hands the rules to *on_save* and the window stays open, so a rule can
    be tried against the live count and changed again. Close (or Escape)
    leaves anything not saved as it was.
    """

    TITLE = "Smart Playlist Rules"
    MENU_TITLE = "Playlist Ru&les"

    def __init__(
        self,
        parent: object,
        *,
        shows: list[PodcastShow],
        rules: PlaylistRules,
        announce_cb: Callable[[str], None] | None = None,
        library: object = None,
        on_save: Callable[[PlaylistRules], None] | None = None,
        key: object = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._body: Any = None
        self.frame = wx.Frame(parent, title="Smart Playlist Rules", size=(520, 760))
        self.frame.SetMinSize((460, 480))
        self.frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.load(shows=shows, rules=rules, library=library, on_save=on_save, key=key)
        self.frame.CentreOnParent()

    def load(
        self,
        *,
        shows: list[PodcastShow],
        rules: PlaylistRules,
        library: object = None,
        on_save: Callable[[PlaylistRules], None] | None = None,
        key: object = None,
    ) -> None:
        """Build the form for *rules*; *key* names what it is editing."""
        wx = self._wx
        # Only for the live preview count. Absent in a test that just wants the
        # form, and the preview simply says nothing then.
        self._library = library
        self._on_save_cb = on_save
        self.key = key
        self._result: PlaylistRules | None = None
        self._shows = sorted(shows, key=lambda s: s.title.casefold())
        if self._body is not None:
            self._body.Destroy()
        self._body = body = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            body,
            label=(
                "A Smart Playlist re-resolves these rules live every time you open it. "
                "Leave a filter at its default to not restrict by it."
            ),
        )
        intro.Wrap(420)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(
            wx.StaticText(body, label="Shows (none checked = every show):"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        # Individual checkboxes, not wx.CheckListBox (A11Y-SR-1): screen
        # readers don't announce checked state as a CheckListBox item is
        # navigated, only the label text -- a real wx.CheckBox always
        # speaks its own state.
        self._shows_scroll = wx.ScrolledWindow(
            body, style=wx.VSCROLL | wx.BORDER_SUNKEN, size=(-1, 130)
        )
        self._shows_scroll.SetScrollRate(0, 20)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        checked_ids = set(rules.show_ids)
        self._show_checks: list[wx.CheckBox] = []
        for show in self._shows:
            check = wx.CheckBox(self._shows_scroll, label=show.title)
            check.SetValue(show.id in checked_ids)
            scroll_sizer.Add(check, 0, wx.ALL, 2)
            self._show_checks.append(check)
        self._shows_scroll.SetSizer(scroll_sizer)
        root.Add(self._shows_scroll, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(body, label="Episode &status:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._status_choice = wx.Choice(body, choices=list(_STATUS_LABELS))
        self._status_choice.SetName("Episode status filter")
        self._status_choice.SetHelpText(
            "Only episodes in this state: unheard, in progress or heard. Any status "
            "does not narrow anything."
        )
        status_index = (
            PLAYLIST_STATUS_MODES.index(rules.episode_status)
            if rules.episode_status in PLAYLIST_STATUS_MODES
            else 0
        )
        self._status_choice.SetSelection(status_index)
        grid.Add(self._status_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(body, label="Published within &days (0 = any):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._days_ctrl = wx.SpinCtrl(body, min=0, max=3650)
        self._days_ctrl.SetValue(rules.published_within_days)
        self._days_ctrl.SetName("Only episodes published within this many days (0 = no limit)")
        self._days_ctrl.SetHelpText(
            "Only episodes published within this many days. 0 means no limit."
        )
        grid.Add(self._days_ctrl, 0)

        grid.Add(
            wx.StaticText(body, label="&Minimum minutes (0 = any):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._min_minutes_ctrl = wx.SpinCtrl(body, min=0, max=1440)
        self._min_minutes_ctrl.SetValue(rules.min_duration_minutes)
        self._min_minutes_ctrl.SetName("Only episodes at least this many minutes long")
        self._min_minutes_ctrl.SetHelpText(
            "Only episodes at least this many minutes long. 0 means any length."
        )
        grid.Add(self._min_minutes_ctrl, 0)

        grid.Add(
            wx.StaticText(body, label="Ma&ximum minutes (0 = any):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._max_minutes_ctrl = wx.SpinCtrl(body, min=0, max=1440)
        self._max_minutes_ctrl.SetValue(rules.max_duration_minutes)
        self._max_minutes_ctrl.SetName("Only episodes at most this many minutes long")
        self._max_minutes_ctrl.SetHelpText(
            "Only episodes at most this many minutes long. 0 means any length."
        )
        grid.Add(self._max_minutes_ctrl, 0)

        grid.Add(wx.StaticText(body, label="So&rt:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._sort_choice = wx.Choice(body, choices=list(_SORT_LABELS))
        self._sort_choice.SetName("How this playlist's episodes are ordered")
        self._sort_choice.SetHelpText("How this playlist's episodes are ordered.")
        sort_index = (
            EPISODE_SORT_MODES.index(rules.sort_mode)
            if rules.sort_mode in EPISODE_SORT_MODES
            else 0
        )
        self._sort_choice.SetSelection(sort_index)
        grid.Add(self._sort_choice, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # The wider rule set -- match mode, folders, downloads, notes, text,
        # progress, limit -- plus the live preview count. Its own module: this
        # dialog is near its GATE-11 ceiling and those rows are a coherent set.
        from quill.ui.podcasts.playlist_rules_extra import ExtraRules

        self._extra = ExtraRules(body, root, rules, announce=self._announce)
        self._extra.set_preview_source(self._preview_count)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(body, label="Save")
        ok_btn.SetHelpText(
            "Saves these rules to the playlist and keeps this window open. "
            "Ctrl+S does the same from anywhere in the window."
        )
        cancel_btn = wx.Button(body, label="Close")
        cancel_btn.SetHelpText(
            "Closes this window and returns to where you were. Anything not saved "
            "is left as it was."
        )
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, cancel_btn, modeless=True)
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        body.SetSizer(root)
        sizer = self.frame.GetSizer()
        sizer.Clear()
        sizer.Add(body, 1, wx.EXPAND)
        self.frame.Layout()

        ok_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def focus_target(self) -> Any:
        return self._show_checks[0] if self._show_checks else self._status_choice

    def menu_rows(self) -> list[tuple[str, Callable[[], None]]]:
        # A frame has no default button, so Save gets a key of its own.
        return [("&Save" + chr(9) + "Ctrl+S", lambda: self._on_save(None))]

    def _current_rules(self) -> PlaylistRules:
        """What the form currently says, as a rules record."""
        checked_show_ids = [
            show.id
            for show, check in zip(self._shows, self._show_checks, strict=True)
            if check.GetValue()
        ]
        status_index = self._status_choice.GetSelection()
        sort_index = self._sort_choice.GetSelection()
        return PlaylistRules(
            show_ids=checked_show_ids,
            episode_status=PLAYLIST_STATUS_MODES[status_index] if status_index >= 0 else "any",
            published_within_days=self._days_ctrl.GetValue(),
            min_duration_minutes=self._min_minutes_ctrl.GetValue(),
            max_duration_minutes=self._max_minutes_ctrl.GetValue(),
            sort_mode=EPISODE_SORT_MODES[sort_index] if sort_index >= 0 else "date_newest",
            **self._extra.values(),
        )

    def _preview_count(self) -> int:
        """How many episodes these rules match **right now**.

        The difference between a rule builder people trust and one they abandon.
        A set of filters with no feedback is a guess somebody has to save,
        close, open and check -- four steps to answer "did I mean that?".
        """
        library = self._library
        if library is None:
            return -1
        from quill.core.podcasts.models import Playlist
        from quill.core.podcasts.playlists import resolve_playlist

        try:
            preview = Playlist(id="preview", name="", kind="smart", rules=self._current_rules())
            return len(resolve_playlist(library, preview))
        except Exception:  # noqa: BLE001 - a preview that cannot be computed is not an error
            return -1

    def _on_save(self, _event: object) -> None:
        self._result = self._current_rules()
        if self._on_save_cb is not None:
            self._on_save_cb(self._result)


def open_playlist_rules(
    host: Any,
    *,
    parent: object,
    shows: list[PodcastShow],
    rules: PlaylistRules,
    library: object,
    on_save: Callable[[PlaylistRules], None],
    key: object,
    opener: Any = None,
) -> PlaylistRulesWindow:
    """Open, or raise, the one Smart Playlist Rules window, on *key*.

    Already showing the same playlist, it is only raised, so a draft survives;
    otherwise it is rebuilt from the rules given.
    """
    from quill.ui.podcasts.peer_window import open_peer

    content = {"shows": shows, "rules": rules, "library": library, "on_save": on_save, "key": key}
    existing = getattr(host, "_playlist_rules_window", None)
    if existing is not None and existing.frame:
        if not (existing.frame.IsShown() and key is not None and existing.key == key):
            existing.load(**content)

    def _make(owner: Any) -> PlaylistRulesWindow:
        return PlaylistRulesWindow(parent, announce_cb=owner._announce, **content)

    window: PlaylistRulesWindow = open_peer(host, "_playlist_rules_window", _make, opener=opener)
    return window
