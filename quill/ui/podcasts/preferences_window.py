"""Preferences: everything that is not about one podcast, in eight sections (qc.md 13).

Four windows called themselves settings; two remain. This is the first:
the app's own rows (the ``PodcastHistory`` record) and the shared defaults
for every podcast (the catalogue at the global level), in grouped sections
that scroll -- *When Cast opens*, *Playing*, *Fetching*, *The Inbox*,
*Chapters*, *Telling you*, *The window*, *Data* -- each row exactly once.
Podcast Settings and Skip Settings are absorbed here.

A **Section** list first, then a scrolling panel rebuilt for the section
(a hidden control is still a Tab stop on some platforms, and a window where
Tab visits seventy invisible controls is worse than one that rebuilds). The
catalogue rows are built by kind from the definitions, with the definition's
own help, so a new default needs a definition and nothing here; the app rows
are the small table at the top of this file.

Save writes only what changed: a row left alone writes nothing, so opening
this window and pressing Save never freezes ninety settings at today's
values (the old dialog's actual behaviour, qc.md 6b).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.podcasts import settings_catalog
from quill.core.podcasts.settings_types import (
    CATEGORY_ANNOUNCEMENTS,
    CATEGORY_ARRIVAL,
    CATEGORY_CURATION,
    CATEGORY_PLAYBACK,
    CATEGORY_STORAGE,
    KIND_BOOL,
    KIND_CHOICE,
    KIND_FLOAT,
    KIND_INT,
    KIND_OPAQUE,
    KIND_TEXT,
    LEVEL_GLOBAL,
    SettingDef,
)

__all__ = ["AppRow", "CastPreferencesWindow", "SECTIONS", "section_of", "TITLE"]

TITLE = "QUILL Cast Preferences"

SECTIONS: tuple[tuple[str, str], ...] = (
    ("opens", "When Cast opens"),
    ("playing", "Playing"),
    ("fetching", "Fetching"),
    ("inbox", "The Inbox"),
    ("chapters", "Chapters"),
    ("telling", "Telling you"),
    ("window", "The window"),
    ("data", "Data"),
)

#: Catalogue ids placed by hand; everything else goes by category.
_SECTION_BY_ID: dict[str, str] = {
    "default_launch_view": "opens",
    "check_on_launch": "opens",
    "check_on_resume": "opens",
    "check_burst_after_miss": "opens",
    "refresh_schedule": "fetching",
    "check_in_quiet_hours": "fetching",
    "refresh_minutes": "",  # absorbed by the schedule; never shown
    "refresh_on_launch": "",  # absorbed by Check when Cast opens
    "check_interval_minutes": "",  # Radio's heartbeat; not Cast's row
    "inbox_mode": "inbox",
    "inbox_max_episodes": "inbox",
    "inbox_age_limit_hours": "inbox",
    "queue_age_limit_days": "inbox",
    "new_episode_alert": "telling",
    "download_notify": "telling",
    "announce_show_name_first": "telling",
    "download_root": "data",
    "delete_files_on_remove": "data",
    "retention": "data",
    "retention_count": "data",
    "download_retention_days": "data",
    "delete_after_play": "data",
    "storage_cap_mb": "data",
    "history_retention_days": "data",
    "stats_streaks_enabled": "data",
    "directory_source": "data",
    "playback_cache": "data",
    "playback_cache_cap_mb": "data",
}
_SECTION_BY_CATEGORY: dict[str, str] = {
    CATEGORY_ARRIVAL: "fetching",
    CATEGORY_PLAYBACK: "playing",
    CATEGORY_STORAGE: "data",
    CATEGORY_ANNOUNCEMENTS: "telling",
    CATEGORY_CURATION: "window",
}


def section_of(definition: SettingDef) -> str:
    """Which section a catalogue default is shown in ("" means not shown)."""
    if definition.id in _SECTION_BY_ID:
        return _SECTION_BY_ID[definition.id]
    if definition.id.startswith("chapters_"):
        return "chapters"
    if definition.id.startswith("row_"):
        return "telling"
    return _SECTION_BY_CATEGORY.get(definition.category, "window")


@dataclass(slots=True)
class AppRow:
    """One of the app's own rows (history-backed), as the window builds it."""

    key: str
    label: str
    help: str
    section: str
    kind: str = "bool"
    #: For choices: (value, label) pairs; values compare as text.
    options: tuple[tuple[object, str], ...] = ()
    #: For a button row: what it opens.
    action: Callable[[], None] | None = None


@dataclass(slots=True)
class _Built:
    key: str
    control: Any
    original: object
    definition: SettingDef | None = None
    row: AppRow | None = None
    #: For a choice whose stored values are not the definition's own choices.
    values: tuple[object, ...] = ()

    def read(self) -> object:
        if self.values:
            index = max(0, self.control.GetSelection())
            return self.values[index] if index < len(self.values) else self.original
        if self.definition is not None:
            kind = self.definition.kind
            if kind == KIND_CHOICE:
                values = [choice.value for choice in self.definition.choices]
                index = max(0, self.control.GetSelection())
                return values[index] if index < len(values) else self.definition.default
            if kind == KIND_BOOL:
                return bool(self.control.GetValue())
            if kind in (KIND_INT, KIND_FLOAT):
                return self.definition.coerce(self.control.GetValue())
            if kind == KIND_TEXT:
                return str(self.control.GetValue())
            return self.original
        assert self.row is not None
        if self.row.kind == "choice":
            index = max(0, self.control.GetSelection())
            return self.row.options[index][0] if index < len(self.row.options) else self.original
        if self.row.kind == "bool":
            return bool(self.control.GetValue())
        return self.original


class CastPreferencesWindow:
    """The dialog. ``show()`` returns the changes, or None."""

    def __init__(
        self,
        parent: Any,
        *,
        library: Any,
        history: Any,
        app_rows: list[AppRow],
        announce: Callable[[str], None] | None = None,
        on_change_schedule: Callable[[], None] | None = None,
        summary: Callable[[], str] | None = None,
        open_section: str = "",
    ) -> None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids

        self._wx = wx
        self._library = library
        self._history = history
        self._app_rows = list(app_rows)
        self._announce = announce or (lambda _m: None)
        self._on_change_schedule = on_change_schedule
        self._summary = summary
        self._built: list[_Built] = []
        self._changed_app: dict[str, object] = {}
        self._changed_defs: dict[str, object] = {}
        self._result: tuple[dict[str, object], dict[str, object]] | None = None
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label="&Section:"), 0, wx.LEFT | wx.TOP, 8)
        self._section = wx.Choice(self.dialog, choices=[label for _key, label in SECTIONS])
        self._section.SetHelpText(
            "Which group of settings the panel below shows: when Cast opens, "
            "playing, fetching, the Inbox, chapters, telling you, the window, and "
            "data. Changing the section keeps what you changed in the others."
        )
        keys = [key for key, _label in SECTIONS]
        self._section.SetSelection(keys.index(open_section) if open_section in keys else 0)
        self._section.Bind(wx.EVT_CHOICE, lambda _e: self._on_section())
        root.Add(self._section, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._panel = wx.ScrolledWindow(self.dialog, style=wx.TAB_TRAVERSAL | wx.VSCROLL)
        self._panel.SetScrollRate(0, 16)
        root.Add(self._panel, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        ok = wx.Button(self.dialog, wx.ID_OK, label="Save")
        ok.SetHelpText("Saves every change made in any section and says what changed.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Closes this window without saving; nothing you changed here is kept.")
        buttons.Add(ok, 0, wx.RIGHT, 6)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        self.dialog.SetSize((720, 560))
        self.dialog.SetMinSize((560, 400))
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_OK, affirmative_label="Save", cancel_id=wx.ID_CANCEL
        )
        ok.Bind(wx.EVT_BUTTON, self._on_save)
        self._fill()

    # -- building a section ---------------------------------------------------------- #

    def _current_section(self) -> str:
        return SECTIONS[max(0, self._section.GetSelection())][0]

    def _remember(self) -> None:
        """Keep what the listener changed in the section about to be rebuilt."""
        for built in self._built:
            value = built.read()
            if value == built.original:
                continue
            if built.definition is not None:
                self._changed_defs[built.definition.id] = value
            elif built.row is not None:
                self._changed_app[built.row.key] = value

    def _on_section(self) -> None:
        self._remember()
        self._fill()
        self._announce(f"{len(self._built)} settings.")

    def _fill(self) -> None:
        wx = self._wx
        section = self._current_section()
        self._panel.DestroyChildren()
        self._built = []
        # Section is Alt+S; every row below gets its own letter (GATE-14).
        self._used_keys: set[str] = {"s"}
        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        for row in self._app_rows:
            if row.section == section:
                self._build_app_row(grid, row)
        for definition in settings_catalog.for_level(LEVEL_GLOBAL):
            if section_of(definition) == section:
                self._build_default(grid, definition)
        if section == "fetching" and self._summary is not None:
            grid.Add(wx.StaticText(self._panel, label=""), 0)
            note = wx.StaticText(self._panel, label=self._summary())
            note.Wrap(560)
            grid.Add(note, 1, wx.EXPAND)
        self._panel.SetSizer(grid)
        self._panel.Layout()
        self._panel.FitInside()
        self._panel.Scroll(0, 0)

    def _value_for(self, built_key: str, original: object, *, app: bool) -> object:
        store = self._changed_app if app else self._changed_defs
        return store.get(built_key, original)

    def _build_app_row(self, grid: Any, row: AppRow) -> None:
        wx = self._wx
        original = getattr(self._history, row.key, None) if row.kind != "action" else None
        value = self._value_for(row.key, original, app=True)
        if row.kind == "bool":
            grid.Add(wx.StaticText(self._panel, label=""), 0)
            control = wx.CheckBox(self._panel, label=self._key(row.label))
            control.SetValue(bool(value))
            control.SetHelpText(row.help)
            grid.Add(control, 1, wx.EXPAND)
        elif row.kind == "choice":
            grid.Add(
                wx.StaticText(self._panel, label=self._key(row.label)), 0, wx.ALIGN_CENTER_VERTICAL
            )
            control = wx.Choice(self._panel, choices=[label for _value, label in row.options])
            values = [str(item) for item, _label in row.options]
            control.SetSelection(values.index(str(value)) if str(value) in values else 0)
            control.SetHelpText(row.help)
            grid.Add(control, 1, wx.EXPAND)
        else:
            grid.Add(wx.StaticText(self._panel, label=""), 0)
            control = wx.Button(self._panel, label=self._key(row.label))
            control.SetHelpText(row.help)
            control.Bind(wx.EVT_BUTTON, lambda _e, r=row: r.action() if r.action else None)
            grid.Add(control, 0)
            return
        self._built.append(_Built(row.key, control, original, row=row))

    def _build_default(self, grid: Any, definition: SettingDef) -> None:
        wx = self._wx
        from quill.core.podcasts.settings_resolver import value_of

        original = value_of(self._library, definition, show=None)
        value = self._value_for(definition.id, original, app=False)
        help_text = (
            f"{definition.help} This is the shared default; a podcast can answer "
            "differently in Settings for This Podcast."
        )
        kind = definition.kind
        if definition.id == "default_launch_view":
            # Stored as text, offered as the places it can name (qc.md 4.8).
            from quill.core.podcasts import launch_place

            grid.Add(
                wx.StaticText(self._panel, label=self._key("Where to land on la&unch:")),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            control = wx.Choice(self._panel, choices=[label for _v, label in launch_place.CHOICES])
            control.SetSelection(launch_place.index_for(str(value or "")))
            control.SetHelpText(
                "Which place has focus when QUILL Cast opens. What is new lands on "
                "the Inbox when anything is waiting, else Continue Listening, else "
                "Podcasts; every other choice always lands on that place, even empty."
            )
            grid.Add(control, 1, wx.EXPAND)
            values = tuple(item for item, _label in launch_place.CHOICES)
            self._built.append(
                _Built(definition.id, control, original or "", definition=definition, values=values)
            )
            return
        if definition.id == "refresh_schedule":
            grid.Add(
                wx.StaticText(self._panel, label=self._key(definition.label)),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            from quill.core.podcasts import schedule_policy

            button = wx.Button(
                self._panel,
                label=f"Change Schedule... ({self._schedule_words(schedule_policy)})",
            )
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e: self._change_schedule())
            grid.Add(button, 1, wx.EXPAND)
            return
        if kind == KIND_BOOL:
            grid.Add(wx.StaticText(self._panel, label=""), 0)
            control = wx.CheckBox(self._panel, label=self._key(definition.label))
            control.SetValue(bool(value))
        elif kind == KIND_CHOICE:
            grid.Add(
                wx.StaticText(self._panel, label=self._key(definition.label)),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            control = wx.Choice(
                self._panel, choices=[choice.label for choice in definition.choices]
            )
            values = [choice.value for choice in definition.choices]
            control.SetSelection(values.index(value) if value in values else 0)
        elif kind == KIND_INT:
            grid.Add(
                wx.StaticText(self._panel, label=self._key(definition.label)),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            low = int(definition.minimum) if definition.minimum is not None else -1
            high = int(definition.maximum) if definition.maximum is not None else 1_000_000
            control = wx.SpinCtrl(
                self._panel, min=low, max=high, initial=int(definition.coerce(value))
            )  # type: ignore[arg-type]
        elif kind == KIND_FLOAT:
            grid.Add(
                wx.StaticText(self._panel, label=self._key(definition.label)),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            low = float(definition.minimum) if definition.minimum is not None else 0.0
            high = float(definition.maximum) if definition.maximum is not None else 1000.0
            control = wx.SpinCtrlDouble(
                self._panel, min=low, max=high, initial=float(definition.coerce(value)), inc=0.1
            )  # type: ignore[arg-type]
        elif kind == KIND_TEXT:
            grid.Add(
                wx.StaticText(self._panel, label=self._key(definition.label)),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            control = wx.TextCtrl(self._panel, value=str(value or ""))
        elif kind == KIND_OPAQUE:
            return
        else:
            return
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        self._built.append(_Built(definition.id, control, original, definition=definition))

    def _key(self, label: str) -> str:
        """*label* with an access key no other control in this section has.

        The catalogue's labels were written for five separate windows, so two
        rows that now share a section can claim one letter, and a duplicate
        letter is one Windows cycles between rather than presses. The label's
        own letter is kept when it is free; otherwise the first free initial of
        a word, then any free letter; otherwise none at all.
        """
        plain = label.replace("&", "")
        used = getattr(self, "_used_keys", set())
        wanted = label.index("&") if "&" in label else -1
        candidates: list[int] = []
        if 0 <= wanted < len(plain):
            candidates.append(wanted)
        candidates += [
            i for i, ch in enumerate(plain) if ch.isalpha() and (i == 0 or plain[i - 1] == " ")
        ]
        candidates += [i for i, ch in enumerate(plain) if ch.isalpha()]
        for index in candidates:
            letter = plain[index].lower()
            if letter not in used:
                used.add(letter)
                return plain[:index] + "&" + plain[index:]
        return plain

    def _schedule_words(self, schedule_policy: Any) -> str:
        return str(schedule_policy.describe_for(self._library, None)).rstrip(".")

    def _change_schedule(self) -> None:
        if self._on_change_schedule is not None:
            self._on_change_schedule()
            self._remember()
            self._fill()

    # -- saving ---------------------------------------------------------------------- #

    def _on_save(self, _event: object) -> None:
        self._remember()
        self._result = (dict(self._changed_app), dict(self._changed_defs))
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[dict[str, object], dict[str, object]] | None:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        self._section.SetFocus()
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()
