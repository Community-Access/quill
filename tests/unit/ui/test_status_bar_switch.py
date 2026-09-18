"""The whole status bar has a switch now (bad.md G3, P1.10).

QUILL could hide any individual *cell* and not the bar itself. Somebody who
wanted Notepad's plain window had to empty a list of cell names and still give
up a row of the screen to a bar with nothing in it. Notepad has had
View > Status Bar on Alt+Shift+B for decades; QuillLite has had it since it
shipped, under this setting name.
"""

from __future__ import annotations

from quill.ui.main_frame_statusbar import StatusBarMixin


class _Bar:
    def __init__(self) -> None:
        self.shown: list[bool] = []

    def Show(self, show: bool) -> None:
        self.shown.append(show)


class _Frame:
    def __init__(self) -> None:
        self.layouts = 0

    def Layout(self) -> None:
        self.layouts += 1


def _host() -> tuple[StatusBarMixin, _Bar, list[str]]:
    from quill.core.settings import Settings

    host = StatusBarMixin.__new__(StatusBarMixin)
    bar, said = _Bar(), []
    host.settings = Settings()  # type: ignore[attr-defined]
    host.statusbar = bar  # type: ignore[attr-defined]
    host.frame = _Frame()  # type: ignore[attr-defined]
    host._announce_result = said.append  # type: ignore[attr-defined,method-assign]
    host._save_settings_quietly = lambda: None  # type: ignore[attr-defined,method-assign]
    return host, bar, said


def test_the_setting_starts_on() -> None:
    """A status bar you have to go and find is worse than one you can turn off."""
    from quill.core.settings import Settings

    assert Settings().show_status_bar is True


def test_the_toggle_flips_the_setting_and_the_bar() -> None:
    host, bar, _said = _host()
    host.toggle_status_bar()
    assert host.settings.show_status_bar is False
    assert bar.shown == [False]
    host.toggle_status_bar()
    assert host.settings.show_status_bar is True
    assert bar.shown == [False, True]


def test_it_says_which_way_it_went() -> None:
    """Nothing else will. A bar leaving the window is not a focus change and
    not a control the reader was on, so the sentence is the only evidence the
    key did anything -- and the state is what somebody pressing a toggle needs."""
    host, _bar, said = _host()
    host.toggle_status_bar()
    host.toggle_status_bar()
    assert said == ["Status bar hidden", "Status bar shown"]


def test_applying_it_relays_out_the_frame() -> None:
    host, _bar, _said = _host()
    host.apply_status_bar_visibility()
    assert host.frame.layouts == 1


def test_a_torn_down_bar_is_not_an_error() -> None:
    """The bar is a panel that may be mid-teardown, and a view preference is
    not worth failing a settings save for."""
    host, _bar, _said = _host()
    host.statusbar = None  # type: ignore[attr-defined]
    host.apply_status_bar_visibility()  # must not raise


def test_a_bar_that_raises_is_not_an_error_either() -> None:
    host, _bar, _said = _host()

    class _Dead:
        def Show(self, _show: bool) -> None:
            raise RuntimeError("wrapped C++ object has been deleted")

    host.statusbar = _Dead()  # type: ignore[attr-defined]
    host.apply_status_bar_visibility()  # must not raise


def test_both_editors_call_the_setting_the_same_thing() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    assert LiteSettings().show_status_bar == QuillSettings().show_status_bar


def test_notepads_chord_and_the_displacement_it_cost() -> None:
    """Alt+Shift+B was List Bookmarks here. It moved onto its own alias --
    Word's Ctrl+Shift+F5 -- so nothing was lost, and two days later onto
    QuillLite's Alt+Shift+G under rule 6, with Word's key back as the alias and
    a legacy_rebindings hop for anyone who saved the original."""
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["view.toggle_status_bar"] == "Alt+Shift+B"
    assert DEFAULT_KEYMAP["navigate.list_bookmarks"] == "Alt+Shift+G"
    assert DEFAULT_ALIASES["navigate.list_bookmarks"] == "Ctrl+Shift+F5"
