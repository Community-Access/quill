"""File > Recent Documents in QUILL Lite, and the recent list behind it.

Reported 2026-10-04 ("Unless I'm missing it, the ability to open recent
documents"): the Open Recent submenu was there and was not found. These drive
the shipped handler, the shipped menu builder and the shipped settings, with the
shared window patched where the handler imports it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.apps.lite_window_recent import DocumentRecentMixin
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite import commands as lite_commands
from quill.core.lite.settings import Settings
from quill.ui import recent_documents_dialog
from quill.ui.recent_documents_dialog import RecentDocumentsAnswer


class FakeApp:
    """Only what the recent commands reach for on the application."""

    def __init__(self, _tmp_path: Path, settings: Settings) -> None:
        self.settings = settings
        self.opened: list = []
        self.saved_settings = 0
        self.rebuilt_menus = 0

    def open_path(self, *args, **kwargs) -> bool:
        self.opened.append((args, kwargs))
        return True

    def save_settings(self) -> None:
        self.saved_settings += 1

    def refresh_all_menus(self) -> None:
        self.rebuilt_menus += 1


class _Control:
    def __init__(self) -> None:
        self.focused = 0

    def SetFocus(self) -> None:  # noqa: N802 - wx API shape
        self.focused += 1


class _Window(DocumentRecentMixin):
    def __init__(self, app: FakeApp) -> None:
        self.app = app
        self.control = _Control()
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


@pytest.fixture
def window(tmp_path: Path) -> _Window:
    settings = Settings()
    settings.recent_files = [str(tmp_path / "a.txt"), str(tmp_path / "b.txt")]
    return _Window(FakeApp(tmp_path, settings))


def _answer_with(monkeypatch: pytest.MonkeyPatch, answer: RecentDocumentsAnswer) -> list:
    asked: list = []

    def _show(parent, recent, pinned, **kwargs):
        asked.append((parent, list(recent), list(pinned), kwargs))
        return answer

    monkeypatch.setattr(recent_documents_dialog, "show_recent_documents", _show)
    return asked


def test_choosing_a_document_opens_it(window: _Window, monkeypatch, tmp_path) -> None:
    target = str(tmp_path / "b.txt")
    answer = RecentDocumentsAnswer(
        open_path=target, recent=tuple(window.app.settings.recent_files), limit=10
    )
    asked = _answer_with(monkeypatch, answer)
    window.cmd_recent_documents()
    assert asked[0][0] is window
    assert asked[0][3]["limit"] == 10
    assert window.app.opened == [((Path(target),), {})]
    assert window.app.saved_settings == 0  # nothing about the list changed


def test_pins_removals_and_preferences_are_saved_even_without_opening(
    window: _Window, monkeypatch, tmp_path
) -> None:
    kept = str(tmp_path / "a.txt")
    answer = RecentDocumentsAnswer(
        recent=(kept,), pinned=(kept,), limit=5, auto_clear_missing=True, changed=True
    )
    _answer_with(monkeypatch, answer)
    window.cmd_recent_documents()
    settings = window.app.settings
    assert settings.recent_files == [kept]
    assert settings.pinned_recent_files == [kept]
    assert settings.recent_files_limit == 5
    assert settings.recent_files_auto_clear_missing is True
    assert window.app.saved_settings == 1
    assert window.app.rebuilt_menus == 1
    assert window.app.opened == []
    assert window.control.focused == 1


def test_the_chord_is_alt_shift_0_in_both_editors() -> None:
    rows = [row for row in lite_commands.COMMANDS if row[3] == "cmd_recent_documents"]
    assert rows == [("&File", "Recent &Documents...", "Alt+Shift+0", "cmd_recent_documents", "")]
    assert DEFAULT_KEYMAP["file.recent_documents"] == "Alt+Shift+0"


def test_the_shortcut_list_names_it(window: _Window) -> None:
    text = lite_commands.shortcut_text()
    assert "Alt+Shift+0: Recent Documents..." in text


def test_remember_uses_the_shared_limit() -> None:
    settings = Settings()
    settings.recent_files_limit = 2
    for name in ("a.txt", "b.txt", "c.txt", "a.txt"):
        settings.remember_recent(name)
    assert settings.recent_files == ["a.txt", "c.txt"]


def test_the_limit_is_clamped_on_load() -> None:
    settings = Settings()
    settings.recent_files_limit = 900
    assert settings.normalized().recent_files_limit == 50


def test_pins_stay_on_this_computer() -> None:
    from quill.core.lite.settings import LOCAL_SETTINGS
    from quill.core.lite_bridge import _NOT_COPIED

    assert "pinned_recent_files" in LOCAL_SETTINGS
    assert "pinned_recent_files" in _NOT_COPIED


def test_launch_drops_deleted_files_only_when_asked(tmp_path, monkeypatch) -> None:
    import quill.core.recent as recent_module
    from quill.apps.lite_settings_persistence import LiteSettingsPersistenceMixin
    from quill.core.lite import settings as settings_mod

    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    stored = Settings()
    stored.recent_files = [str(here), str(tmp_path / "gone.txt")]
    monkeypatch.setattr(settings_mod, "load", lambda: stored)
    monkeypatch.setattr(recent_module, "_is_fixed_drive", lambda _p: True)
    loader = LiteSettingsPersistenceMixin()
    assert len(loader._load_settings().recent_files) == 2
    stored.recent_files_auto_clear_missing = True
    assert loader._load_settings().recent_files == [str(here)]


def test_the_open_recent_menu_puts_pins_first_and_numbers_them(
    tmp_path, monkeypatch, wx_app
) -> None:
    import wx

    from quill.apps.lite_window_menus import DocumentMenuMixin

    one = tmp_path / "one.txt"
    two = tmp_path / "two.txt"
    for target in (one, two):
        target.write_text("x", encoding="utf-8")
    settings = Settings()
    settings.recent_files = [str(one), str(two)]
    settings.pinned_recent_files = [str(two)]

    class _Menus(DocumentMenuMixin):
        def __init__(self) -> None:
            self.app = FakeApp(tmp_path, settings)
            self._recent_menu = wx.Menu()

        def Bind(self, *_args, **_kwargs) -> None:  # noqa: N802 - wx API shape
            return None

    menus = _Menus()
    menus.refresh_recent_menu()
    labels = [item.GetItemLabel() for item in menus._recent_menu.GetMenuItems()]
    assert labels[0].startswith("&1 two.txt") and labels[0].endswith("pinned\tAlt+Shift+1")
    assert labels[1].startswith("&2 one.txt") and labels[1].endswith("\tAlt+Shift+2")
    menus._recent_menu.Destroy()
