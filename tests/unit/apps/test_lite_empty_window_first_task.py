"""An empty QUILL Lite window says how to begin (FUX-09).

With every document closed, or at launch when nothing opened, the window has
no control at all: nothing has focus and a screen reader reads only the
title. One sentence now names New and Open by their live keys, said when the
window becomes empty and never while QUILL Lite is closing.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")


def _shell(*, frames=(), deleting=False, shown=True, keymap=None):
    said: list[str] = []

    def speak(message, *, interrupt=True):
        said.append(message)
        assert interrupt is False  # queued behind recovery or update sentences

    app = SimpleNamespace(
        frames=list(frames), keymap=keymap or {}, voice=SimpleNamespace(speak=speak)
    )
    shell = SimpleNamespace(
        app=app, IsBeingDeleted=lambda: deleting, IsShown=lambda: shown, rebuilt=[]
    )
    # The shell's own _announce: the app's voice, which brailles what it speaks.
    shell._announce = lambda message, *, interrupt=True: speak(message, interrupt=interrupt)
    shell.said = said
    return shell


def _say(shell) -> None:
    from quill.apps.lite_shell_menu import ShellMenuMixin

    ShellMenuMixin.say_if_empty(shell)


def test_an_empty_window_names_new_and_open_with_their_keys() -> None:
    shell = _shell()
    _say(shell)
    assert shell.said == [
        "No documents open. New (Ctrl+N) starts one, or Open (Ctrl+O) opens a file."
    ]


def test_a_rebound_key_is_the_key_said() -> None:
    shell = _shell(keymap={"cmd_open": "Ctrl+Shift+F12"})
    _say(shell)
    assert "Open (Ctrl+Shift+F12) opens a file" in shell.said[0]


def test_silent_with_a_document_open_while_closing_or_hidden() -> None:
    for shell in (_shell(frames=[object()]), _shell(deleting=True), _shell(shown=False)):
        _say(shell)
        assert shell.said == []


def test_the_last_close_rebuilds_the_bar_then_says_it_after_the_reader(monkeypatch) -> None:
    from quill.apps.lite_shell_menu import ShellMenuMixin
    from quill.ui.main_frame_first_task import SAY_AFTER_MS

    order: list[object] = []
    monkeypatch.setattr(wx, "CallLater", lambda ms, fn: (order.append(ms), fn()))
    shell = SimpleNamespace(
        rebuild_empty_menu=lambda: order.append("bar"), say_if_empty=lambda: order.append("say")
    )
    ShellMenuMixin.now_empty(shell)
    assert order == ["bar", SAY_AFTER_MS, "say"]


def test_forget_frame_of_the_last_document_goes_through_now_empty(wx_call_after) -> None:
    from quill.apps.lite import QuillLiteApp

    calls = wx_call_after(lambda fn, *a: None)
    frame = object()
    app = SimpleNamespace(
        frames=[frame],
        active_frame=frame,
        save_settings=lambda: None,
        refresh_all_menus=lambda: None,
        shell=SimpleNamespace(now_empty="now_empty"),
    )
    QuillLiteApp.forget_frame(app, frame)
    assert [call[0] for call in calls.calls] == ["now_empty"]
