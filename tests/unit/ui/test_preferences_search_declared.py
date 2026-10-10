"""Find a setting reaches settings that have no control yet (qc.md X-01).

Live wx: a declared row that claims a built control replaces it (no duplicate,
aliases still count); a declared row on a page not built yet builds the page
and focuses the setting; a row in another window hands over; the shared
Preferences dialog keeps or drops edits truthfully when search leaves it; and
QUILL's Settings dialog and Preferences hub are wired to the registry.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.settings_finder import SettingEntry
from quill.ui.preferences_search import declare_settings, install_preferences_search

pytestmark = pytest.mark.machine_global


@pytest.fixture
def application():
    existing = wx.GetApp()
    app = existing or wx.App(False)
    yield app
    if existing is None:
        app.Destroy()


def _dialog(title: str = "Test Preferences") -> tuple[wx.Dialog, wx.BoxSizer]:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()
    dialog = wx.Dialog(None, title=title)
    root = wx.BoxSizer(wx.VERTICAL)
    dialog.SetSizer(root)
    return dialog, root


def test_declared_row_claims_its_control_and_outside_rows_hand_over(application) -> None:
    dialog, root = _dialog()
    tray = wx.CheckBox(dialog, label="Start minimized to the tray")
    root.Add(tray)
    # A real settings window has its buttons; a lone checkbox on a bare
    # dialog trips a wxMSW cast assertion on destroy on some desktops.
    root.Add(wx.Button(dialog, wx.ID_OK))
    gone: list[str] = []
    entries = [
        SettingEntry("tray", "Start minimized to the tray", aliases=("notification area",)),
        SettingEntry("rate", "Sample rate", "the main window's Advanced Options", "", ("hz",)),
    ]
    declare_settings(
        dialog,
        entries,
        lambda entry: gone.append(entry.key),
        control_for=lambda entry: tray if entry.key == "tray" else None,
    )
    try:
        search = install_preferences_search(dialog)
        dialog.Show()
        application.Yield()
        search.search.SetValue("tray")
        application.Yield()
        assert [t.label for t in search.matches] == ["Start minimized to the tray"]
        search.search.SetValue("notification area")  # an alias only the index knows
        application.Yield()
        assert len(search.matches) == 1 and search.matches[0].control is tray
        search._on_choose(None)
        application.Yield()
        assert wx.Window.FindFocus() is tray and tray.GetValue() is False
        search.search.SetValue("hz")
        application.Yield()
        assert search.results.GetString(0) == ("Sample rate, in the main window's Advanced Options")
        search._on_choose(None)
        assert gone == ["rate"]
        search.search.SetFocus()  # as a closing dialog would: never destroy under focus
    finally:
        dialog.Destroy()
        application.Yield()


def test_settings_pages_find_and_build_a_page_nobody_opened(application) -> None:
    from types import SimpleNamespace

    from quill.ui.preferences_search_registry import declare_settings_pages

    dialog, root = _dialog("Settings")
    notebook = wx.Notebook(dialog)
    first, second = wx.Panel(notebook), wx.Panel(notebook)
    notebook.AddPage(first, "General", True)
    notebook.AddPage(second, "Editing")
    root.Add(notebook, 1, wx.EXPAND)
    control_index: dict[str, tuple[int, object]] = {}
    built: list[int] = []

    def build_page(index: int) -> None:
        if index in built or index != 1:
            return
        built.append(index)
        check = wx.CheckBox(second, label="Spell check as you type")
        second.SetSizer(wx.BoxSizer(wx.VERTICAL))
        second.GetSizer().Add(check)
        control_index["spell"] = (1, check)

    group = SimpleNamespace(id="editing", title="Editing")
    spec = SimpleNamespace(
        key="spell",
        label="Spell check as you type",
        group="editing",
        description="",
        keywords=("typos",),
    )
    said: list[str] = []
    pages = declare_settings_pages(
        dialog, notebook, [(1, group, [spec])], build_page, control_index
    )
    try:
        search = install_preferences_search(dialog)
        dialog.Show()
        application.Yield()
        search.search.SetValue("typos")
        application.Yield()
        assert built == [] and len(search.matches) == 1
        assert search.results.GetString(0) == "Spell check as you type, in the Editing page"
        search._on_choose(None)
        application.Yield()
        assert built == [1] and notebook.GetSelection() == 1
        assert wx.Window.FindFocus() is control_index["spell"][1]
        # Opening Settings *at* a setting (the hub's route) says the page.
        notebook.SetSelection(0)
        assert pages.focus("spell", said.append) is not None
        assert notebook.GetSelection() == 1 and said == ["Moved to the Editing page."]
        assert pages.focus("no such key", said.append) is None
        search.search.SetFocus()
    finally:
        dialog.Destroy()
        application.Yield()


def test_hub_search_offers_settings_inside_an_unopened_dialog(application) -> None:
    from quill.ui.preferences_search_registry import declare_hub_settings

    dialog, root = _dialog("Preferences")
    root.Add(wx.Button(dialog, label="Open General..."))
    opened: list[str] = []
    declare_hub_settings(dialog, lambda feature: feature != "core.spellcheck", opened.append)
    try:
        search = install_preferences_search(dialog)
        dialog.Show()
        application.Yield()
        search.search.SetValue("wrap QUILL browse navigation")
        application.Yield()
        assert search.results.GetString(0) == (
            "Wrap QUILL browse navigation, in the Navigation and QUILL Key page of Settings"
        )
        search._on_choose(None)
        assert opened == ["browse_mode_wrap"]
        # A feature that is off is not offered: Settings would not draw it.
        search.search.SetValue("spell check as you type")
        application.Yield()
        assert all("Spell check as you type" not in t.label for t in search.matches)
    finally:
        dialog.Destroy()
        application.Yield()


def test_leaving_preferences_keeps_edits_or_cancels_truthfully(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.app_preferences_dialog import PreferenceCheckbox, PreferencesDialog

    went: list[str] = []
    elsewhere = SettingEntry("rate", "Sample rate", "the main window")

    def make() -> PreferencesDialog:
        return PreferencesDialog(
            None,
            app_title="Quill Converter",
            checkboxes=[PreferenceCheckbox("&Open", "Open it", False, key="open")],
            declared=[SettingEntry("open", "Open the folder"), elsewhere],
            go_elsewhere=lambda entry: went.append(entry.key),
        )

    for change, code in ((False, wx.ID_CANCEL), (True, wx.ID_OK)):
        surface = make()
        ended: list[int] = []
        monkeypatch.setattr(surface.dialog, "EndModal", ended.append)
        assert surface.controls_by_key["open"] is surface._checks[0]
        if change:
            surface._checks[0].SetValue(True)
        assert surface._leave_for(elsewhere) is None
        assert ended == [code] and surface.left_for == elsewhere
        assert surface._result == (None if not change else ([True], [], []))
        surface._after_close()
        surface.dialog.Destroy()
    assert went == ["rate", "rate"]
    application.Yield()


def test_quill_settings_and_hub_are_wired_to_the_registry() -> None:
    source = Path("quill/ui/main_frame_preferences.py").read_text(encoding="utf-8")
    hub = source[source.index("def open_preferences(self)") :]
    hub = hub[: hub.index("\n    def ")]
    assert "declare_hub_settings(dialog, self._feature_enabled, _open_at)" in hub
    assert "open_general_preferences(focus_key=key)" in hub
    settings = source[source.index("def open_general_preferences(") :]
    assert 'def open_general_preferences(self, focus_key: str = "")' in source
    assert "declare_settings_pages(" in settings
    assert "_pages.focus, focus_key, self._announce" in settings
