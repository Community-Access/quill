"""Accessible control navigation for the family's existing settings dialogs.

Two sources feed one search (qc.md X-01):

* **Built controls** -- every labelled control the window already has, walked
  when the search is installed and again on every query, so a notebook page
  that builds itself later is found once it exists.
* **Declared settings** -- rows a window hands over with
  :func:`declare_settings`, from the wx-free index in
  :mod:`quill.core.settings_finder`. These are what reach a settings area that
  has no controls yet: a page QUILL's Settings dialog builds only when it is
  first shown, a setting kept in the main window rather than in Preferences,
  or a whole dialog the Preferences hub has not opened. A declared row whose
  control does exist (``control_for``) replaces the walked one, so nothing is
  listed twice and the declared aliases still count.

Choosing a declared row with no control calls its ``go``. ``go`` returns the
control to move to when the setting is in this window (after building or
revealing its page), or ``None`` when it carried the person somewhere else --
which is then that caller's to finish, focus and say.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import wx

from quill.core.settings_finder import SettingEntry, match_rank, result_label


@dataclass(frozen=True)
class SettingTarget:
    label: str
    description: str
    control: Any
    #: For a setting on a part of the window not built yet (qc.md X-01): shows
    #: that part and returns the control to focus. *control* is then None.
    reveal: Callable[[], Any] | None = None
    #: For a declared setting with no control yet: open its area. Returns the
    #: control to focus, or None when the setting lives in another window.
    go: Callable[[], Any] | None = None

    def enabled(self) -> bool:
        return self.control is None or bool(self.control.IsEnabled())


@dataclass(frozen=True)
class DeclaredSettings:
    """The settings a window declares rather than builds."""

    entries: tuple[SettingEntry, ...]
    go: Callable[[SettingEntry], Any]
    control_for: Callable[[SettingEntry], Any] | None = None


def declare_settings(
    window: Any,
    entries: Iterable[SettingEntry],
    go: Callable[[SettingEntry], Any],
    *,
    control_for: Callable[[SettingEntry], Any] | None = None,
) -> DeclaredSettings:
    """Hand *window*'s search the settings it cannot find by walking controls.

    Call before the window is shown; the shared show paths install the search.
    """
    declared = DeclaredSettings(tuple(entries), go, control_for)
    window._quill_declared_settings = declared
    return declared


def find_settings(targets: list[SettingTarget], query: str) -> list[SettingTarget]:
    """Every target matching all the words of *query*, best match first."""
    ranked = []
    for position, target in enumerate(targets):
        rank = match_rank(target.label, target.description, query)
        if rank is not None:
            ranked.append((rank, position, target))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [target for _rank, _position, target in ranked]


def _targets(parent: Any, prefix: str = "") -> list[SettingTarget]:
    targets = []
    label = ""
    editable = (
        wx.TextCtrl,
        wx.Choice,
        wx.ComboBox,
        wx.CheckBox,
        wx.RadioBox,
        wx.SpinCtrl,
        wx.SpinCtrlDouble,
        wx.Slider,
        wx.Button,
    )
    generic_names = {"text", "choice", "comboBox", "check", "button", "spinCtrl", "slider"}
    for control in parent.GetChildren():
        if isinstance(control, wx.StaticText):
            label = control.GetLabel().replace("&", "").strip().rstrip(":")
            continue
        if isinstance(control, editable):
            if control.GetId() in {wx.ID_OK, wx.ID_CANCEL, wx.ID_APPLY, wx.ID_CLOSE}:
                continue
            name = control.GetName()
            own_label = control.GetLabel() if isinstance(control, (wx.Button, wx.CheckBox)) else ""
            title = own_label or label or (name if name not in generic_names else "")
            title = title.replace("&", "").strip()
            if title:
                targets.append(
                    SettingTarget(
                        f"{prefix}{title}", f"{name} {control.GetHelpText()} {label}", control
                    )
                )
            label = ""
            continue
        if isinstance(control, wx.BookCtrlBase):
            for index in range(control.GetPageCount()):
                targets.extend(_targets(control.GetPage(index), f"{control.GetPageText(index)}: "))
        else:
            targets.extend(_targets(control, prefix))
    return targets


def registry_page_index(
    dialog: Any,
    book: Any,
    page_specs: list[tuple[str, list[Any]]],
    built_pages: set[int],
    build_page: Callable[[int], None],
    control_index: dict[str, tuple[int, Any]],
    value_of: Callable[[str], object],
) -> list[SettingTarget]:
    """Every setting on every page of a lazily built Settings book.

    QUILL's Settings builds a page the first time it is shown, so a search over
    the controls on screen found only the first page. The built pages are read
    as usual; an unbuilt page's settings come from its registry specs, and
    choosing one shows that page and returns the control to focus.
    """

    def reveal(index: int, key: str) -> Any:
        book.SetSelection(index)
        build_page(index)
        entry = control_index.get(key)
        return entry[1] if entry is not None else None

    targets = _targets(dialog)
    for index, (title, specs) in enumerate(page_specs):
        if index in built_pages:
            continue
        for spec in specs:
            if isinstance(value_of(spec.key), (list, dict)):
                continue  # not drawn on the page (it has its own manager)
            targets.append(
                SettingTarget(
                    f"{title}: {spec.label}",
                    f"{spec.key} {spec.description} {' '.join(spec.keywords)}",
                    None,
                    reveal=lambda i=index, k=spec.key: reveal(i, k),
                )
            )
    return targets


def _declared_targets(window: Any) -> tuple[list[SettingTarget], set[int]]:
    """Declared rows as targets, and the ids of the built controls they claim."""
    declared = getattr(window, "_quill_declared_settings", None)
    if not isinstance(declared, DeclaredSettings):
        return [], set()
    targets: list[SettingTarget] = []
    claimed: set[int] = set()
    for entry in declared.entries:
        control = declared.control_for(entry) if declared.control_for is not None else None
        if control is not None:
            claimed.add(id(control))
        targets.append(
            SettingTarget(
                result_label(entry),
                entry.searchable_text(),
                control,
                go=None if control is not None else (lambda e=entry: declared.go(e)),
            )
        )
    return targets, claimed


class PreferencesSearch:
    """Find a setting and focus it without changing values or accepting edits."""

    def __init__(self, dialog: Any, announce: Callable[[str], None] | None = None) -> None:
        from quill.ui.app_context_help import ensure_help_provider

        ensure_help_provider()
        self.dialog = dialog
        self.announce = announce or (lambda _message: None)
        self.panel: Any = None
        self.targets = self._all_targets()
        self.matches: list[SettingTarget] = []
        self.timer: Any = None
        self.closed = False
        self.panel = wx.Panel(dialog)
        layout = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.panel, label="Find a setting:")
        layout.Add(label, 0, wx.BOTTOM, 4)
        self.search = wx.TextCtrl(self.panel)
        self.search.SetName("Find a setting")
        self.search.SetHelpText(
            "Find settings by label or help text. Control F returns here. "
            "Down moves to matches; Enter focuses a selected setting without changing it. "
            "Escape clears a search before closing the dialog."
        )
        layout.Add(self.search, 0, wx.EXPAND)
        results_label = wx.StaticText(self.panel, label="Matching settings:")
        layout.Add(results_label, 0, wx.TOP, 4)
        self.results = wx.ListBox(self.panel, size=(-1, 90))
        self.results.SetName("Matching settings")
        self.results.SetHelpText(
            "Settings matching the search. Arrow through results and press Enter "
            "to focus the setting. Disabled settings cannot be changed."
        )
        layout.Add(self.results, 0, wx.EXPAND | wx.TOP, 4)
        self.status = wx.StaticText(self.panel, label="")
        layout.Add(self.status, 0, wx.TOP, 4)
        self.panel.SetSizer(layout)
        self.results.Hide()
        self.status.Hide()
        original = dialog.GetSizer()
        dialog.SetSizer(None, deleteOld=False)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self.panel, 0, wx.EXPAND | wx.ALL, 8)
        outer.Add(original, 1, wx.EXPAND)
        dialog.SetSizer(outer)
        self.panel.MoveBeforeInTabOrder(dialog.GetChildren()[0])
        self.search.Bind(wx.EVT_TEXT, self._on_search)
        self.results.Bind(wx.EVT_LISTBOX_DCLICK, self._on_choose)
        dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        outer.Fit(dialog)
        self.search.SetFocus()

    def _all_targets(self) -> list[SettingTarget]:
        """Built controls (not the search's own) plus declared settings."""
        declared, claimed = _declared_targets(self.dialog)
        # Older lazy settings surfaces provide a complete index themselves.
        # Declarations supersede that index when present, avoiding duplicate
        # unbuilt rows while retaining the legacy reveal contract elsewhere.
        index = getattr(self.dialog, "_quill_settings_index", None)
        indexed = list(index()) if callable(index) and not declared else _targets(self.dialog)
        built = [
            target
            for target in indexed
            if id(target.control) not in claimed
            and (self.panel is None or target.control.GetParent() is not self.panel)
        ]
        return built + declared

    def _on_search(self, _event: Any) -> None:
        if self.closed:
            return
        self.targets = self._all_targets()
        self.matches = find_settings(self.targets, self.search.GetValue())
        active = bool(self.search.GetValue().strip())
        self.results.Set([
            target.label + (" (disabled)" if not target.enabled() else "")
            for target in self.matches
        ])
        if self.matches:
            self.results.SetSelection(0)
        self.results.Show(active)
        self.status.Show(active)
        self.status.SetLabel(f"{len(self.matches)} matching settings" if active else "")
        self.dialog.Layout()
        if self.timer is not None:
            self.timer.Stop()
        self.timer = wx.CallLater(250, self._report_count) if active else None

    def _report_count(self) -> None:
        if not self.closed:
            self.announce(f"{len(self.matches)} matching settings")

    def _on_choose(self, _event: Any) -> None:
        index = self.results.GetSelection()
        if not 0 <= index < len(self.matches):
            return
        target = self.matches[index]
        control = target.control
        if control is None:
            action = target.go or target.reveal
            if action is None:
                return
            if self.timer is not None:
                self.timer.Stop()
            control = action()
            if control is None or self.closed:
                return  # it lives in another window; the caller moves there
        if not control.IsEnabled():
            self.announce("This setting is disabled")
            return
        self._navigate(control)

    def _navigate(self, control: Any) -> None:
        """Reveal the page *control* is on, then focus it."""
        child = control
        while child is not self.dialog:
            parent = child.GetParent()
            if parent is None:
                return
            if isinstance(parent, wx.BookCtrlBase):
                for page in range(parent.GetPageCount()):
                    if parent.GetPage(page) is child:
                        parent.SetSelection(page)
                        break
            panels = getattr(parent, "_panels", {})
            for name, panel in panels.items():
                if panel is child and hasattr(parent, "sections"):
                    parent.sections.SetStringSelection(name)
                    parent._on_section(None)
                    break
            child = parent
        self.dialog.Layout()
        control.SetFocus()
        parent = control.GetParent()
        while parent is not None and parent is not self.dialog:
            if isinstance(parent, wx.ScrolledWindow):
                parent.ScrollChildIntoView(control)
                break
            parent = parent.GetParent()

    def _on_key(self, event: Any) -> None:
        key = event.GetKeyCode()
        if event.ControlDown() and key in (ord("F"), ord("f")):
            self.search.SetFocus()
            self.search.SelectAll()
            return
        focused = wx.Window.FindFocus()
        if focused in (self.search, self.results):
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                self._on_choose(None)
                return
            if key == wx.WXK_ESCAPE and self.search.GetValue():
                self.search.SetValue("")
                self.search.SetFocus()
                return
            if key == wx.WXK_DOWN and focused is self.search and self.matches:
                self.results.SetFocus()
                return
        event.Skip()

    def close(self) -> None:
        self.closed = True
        if self.timer is not None:
            self.timer.Stop()


def install_preferences_context_help(dialog: Any) -> None:
    """Onboard apps whose local dialogs bypass the shared show contracts."""
    from quill.ui.app_context_help import install

    install(dialog)
    install_preferences_search(dialog)


def install_preferences_search(
    dialog: Any, *, announce: Callable[[str], None] | None = None
) -> PreferencesSearch | None:
    title_getter = getattr(dialog, "GetTitle", None)
    title = title_getter().casefold() if callable(title_getter) else ""
    is_settings_form = bool(getattr(dialog, "_quill_settings_form", False))
    if not ("preferences" in title or title.endswith("settings") or is_settings_form):
        return None
    if not isinstance(dialog, (wx.Dialog, wx.Frame)) or dialog.GetSizer() is None:
        return None
    existing = getattr(dialog, "_quill_preferences_search", None)
    if existing is not None:
        existing.closed = False
        return existing
    search = PreferencesSearch(dialog, announce)
    dialog._quill_preferences_search = search

    def on_destroy(event: Any) -> None:
        if event.GetEventObject() is dialog:
            search.close()
        event.Skip()

    dialog.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    return search
