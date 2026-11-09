"""QUILL Lite's Help > Open User Guide and Open GitHub Guide, as the menu runs them."""

from __future__ import annotations

import pytest

pytest.importorskip("wx")

from quill.ui import guide_opener  # noqa: E402


@pytest.fixture
def opened(monkeypatch) -> list[str]:
    urls: list[str] = []
    monkeypatch.setattr(guide_opener.webbrowser, "open", lambda url: urls.append(url) or True)
    return urls


def test_open_user_guide_renders_quill_lites_guide(lite_window, monkeypatch, tmp_path, opened):
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(tmp_path / "data"))
    source = tmp_path / "docs" / "userguide.md"
    source.parent.mkdir()
    source.write_text("# QUILL Lite User Guide\n\nHello.\n", encoding="utf-8")
    asked: list[tuple[str, str]] = []

    def fake_find(product, guide, **_kw):
        asked.append((product, guide))
        return source

    monkeypatch.setattr(guide_opener, "find_guide", fake_find)
    win = lite_window("text")
    win.cmd_user_guide()
    assert asked == [("quilllite", "user")]
    assert opened == [(tmp_path / "data" / "user-guide" / "userguide.html").as_uri()]
    assert win.app.voice.said[-1] == "Opened user guide in browser"


def test_open_user_guide_says_when_there_is_none(lite_window, monkeypatch, opened) -> None:
    monkeypatch.setattr(guide_opener, "find_guide", lambda *_a, **_k: None)
    win = lite_window("text")
    win.cmd_user_guide()
    assert opened == []
    assert win.app.voice.said[-1] == "The user guide is not in this copy of QUILL Lite."


def test_open_github_guide_opens_the_shipped_page(lite_window, opened) -> None:
    win = lite_window("text")
    win.cmd_github_guide()
    assert opened[-1].endswith("github-guide/lite-github-guide.html")
    assert win.app.voice.said[-1] == "Opened GitHub Guide in browser"


def test_both_rows_are_on_the_help_menu_with_quills_keys() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands_help import HELP_ROWS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    rows = {handler: (label, key) for _menu, label, key, handler, _kind in HELP_ROWS}
    assert rows["cmd_user_guide"] == ("&Open User Guide", "Ctrl+Shift+F1")
    assert rows["cmd_github_guide"] == ("Open GitHub Gu&ide", "")
    assert DEFAULT_KEYMAP[COMMAND_EQUIVALENTS["cmd_user_guide"]] == "Ctrl+Shift+F1"
    assert DEFAULT_KEYMAP[COMMAND_EQUIVALENTS["cmd_github_guide"]] == ""


def test_the_empty_window_reaches_both_guides() -> None:
    from quill.apps.lite_shell_menu import NO_DOCUMENT_COMMANDS

    assert {"cmd_user_guide", "cmd_github_guide"} <= set(NO_DOCUMENT_COMMANDS)


def test_f1_in_a_github_window_speaks_through_the_shell(monkeypatch, opened) -> None:
    from types import SimpleNamespace

    from quill.apps.lite_guides import register_lite_github_guide_help
    from quill.ui import app_context_help

    monkeypatch.setattr(app_context_help, "_guide_routes", [])
    said: list[str] = []
    app = SimpleNamespace(shell=SimpleNamespace(_announce=said.append))
    register_lite_github_guide_help(app)
    route = app_context_help.guide_route_for("Explore GitHub")
    assert route is not None
    route[1]()
    assert opened[-1].endswith("github-guide/lite-github-guide.html")
    assert said == ["Opened GitHub Guide in browser"]
