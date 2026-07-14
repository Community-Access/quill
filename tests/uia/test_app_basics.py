"""First-wave UIA regressions: launch, title truth, typing, and spoken output."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.uia


def test_app_launches_with_versioned_title(quill_app) -> None:
    # The window title carries the product name and version (#615): it is the
    # one in-process channel every screen reader can read on demand.
    title = quill_app.main_window.window_text()
    assert "QUILL for All" in title
    assert "Untitled" in title


def test_menu_bar_present_with_named_menus(quill_app) -> None:
    # wx exposes two MenuBar elements (the window's system menu and the app
    # menu bar); the app one is the one that contains File.
    bars = quill_app.main_window.descendants(control_type="MenuBar")
    assert bars, "no menu bar found"
    all_names: list[list[str]] = [[item.window_text() for item in bar.items()] for bar in bars]
    app_menus = next((names for names in all_names if any("File" in n for n in names)), None)
    assert app_menus is not None, f"no menu bar contains File: {all_names}"
    assert not [n for n in app_menus if not n.strip()], f"unnamed menus: {app_menus}"
    joined = " ".join(app_menus)
    for expected in ("Edit", "Tools", "Help"):
        assert expected in joined, f"expected menu {expected!r} in {app_menus}"


def _wait_title(quill_app, fragment: str, timeout: float = 10.0) -> str:
    import time

    deadline = time.monotonic() + timeout
    title = ""
    while time.monotonic() < deadline:
        title = quill_app.main_window.window_text()
        if fragment in title:
            return title
        time.sleep(0.25)
    raise AssertionError(f"title never contained {fragment!r}; last title: {title!r}")


def test_typing_reaches_the_editor(quill_app) -> None:
    # QUILL focuses the editor on launch; typing at the window goes there —
    # exactly the keystroke path a real user's hands take. The title gaining
    # [modified] is the product's own proof the keystrokes became document text.
    quill_app.main_window.set_focus()
    quill_app.main_window.type_keys("Hello from the UIA harness", with_spaces=True)
    _wait_title(quill_app, "[modified]")


def test_describe_formatting_is_announced(quill_app) -> None:
    # Ctrl+Shift+D speaks the formatting at the caret. The assertion reads the
    # announcement trace — the same channel a screen reader hears — so a
    # regression that silences the command fails here, not on a user.
    quill_app.main_window.set_focus()
    quill_app.main_window.type_keys("spoken check", with_spaces=True)
    _wait_title(quill_app, "[modified]")
    quill_app.main_window.type_keys("^+d")
    # Any honest response mentions formatting (either the description itself
    # or the "available in Markdown documents" availability notice).
    quill_app.wait_spoken("formatting", timeout=15)
