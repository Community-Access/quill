"""QUILL's Start page names New and Open, once the window is up (FUX-09)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")


def _host(**keys: str):
    later: list[int] = []
    said: list[str] = []

    def call_later(ms, fn, *args):
        later.append(ms)
        fn(*args)

    host = SimpleNamespace(
        commands=SimpleNamespace(keybinding_for=lambda cid: keys.get(cid)),
        _empty_workspace_active=True,
        _set_status=said.append,
        _wx=SimpleNamespace(CallLater=call_later),
    )
    host.said, host.later = said, later
    return host


def test_the_start_page_names_new_and_open_by_their_bound_keys() -> None:
    from quill.ui.main_frame_first_task import SAY_AFTER_MS, say_start_page_later

    host = _host(**{"file.new": "Ctrl+N", "file.open": "Ctrl+F12"})
    say_start_page_later(host)
    assert host.said == [
        "No document open. New (Ctrl+N) starts one, or Open (Ctrl+F12) opens a file."
    ]
    assert host.later == [SAY_AFTER_MS]  # after the focus speech, not during it


def test_said_once_however_often_the_window_is_shown() -> None:
    from quill.ui.main_frame_first_task import say_start_page_later

    host = _host(**{"file.new": "Ctrl+N", "file.open": "Ctrl+O"})
    say_start_page_later(host)
    say_start_page_later(host)
    assert len(host.said) == 1


def test_nothing_is_said_once_a_document_is_open_or_without_a_start_page() -> None:
    from quill.ui.main_frame_first_task import say_start_page_later

    host = _host()
    host._empty_workspace_active = False
    say_start_page_later(host)
    assert host.said == []


def test_the_start_page_is_written_quietly_while_the_window_is_being_built() -> None:
    from quill.ui.main_frame import MainFrame

    spoken: list[str] = []
    quiet: list[str] = []
    editor = SimpleNamespace(GetValue=lambda: "", SetEditable=lambda _on: None)
    host = SimpleNamespace(
        settings=SimpleNamespace(start_with_no_document_open=True),
        _document_tabs=[object()],
        document=SimpleNamespace(path=None, modified=False),
        editor=editor,
        _empty_workspace_active=False,
        _set_tab_page_text=lambda *_a: None,
        _set_status=spoken.append,
        _set_status_quiet=quiet.append,
    )
    MainFrame._apply_startup_document_preference(host)
    assert host._empty_workspace_active
    assert spoken == []
    assert quiet == ["No document open. New starts one, or Open opens a file."]
