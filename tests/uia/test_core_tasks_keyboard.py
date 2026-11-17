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

import contextlib
import json
import time
import warnings

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


def _window_inventory(quill_app) -> list[str]:
    """Every top-level window of the process: class, title, and what it holds."""
    try:
        from pywinauto import Desktop

        found = []
        for window in Desktop(backend="uia").windows(process=quill_app.process.pid):
            info = window.element_info
            texts = []
            for child in window.descendants()[:40]:
                name = child.window_text()
                if name:
                    texts.append(f"{child.element_info.control_type}:{name}")
            found.append(
                f"[{info.class_name!r} {window.window_text()!r} visible={window.is_visible()} "
                f"rect={window.rectangle()} holds={texts[:15]}]"
            )
        return found
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


def _focused_name() -> str:
    """The accessible name and type of whatever has keyboard focus."""
    from pywinauto.uia_defines import IUIA
    from pywinauto.uia_element_info import UIAElementInfo

    try:
        info = UIAElementInfo(IUIA().get_focused_element())
        return f"{info.name} ({info.control_type})"
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        return f"(unknown: {exc})"


def _focused_toggle_state() -> str:
    """The focused check box's state as UIA reports it: 0 off, 1 on."""
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.uia_defines import IUIA
    from pywinauto.uia_element_info import UIAElementInfo

    try:
        info = UIAElementInfo(IUIA().get_focused_element())
        return str(UIAWrapper(info).get_toggle_state())
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        return f"(unknown: {exc})"


def _assert_focus_inside(window, what: str) -> None:
    handle = int(window.wrapper_object().handle)
    assert handle in _focused_handle_chain(), f"keyboard focus left {what}"


def _assert_closes(window, what: str, timeout: float = 10.0, *, key: str = "Escape") -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if not window.exists(timeout=0.5):
                return
        except Exception:  # noqa: BLE001 - a destroyed window counts as closed
            return
        time.sleep(0.25)
    raise AssertionError(f"{key} did not close {what}")


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


def _file_name_box(dialog) -> str:
    """What the common file dialog's File name box holds (1001 is its id)."""
    try:
        box = dialog.child_window(auto_id="1001", control_type="Edit")
        return str(box.get_value())
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        return f"(unreadable: {exc})"


@contextlib.contextmanager
def _no_autosuggest():
    """Windows' AutoSuggest off for this user while the block runs, then put back.

    HKCU's ``AutoComplete\\AutoSuggest`` is what the file dialogs' File name
    box reads when it starts; "no" leaves the box a plain edit field.
    """
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\AutoComplete"
    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
    try:
        try:
            before: object = winreg.QueryValueEx(key, "AutoSuggest")[0]
        except FileNotFoundError:
            before = None
        winreg.SetValueEx(key, "AutoSuggest", 0, winreg.REG_SZ, "no")
        try:
            yield
        finally:
            if before is None:
                winreg.DeleteValue(key, "AutoSuggest")
            else:
                winreg.SetValueEx(key, "AutoSuggest", 0, winreg.REG_SZ, str(before))
    finally:
        winreg.CloseKey(key)


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
    with _no_autosuggest():
        _save_as(quill_app, target)
    _wait_title(quill_app, "[modified]", present=False)
    text = target.read_text(encoding="utf-8")
    assert "Keyboard heading" in text and "Typed without a mouse." in text
    quill_app.wait_spoken("Saved", timeout=15)
    _assert_focus_back_in_main(quill_app)


def _dialog_ready(dialog, timeout: float = 10.0) -> None:
    """Wait until Save As has finished filling its folder view and its Save button is on.

    The common dialog takes keys before it has finished enumerating the folder
    it opened on, and while it is still doing that it ignores OK: the path is
    in the box, focus is on it, and Enter does nothing. On the hosted runner
    that race lost about one night in three from 2026-11-01 on, on commits
    that had passed the night before, which is how it showed itself to be the
    runner's timing and not QUILL's.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.suppress(Exception):
            button = dialog.child_window(title="Save", control_type="Button")
            if button.exists(timeout=0.2) and button.is_enabled():
                view = dialog.child_window(class_name="DirectUIHWND")
                if not view.exists(timeout=0.2) or view.is_visible():
                    time.sleep(0.75)  # the view is drawn; let its enumeration finish
                    return
        time.sleep(0.25)


def _save_as(quill_app, target) -> None:
    """Ctrl+S on an untitled document, a path typed into Save As, Enter."""
    dialog = _open_window(quill_app, "^s", "Save")
    # Alt+N is the common file dialog's own key for "File name:", so focus
    # lands there whichever pane the dialog chose first. A value set through
    # UI Automation is not seen by the dialog at all, so the run types as a
    # person would, with AutoSuggest off (_no_autosuggest). When the dialog
    # was still busy and ignored Enter, it is typed and pressed again, as a
    # person would; never by its Save button, which on the runner closed the
    # dialog without saving.
    typed = ""
    tries = 0
    while tries < 3:
        tries += 1
        _dialog_ready(dialog)
        dialog.type_keys("%n^a" + _literal(str(target)), with_spaces=True)
        typed = _file_name_box(dialog)
        dialog.type_keys("{ENTER}")
        try:
            _assert_closes(dialog, "Save file as", timeout=4, key="Enter")
            break
        except AssertionError:
            continue
    if tries > 1:
        warnings.warn(f"Save As took Enter on attempt {tries}", stacklevel=2)
    route = "Enter"
    try:
        _assert_closes(dialog, "Save file as", timeout=5, key=route)
        _wait_title(quill_app, "written-by-keyboard")
    except AssertionError as exc:
        raise AssertionError(
            f"{exc}; file name box held {typed!r} before Enter and "
            f"{_file_name_box(dialog)!r} after; the file "
            f"{'exists' if target.exists() else 'does not exist'}; focus on "
            f"{_focused_name()!r}; windows open: {_window_inventory(quill_app)!r}; "
            f"spoken: {quill_app.spoken()!r}"
        ) from exc


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
    from pywinauto.keyboard import send_keys

    # After the first key, send_keys types into whatever has focus, as hands
    # do; type_keys would refocus the dialog before every string.
    dialog.type_keys("^f")
    time.sleep(0.5)
    in_search = _focused_name()
    send_keys("wrap find searches", with_spaces=True)
    try:
        quill_app.wait_spoken("matching settings", timeout=15)
    except AssertionError as exc:
        raise AssertionError(
            f"{exc}; focus after Ctrl+F was on {in_search!r}, now on {_focused_name()!r}"
        ) from exc
    send_keys("{ENTER}")
    time.sleep(0.5)
    on_setting = _focused_name()
    before_space = _focused_toggle_state()
    send_keys("{SPACE}")
    time.sleep(0.3)
    after_space = _focused_name()
    toggled = _focused_toggle_state()
    send_keys("{ENTER}")
    try:
        _assert_closes(dialog, "the Settings dialog", key="Enter")
    except AssertionError as exc:
        # The nightly run has failed here since 2026-11-12; say where focus
        # was at each step so the log shows which key went astray.
        raise AssertionError(
            f"{exc}; focus after Enter on the match was on {on_setting!r}, after "
            f"Space on {after_space!r}, after the last Enter on {_focused_name()!r}; "
            f"spoken: {quill_app.spoken()[-5:]!r}"
        ) from exc
    deadline = time.monotonic() + 15
    saved: dict[str, object] = {}
    while time.monotonic() < deadline:
        try:
            document = json.loads(settings_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            document = {}
        # Settings are saved as {"groups": {"editing": {"wrap_find": false}}}
        # (SET-5), so the key is looked for in every group, not at the top.
        saved = {}
        for group in (document.get("groups") or {}).values():
            if isinstance(group, dict):
                saved.update(group)
        if saved.get("wrap_find") is False:
            break
        time.sleep(0.25)
    assert saved.get("wrap_find") is False, (
        f"Wrap find searches was not turned off; wrap_find={saved.get('wrap_find')!r}; "
        f"its check box went from {before_space} to {toggled} on Space; "
        f"settings.json held {document!r}; spoken: {quill_app.spoken()[-5:]!r}"
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
    # #1703: "^%{F2}" reached QUILL as a bare F2 on the runner (it said "No
    # bookmarks in this document", Next Bookmark's line), so Ctrl and Alt are
    # held down explicitly around the key instead of through the shorthand.
    chord = "{VK_CONTROL down}{VK_MENU down}{F2}{VK_MENU up}{VK_CONTROL up}"
    support = _open_window(quill_app, chord, "Get Help from Support")
    support.type_keys("{ESC}")
    _assert_closes(support, "Get Help from Support")
