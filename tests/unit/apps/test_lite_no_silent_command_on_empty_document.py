"""No QUILL Lite command is silent in an empty document.

Reported 2026-11-02 by the owner, a screen-reader user: in a blank document,
"issuing commands produces no feedback at all". The rule that came with it is
short -- **a command is never silent** -- and this is the sweep that holds every
command in the table to it.

Each handler in :data:`quill.core.lite.commands.COMMANDS` runs once, in a fresh
empty plain document (which is what File > New gives you), through the shipped
mixins over the recorded fakes of ``lite_window``. It passes if the user would
perceive *something*: a sentence or an earcon, a dialog or a window, a menu, a
focus move, a new or closed document, or a change to the text, the selection or
the clipboard. A handler that returns having done none of those is the bug.

What a stub cannot reach is listed in :data:`STUB_CANNOT_REACH` with its reason,
and the list may only shrink: a handler on it that starts passing fails the
test until it is taken off, so the list never hides a command that has since
gone quiet.

The sweep sees the *handler*. The keys that never reach a handler at all --
a dimmed menu row's accelerator, which Windows does not fire -- are the other
half of the same report, and ``test_dimmed_row_keys_reach_a_handler.py`` holds
those.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.lite.commands import COMMANDS

HANDLERS = sorted({row[3] for row in COMMANDS if row[3]})

#: Handlers this harness cannot drive to their outcome, with the reason. Each
#: one is a gap in the fakes, not a silent command -- the reason says which.
STUB_CANNOT_REACH: dict[str, str] = {
    "cmd_recent_documents": "defined on DocumentFrame itself, not on a mixin the stub composes",
    "cmd_reopen_last_session": "FakeApp has no choose_session_documents",
    "cmd_toggle_problems_pane": "the pane is a wx.Panel and needs a real wx parent "
    "(its behaviour is tested in test_lite_code_nav.py with a stand-in pane)",
    **{
        handler: "they show the Problems pane, a wx.Panel that needs a real wx parent "
        "(tested in test_lite_code_nav.py with a stand-in pane)"
        for handler in ("cmd_problems_this_file", "cmd_problems_all_files")
    },
    "cmd_snippet_gallery": "FakeApp.abbreviations is a dict, not the abbreviation store",
    "cmd_toggle_abbreviations": "FakeApp.abbreviations is a dict, not the abbreviation store",
    "cmd_clipboard_collector": "the collector's wx.Timer needs a real wx owner",
    "cmd_live_transcript": "the dictation session is not faked here",
    "cmd_page_setup": "wx.PageSetupDialogData will not take FakePageData",
    "cmd_print": "wx.PrintDialogData will not take FakePageData",
    "cmd_command_palette": "the recorder answers the palette's constructor with None",
    "cmd_go_to_anything": "the recorder answers the palette's constructor with None",
    "cmd_customize_features": "the recorder answers the features dialog's constructor with None",
    "cmd_keyboard_manager": "the recorder answers the keymap editor's constructor with None",
    "cmd_preferences": "the recorder answers edit_preferences with None",
    "cmd_find": "the recorder answers FindDialog's constructor with None",
    "cmd_find_next": "with no search yet it opens Find; the recorder answers None",
    "cmd_find_previous": "with no search yet it opens Find; the recorder answers None",
    "cmd_find_all": "with no search yet it opens Find; the recorder answers None",
    "cmd_count_occurrences": "with no search yet it opens Find; the recorder answers None",
    "cmd_replace": "the recorder answers ReplaceDialog's constructor with None",
}

#: The ``wx`` dialog classes commands construct themselves.
_WX_DIALOGS = (
    "FileDialog",
    "MessageDialog",
    "TextEntryDialog",
    "SingleChoiceDialog",
    "MultiChoiceDialog",
    "FontDialog",
    "ColourDialog",
    "DirDialog",
    "NumberEntryDialog",
    "PasswordEntryDialog",
    "RichMessageDialog",
    "GenericMessageDialog",
)


class _WindowOpened(Exception):
    """Raised where a real ``wx.Dialog`` or ``wx.Frame`` would have been built.

    A window opening is something the user perceives, and the stub has no real
    parent to give one, so the sweep stops the command there and counts it.
    """


def _snapshot(window: Any) -> dict[str, Any]:
    control = window.control
    app = window.app
    return {
        "text": control.GetValue(),
        "selection": control.GetSelection(),
        "caret": control.GetInsertionPoint(),
        "clipboard": control.clipboard,
        "announcements": len(window.announcements),
        "actions": len(window.actions),
        "cues": len(window.cues),
        "said": len(app.voice.said),
        "menus": len(window.popped_menus),
        "status_bar": window.status_bar_focused,
        "closed": window.closed,
        "failures": len(window.failures),
        "mode": window.editor.mode,
        "opened": len(app.opened),
        "cycled": len(app.cycled),
        "focused": len(app.focused),
        "exited": app.exited,
        "frames": len(app.frames),
    }


@pytest.fixture(autouse=True)
def _fresh_dictation(monkeypatch):
    """Each case starts with no dictation session, and leaves none behind.

    The controller is module state. Where a speech engine is installed,
    Speak a Command really starts one, and the next case (Switch Dictation
    Language) then talks to that session instead of saying the language.
    """
    from quill.ui import windows_dictation_commands as shared

    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    yield
    controller = shared._controller
    if controller is not None and (controller.active or controller.standing_by):
        try:
            controller.stop()
        except Exception:  # noqa: BLE001 - teardown only; the case already ran
            pass


@pytest.fixture(autouse=True)
def _no_real_update_check(monkeypatch) -> list[str]:
    """Check for Updates says "Checking for updates" and stops there.

    Unfaked, ``cmd_check_updates`` handed the real GitHub fetch to a real
    thread. This case passed on the announcement long before the answer came
    back; when the read timed out on CI, the error box it then posted through
    the real ``wx.CallAfter`` failed whichever unrelated test was running
    (2026-11-06). The background work is recorded, never run.
    """
    from quill.ui import update_download

    submitted: list[str] = []
    monkeypatch.setattr(
        update_download, "thread_submit", lambda name, *_a, **_k: submitted.append(name)
    )
    return submitted


@pytest.fixture
def opened_windows(monkeypatch, wx_session_app, wx_call_after) -> list[str]:
    """Every wx window a command tried to show, by class name."""
    wx_call_after()
    shown: list[str] = []

    def dialog_class(name: str) -> type:
        class Recorded:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                shown.append(name)

            def __enter__(self) -> Recorded:
                return self

            def __exit__(self, *_exc: Any) -> bool:
                return False

            def ShowModal(self) -> int:  # noqa: N802 - wx API shape
                return wx.ID_CANCEL

            def Destroy(self) -> None:  # noqa: N802 - wx API shape
                return None

            def __getattr__(self, _name: str) -> Any:
                return lambda *_a, **_k: None

        return Recorded

    for name in _WX_DIALOGS:
        monkeypatch.setattr(wx, name, dialog_class(name))
    monkeypatch.setattr(wx, "MessageBox", lambda *_a, **_k: shown.append("MessageBox") or wx.CANCEL)

    def refuse(kind: str) -> Any:
        def init(self: Any, *_args: Any, **_kwargs: Any) -> None:
            shown.append(f"{kind}:{type(self).__name__}")
            raise _WindowOpened(type(self).__name__)

        return init

    monkeypatch.setattr(wx.Dialog, "__init__", refuse("Dialog"))
    monkeypatch.setattr(wx.Frame, "__init__", refuse("Frame"))
    return shown


@pytest.mark.parametrize("handler", HANDLERS)
def test_no_command_is_silent_in_an_empty_document(
    handler, lite_window, lite_dialogs, opened_windows
) -> None:
    window = lite_window("")
    command = getattr(window, handler, None)
    if handler in STUB_CANNOT_REACH:
        pytest.skip(STUB_CANNOT_REACH[handler])
    assert command is not None, f"{handler} is in the command table but not on the window"
    before = _snapshot(window)
    try:
        command()
    except _WindowOpened:
        pass
    except Exception:
        # The recorded dialogs answer every getter with None, which some
        # callers then trip over -- after the dialog was put up, which is the
        # outcome this sweep is asking about. Anything else is a real failure.
        if not (opened_windows or lite_dialogs.names()):
            raise
    after = _snapshot(window)
    changed = [name for name in before if before[name] != after[name]]
    assert changed or lite_dialogs.names() or opened_windows, (
        f"{handler} did nothing a listener could perceive in an empty document. "
        "Say why in one sentence through _announce (it brailles too)."
    )


@pytest.mark.parametrize("handler", sorted(STUB_CANNOT_REACH))
def test_the_unreachable_list_only_shrinks(
    handler, lite_window, lite_dialogs, opened_windows
) -> None:
    """A listed handler the stub can now drive must come off the list."""
    window = lite_window("")
    command = getattr(window, handler, None)
    if command is None:
        return
    before = _snapshot(window)
    try:
        command()
    except _WindowOpened:
        pass
    except Exception:  # noqa: BLE001 - still out of the stub's reach
        return
    after = _snapshot(window)
    reached = any(before[name] != after[name] for name in before)
    assert not (reached or lite_dialogs.names() or opened_windows), (
        f"{handler} now runs to an outcome under the stub: take it off STUB_CANNOT_REACH."
    )


def test_the_sweeps_check_for_updates_never_starts_a_real_fetch(
    lite_window, lite_dialogs, opened_windows, _no_real_update_check
) -> None:
    """The sweep's Check for Updates is handed to the recorder, not a thread."""
    from tests import real_output_guard

    lite_window("").cmd_check_updates()
    assert _no_real_update_check == ["app-update-check"]
    assert real_output_guard.take_violations() == []
