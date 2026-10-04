"""qc.md X-01: settings search reaches what it could not -- menu-only apps and
Cast Preferences' sections that are not built yet."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.machine_global


@pytest.fixture(scope="module")
def app():
    application = wx.App()
    yield application
    application.Destroy()


def test_menu_rows_carry_path_and_state(app) -> None:
    from quill.ui.menu_palette import find, menu_rows

    frame = wx.Frame(None)
    bar = wx.MenuBar()
    options = wx.Menu()
    options.AppendCheckItem(wx.ID_ANY, "&Announce every expansion\tCtrl+Alt+A")
    options.Append(wx.ID_ANY, "E&xcluded Applications...")
    bar.Append(options, "&Options")
    frame.SetMenuBar(bar)
    rows = menu_rows(bar)
    assert [r.spoken() for r in find(rows, "announce")] == [
        "Announce every expansion, off -- Options"
    ]
    assert find(rows, "excluded apps") == []
    frame.Destroy()


def test_running_a_check_row_toggles_and_says_so(app) -> None:
    from quill.ui import menu_palette

    frame = wx.Frame(None)
    bar = wx.MenuBar()
    options = wx.Menu()
    item = options.AppendCheckItem(wx.ID_ANY, "&Close to tray")
    bar.Append(options, "&Options")
    frame.SetMenuBar(bar)
    seen: list[bool] = []
    frame.Bind(wx.EVT_MENU, lambda e: seen.append(e.IsChecked()), id=item.GetId())
    said: list[str] = []
    host = SimpleNamespace(frame=frame, _announce=said.append)
    row = menu_palette.menu_rows(bar)[0]
    menu_palette._run(host, row)
    assert seen == [True] and item.IsChecked()
    assert said == ["Close to tray, on."]
    frame.Destroy()


def test_cast_preferences_index_reaches_every_section(app) -> None:
    from quill.apps.podcasts_preferences import app_rows
    from quill.core.podcasts.history import PodcastHistory
    from quill.core.podcasts.subscriptions import PodcastLibrary
    from quill.ui.podcasts.preferences_window import CastPreferencesWindow
    from quill.ui.preferences_search import find_settings

    parent = wx.Frame(None)
    window = CastPreferencesWindow(
        parent,
        library=PodcastLibrary(),
        history=PodcastHistory(),
        app_rows=app_rows(SimpleNamespace(open_cast_data_folder=lambda: None)),
        summary=lambda: "",
    )
    index = window.dialog._quill_settings_index()
    matches = find_settings(index, "watched folder original")
    assert matches and matches[0].label.startswith("Data:")
    assert window._current_section() != "data"
    control = matches[0].reveal()
    assert window._current_section() == "data"
    assert control is not None
    window.dialog.Destroy()
    parent.Destroy()
