"""QUILL Lite: Find in Open Documents, across every window (QUILLVille, Oct 2026).

The window is QUILL's (ui/open_documents_find); these hold QUILL Lite's half:
the command opens it over this app's windows, F3 carries on across windows
afterwards, and an ordinary Find hands F3 back.
"""

from __future__ import annotations

from quill.core.find_model import FindQuery


def _two_windows(lite_window):  # type: ignore[no-untyped-def]
    first = lite_window("no match here\n", cursor=0)
    second = lite_window("the cat sat\n", cursor=0)
    # One app, two windows: the second joins the first's.
    second.app.frames.remove(second)
    second.app = first.app
    first.app.frames.append(second)
    first.app.active_frame = first
    focused: list[object] = []

    def focus_frame(frame: object) -> None:
        focused.append(frame)
        first.app.active_frame = frame

    first.app.focus_frame = focus_frame
    for win, name in ((first, "Notes.txt"), (second, "Chapter 3.txt")):
        win.document_name = lambda name=name: name
    return first, second, focused


def test_the_command_opens_the_shared_window_over_this_apps_windows(
    lite_window, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from quill.apps.lite_open_documents import LiteOpenDocuments
    from quill.ui import open_documents_find

    opened: list[object] = []
    monkeypatch.setattr(open_documents_find, "open_find_in_open_documents", opened.append)
    first, second, _focused = _two_windows(lite_window)
    first.cmd_find_open_docs()
    assert len(opened) == 1 and isinstance(opened[0], LiteOpenDocuments)
    assert [doc.name for doc in opened[0].documents()] == ["Notes.txt", "Chapter 3.txt"]


def test_f3_carries_on_into_the_next_window(lite_window) -> None:  # type: ignore[no-untyped-def]
    from quill.apps.lite_open_documents import state_for

    first, second, focused = _two_windows(lite_window)
    state = state_for(first.app)
    state.query, state.active = FindQuery("cat"), True
    first.cmd_find_next()
    assert focused == [second]
    assert second.control.GetSelection() == (4, 7)
    assert any("Chapter 3.txt, line 1: the cat sat" in said for said in first.announcements)


def test_an_ordinary_find_hands_f3_back_to_this_window(lite_window, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from quill.apps import lite_window_find
    from quill.apps.lite_open_documents import state_for

    first, _second, _focused = _two_windows(lite_window)
    state = state_for(first.app)
    state.query, state.active = FindQuery("cat"), True
    monkeypatch.setattr(lite_window_find, "FindDialog", _NoDialog)
    first.cmd_find()
    assert state.active is False


def test_replace_ends_it_too(lite_window, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from quill.apps import lite_window_find
    from quill.apps.lite_open_documents import state_for

    first, _second, _focused = _two_windows(lite_window)
    state = state_for(first.app)
    state.active = True
    monkeypatch.setattr(lite_window_find, "ReplaceDialog", _NoDialog)
    first.cmd_replace()
    assert state.active is False


class _NoDialog:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def Bind(self, *_args, **_kwargs) -> None:
        pass

    def Show(self) -> None:
        pass

    def ShowModal(self) -> int:
        return 0

    def Destroy(self) -> None:
        pass

    def __getattr__(self, _name):  # type: ignore[no-untyped-def]
        return lambda *a, **k: None
