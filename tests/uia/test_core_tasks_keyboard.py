"""Keyboard-only runs of the core tasks in docs/accessibility-testing.md.

Every step here is a real key press sent to the running app; nothing is
clicked and no control is driven through UI Automation patterns. UIA is used
only to *look*: which window is open, where focus is, what the title says,
and what QUILL announced (the announcement trace). That is the keyboard-only
smoke test the Open Source Accessibility Framework asks for, run on CI where
it cannot fight a screen reader.

Task 1 (installer and setup wizard) is not here: the fixture seeds a profile
with the wizard completed, and the installer is not built on this runner.
"""

from __future__ import annotations

import json
import time

import pytest

from tests.uia.a11y_scan import scan_window, summarize, unnamed_focusable

pytestmark = pytest.mark.uia

_SPECIAL = set("+^%~(){}[]")


def _literal(text: str) -> str:
    """Escape pywinauto's send-keys syntax so *text* is typed as written."""
    return "".join("{" + ch + "}" if ch in _SPECIAL else ch for ch in text)


def _wait_title(quill_app, fragment: str, *, present: bool = True, timeout: float = 15.0) -> str:
    deadline = time.monotonic() + timeout
    title = ""
    while time.monotonic() < deadline:
        title = quill_app.main_window.window_text()
        if (fragment in title) == present:
            return title
        time.sleep(0.25)
    verb = "contained" if present else "lost"
    raise AssertionError(f"title never {verb} {fragment!r}; last title: {title!r}")


def _open_window(quill_app, keys: str, title_fragment: str, attempts: int = 3):
    """Press *keys* in the editor until a window titled *title_fragment* opens."""
    last_error: Exception | None = None
    for _ in range(attempts):
        gone = quill_app.exit_status()
        if gone:
            raise AssertionError(f"{gone}, so {keys!r} has nothing to type into")
        quill_app.main_window.set_focus()
        quill_app.main_window.type_keys(keys)
        window = quill_app.main_window.child_window(
            title_re=f".*{title_fragment}.*", control_type="Window"
        )
        try:
            window.wait("exists visible", timeout=8)
            return window
        except Exception as exc:  # noqa: BLE001 - a foreground race; retry the key
            last_error = exc
    raise AssertionError(
        f"{title_fragment!r} never opened via {keys!r}: {last_error}; "
        f"windows open: {_window_titles(quill_app)!r}; spoken: {quill_app.spoken()!r}"
    )


def _window_titles(quill_app) -> list[str]:
    """Titles of every window the QUILL process has open, for a failure message."""
    try:
        from pywinauto import Desktop

        return [
            w.window_text() for w in Desktop(backend="uia").windows(process=quill_app.process.pid)
        ] + [w.window_text() for w in quill_app.main_window.children(control_type="Window")]
    except Exception as exc:  # noqa: BLE001 - diagnostics must never mask the failure
        return [f"(could not list windows: {exc})"]


def _focused_handle_chain() -> list[int]:
    """Window handles from the focused element up to the desktop."""
    from pywinauto.uia_defines import IUIA
    from pywinauto.uia_element_info import UIAElementInfo

    info = UIAElementInfo(IUIA().get_focused_element())
    handles: list[int] = []
    while info is not None:
        handle = info.handle
        if handle:
            handles.append(int(handle))
        info = info.parent
    return handles


def _assert_focus_inside(window, what: str) -> None:
    handle = int(window.wrapper_object().handle)
    assert handle in _focused_handle_chain(), f"keyboard focus left {what}"


def _assert_closes(window, what: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if not window.exists(timeout=0.5):
                return
        except Exception:  # noqa: BLE001 - a destroyed window counts as closed
            return
        time.sleep(0.25)
    raise AssertionError(f"Escape did not close {what}")


def _assert_named(window, what: str) -> None:
    # A tab control's container has no name of its own: wx cannot set one on
    # Windows yet (#1693, the upstream SetAccessibleName blocker). Its tab
    # items are named, and they are what a screen reader reads on arrival.
    offenders = [r for r in unnamed_focusable(scan_window(window)) if r.control_type != "Tab"]
    assert not offenders, f"{what}: keyboard-reachable controls without names:\n" + "\n".join(
        summarize(offenders)
    )


def _tab_round(window, what: str, presses: int = 12) -> None:
    """Tab forward and back through *window*; focus must never leave it."""
    for _ in range(presses):
        window.type_keys("{TAB}")
        _assert_focus_inside(window, what)
    for _ in range(presses):
        window.type_keys("+{TAB}")
        _assert_focus_inside(window, what)


def _assert_focus_back_in_main(quill_app) -> None:
    deadline = time.monotonic() + 10
    handle = int(quill_app.main_window.wrapper_object().handle)
    while time.monotonic() < deadline:
        if handle in _focused_handle_chain():
            return
        time.sleep(0.25)
    raise AssertionError("focus did not return to the QUILL window after the dialog closed")


def test_core_task_2_open_and_move_by_heading(quill_app) -> None:
    # Ctrl+O, type the path in the standard Open dialog, Enter; then Next
    # Heading (Ctrl+Alt+H) and hear the heading's level and text.
    sample = quill_app.documents_dir / "headings-sample.md"
    dialog = _open_window(quill_app, "^o", "Open")
    dialog.type_keys(_literal(str(sample)) + "{ENTER}", with_spaces=True)
    _wait_title(quill_app, "headings-sample")
    _assert_focus_back_in_main(quill_app)
    quill_app.main_window.type_keys("^{HOME}")
    quill_app.main_window.type_keys("^%h")
    quill_app.wait_spoken("Second section", timeout=15)
    quill_app.main_window.type_keys("^%h")
    quill_app.wait_spoken("Third section", timeout=15)


def test_core_task_3_write_and_save(quill_app) -> None:
    # Type a heading and a paragraph, Ctrl+S on the untitled document opens
    # Save As; type a path, Enter; the file is written and the title says so.
    target = quill_app.documents_dir / "written-by-keyboard.md"
    quill_app.main_window.set_focus()
    quill_app.main_window.type_keys(
        _literal("# Keyboard heading") + "{ENTER}{ENTER}" + "Typed without a mouse.",
        with_spaces=True,
    )
    _wait_title(quill_app, "[modified]")
    dialog = _open_window(quill_app, "^s", "Save")
    # Alt+N is the common file dialog's own key for "File name:", so the path
    # lands there whichever pane the dialog chose to focus first.
    dialog.type_keys("%n^a" + _literal(str(target)) + "{ENTER}", with_spaces=True)
    try:
        _wait_title(quill_app, "written-by-keyboard")
    except AssertionError as exc:
        raise AssertionError(
            f"{exc}; windows open: {_window_titles(quill_app)!r}; spoken: {quill_app.spoken()!r}"
        ) from exc
    _wait_title(quill_app, "[modified]", present=False)
    text = target.read_text(encoding="utf-8")
    assert "Keyboard heading" in text and "Typed without a mouse." in text
    quill_app.wait_spoken("Saved", timeout=15)
    _assert_focus_back_in_main(quill_app)


def test_core_task_4_find_and_replace(quill_app) -> None:
    # Ctrl+F finds; Ctrl+H, type the find and replace text, Alt+A (Replace
    # All), and hear the count. Escape closes each dialog.
    quill_app.main_window.set_focus()
    quill_app.main_window.type_keys("alpha beta alpha gamma", with_spaces=True)
    _wait_title(quill_app, "[modified]")

    find = _open_window(quill_app, "^f", "Find")
    _assert_named(find, "Find")
    _tab_round(find, "the Find dialog", presses=8)
    find.type_keys("{ESC}")
    _assert_closes(find, "the Find dialog")
    _assert_focus_back_in_main(quill_app)

    replace = _open_window(quill_app, "^h", "Replace")
    _assert_named(replace, "Replace")
    replace.type_keys("^a" + "alpha" + "{TAB}" + "omega", with_spaces=True)
    replace.type_keys("%a")
    quill_app.wait_spoken("Replaced 2", timeout=15)
    _tab_round(replace, "the Replace dialog", presses=10)
    replace.type_keys("{ESC}")
    _assert_closes(replace, "the Replace dialog")
    _assert_focus_back_in_main(quill_app)


def test_core_task_5_change_a_setting(quill_app) -> None:
    # Ctrl+, opens Settings; Ctrl+F reaches Find a setting; type, Enter moves
    # to the setting, Space changes it, Enter is OK. The saved settings file
    # is the proof the change took.
    settings_file = quill_app.data_dir / "settings.json"
    dialog = _open_window(quill_app, "^,", "Settings")
    _assert_named(dialog, "Settings")
    _tab_round(dialog, "the Settings dialog", presses=15)
    dialog.type_keys("^f")
    dialog.type_keys("wrap find searches", with_spaces=True)
    quill_app.wait_spoken("matching settings", timeout=15)
    dialog.type_keys("{ENTER}")
    time.sleep(0.5)
    dialog.type_keys("{SPACE}")
    dialog.type_keys("{ENTER}")
    _assert_closes(dialog, "the Settings dialog")
    deadline = time.monotonic() + 15
    saved: dict[str, object] = {}
    while time.monotonic() < deadline:
        try:
            saved = json.loads(settings_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        if saved.get("wrap_find") is False:
            break
        time.sleep(0.25)
    assert saved.get("wrap_find") is False, (
        f"Wrap find searches was not turned off; wrap_find={saved.get('wrap_find')!r}"
    )
    _assert_focus_back_in_main(quill_app)


def test_core_task_6_help_and_support(quill_app) -> None:
    # F1 in the editor opens help for it; Escape returns. Ctrl+Alt+F2 opens
    # Get Help from Support, which is reviewed and closed without sending.
    help_window = _open_window(quill_app, "{F1}", "Help")
    _assert_named(help_window, "Context help")
    _tab_round(help_window, "the help window", presses=6)
    help_window.type_keys("{ESC}")
    _assert_closes(help_window, "the help window")
    _assert_focus_back_in_main(quill_app)

    # Through the Help menu (Alt+H, then L for "Get He&lp from Support"), the
    # route the menu teaches. The Ctrl+Alt+F2 chord is checked on its own below.
    support = _open_window(quill_app, "%hl", "Get Help from Support")
    _assert_named(support, "Get Help from Support")
    _tab_round(support, "Get Help from Support", presses=12)
    support.type_keys("{ESC}")
    _assert_closes(support, "Get Help from Support")
    _assert_focus_back_in_main(quill_app)


def test_core_task_6_support_chord(quill_app) -> None:
    # The documented chord for Get Help from Support, Ctrl+Alt+F2. Kept apart
    # from the menu route so a chord problem cannot hide the task passing.
    support = _open_window(quill_app, "^%{F2}", "Get Help from Support")
    support.type_keys("{ESC}")
    _assert_closes(support, "Get Help from Support")
