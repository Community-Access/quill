from types import SimpleNamespace

import pytest
import wx

from quill.ui.preferences_search import SettingTarget, find_settings, install_preferences_search


@pytest.fixture
def application():
    existing = wx.GetApp()
    app = existing or wx.App(False)
    yield app
    if existing is None:
        app.Destroy()


def test_search_uses_labels_and_help_not_values():
    targets = [SettingTarget("Sound", "Choose an output device", object())]
    assert find_settings(targets, "OUTPUT sound") == targets
    assert find_settings(targets, "password") == []
    assert find_settings(targets, "") == []


@pytest.mark.machine_global
def test_live_search_finds_hidden_pages_and_does_not_save(application):
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()
    dialog = wx.Dialog(None, title="Test Preferences")
    root = wx.BoxSizer(wx.VERTICAL)
    book = wx.Notebook(dialog)
    first = wx.Panel(book)
    second = wx.Panel(book)
    book.AddPage(first, "General", True)
    book.AddPage(second, "Audio")
    label = wx.StaticText(second, label="Volume:")
    volume = wx.SpinCtrl(second, min=0, max=100, initial=70)
    volume.SetHelpText("The playback sound level")
    page = wx.BoxSizer(wx.VERTICAL)
    page.Add(label)
    page.Add(volume)
    second.SetSizer(page)
    root.Add(book, 1, wx.EXPAND)
    dialog.SetSizer(root)
    spoken = []
    try:
        search = install_preferences_search(dialog, announce=spoken.append)
        assert search is not None
        assert install_preferences_search(dialog) is search
        dialog.Show()
        application.Yield()
        search.search.SetValue("sound")
        application.Yield()
        assert len(search.matches) == 1
        assert book.GetSelection() == 0
        search._on_choose(None)
        application.Yield()
        assert book.GetSelection() == 1
        assert wx.Window.FindFocus() is volume
        assert volume.GetValue() == 70
        search.search.SetValue("nothing matches")
        application.Yield()
        assert search.matches == []
        search._report_count()
        assert spoken[-1] == "0 matching settings"
        search.close()
        search._report_count()
        assert len(spoken) == 1
    finally:
        dialog.Destroy()
        application.Yield()


def test_non_settings_surfaces_are_unchanged():
    assert install_preferences_search(SimpleNamespace(GetTitle=lambda: "Open File")) is None


@pytest.mark.machine_global
def test_lite_preferences_search_is_available_without_committing_changes(monkeypatch, application):
    from quill.apps import lite_preferences
    from quill.core.lite.settings import Settings
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()
    settings = Settings()
    found = []

    def cancel_with_search(dialog, _label):
        search = install_preferences_search(dialog)
        search.search.SetValue("recovery")
        search._on_search(None)
        found.extend(search.matches)
        search.close()
        return wx.ID_CANCEL

    monkeypatch.setattr(lite_preferences, "show_modal_dialog", cancel_with_search)
    result = lite_preferences.edit_preferences(None, settings)
    application.Yield()
    assert found
    assert not result.changed
    assert settings == Settings()


@pytest.mark.machine_global
def test_live_companion_preferences_search_and_keyboard_preserve_values(application):
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.app_preferences_dialog import PreferenceCheckbox, PreferencesDialog

    ensure_help_provider()
    surface = PreferencesDialog(
        None,
        app_title="Quill Radio",
        checkboxes=[PreferenceCheckbox("Resume on launch", "Restore playback on startup", True)],
    )
    try:
        search = install_preferences_search(surface.dialog)
        surface.dialog.Show()
        application.Yield()
        search.search.SetValue("resume")
        application.Yield()
        assert search.matches[0].control is surface._checks[0]
        search.search.SetFocus()
        application.Yield()
        skipped = []
        event = SimpleNamespace(
            GetKeyCode=lambda: wx.WXK_RETURN,
            ControlDown=lambda: False,
            Skip=lambda: skipped.append(True),
        )
        search._on_key(event)
        application.Yield()
        assert wx.Window.FindFocus() is surface._checks[0]
        assert surface._result is None
        assert surface._checks[0].GetValue() is True
        assert skipped == []
        surface._checks[0].Disable()
        search.search.SetFocus()
        search._on_key(event)
        assert wx.Window.FindFocus() is search.search
        event.GetKeyCode = lambda: wx.WXK_ESCAPE
        search._on_key(event)
        assert search.search.GetValue() == ""
        search._on_key(event)
        assert skipped == [True]
    finally:
        surface.dialog.Destroy()
        application.Yield()
