"""The YouTube Comments window: loading, searching, sorting, paging, keys."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.radio import youtube_comments as yc  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Tasks:
    """Runs work at once, on this thread -- the way the window's tests can see it."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def submit(self, name, work, *, on_success=None, on_failure=None):
        self.names.append(name)
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            if on_failure:
                on_failure(name, error)
            return
        if on_success:
            on_success(name, result)


def _info(count: int, *, prefix: str = "c") -> dict:
    return {
        "comments": [
            {
                "id": f"{prefix}{i}",
                "parent": "root",
                "text": f"Comment number {i} about the bridge" if i % 2 else f"Number {i}",
                "author": f"@Person{i}",
                "like_count": i,
                "_time_text": "1 day ago",
            }
            for i in range(count)
        ]
    }


class _YouTube:
    def __init__(self) -> None:
        self.asked: list[dict] = []

    def __call__(self, target, options):
        args = options["extractor_args"]["youtube"]
        self.asked.append(args)
        return _info(int(args["max_comments"][0]))


def _window(fetch=None, **kwargs):
    from quill.ui.radio.youtube_comments_window import YouTubeCommentsWindow

    said: list[str] = []
    failures: list[str] = []
    window = YouTubeCommentsWindow(
        None,
        video_title="Bristol walking tour",
        page_url="https://www.youtube.com/watch?v=abcdefghijk",
        task_manager=_Tasks(),
        announce=said.append,
        on_failure=failures.append,
        fetch=fetch or _YouTube(),
        copy_text=kwargs.get("copy_text"),
    )
    return window, said, failures


def test_the_first_page_arrives_and_the_count_is_said_once(wx_app) -> None:
    youtube = _YouTube()
    window, said, _f = _window(youtube)
    try:
        window.start()
        assert window._list.GetCount() == yc.PAGE_SIZE
        assert said[-1] == f"{yc.PAGE_SIZE} comments."
        assert youtube.asked[0] == {"max_comments": ["100"], "comment_sort": ["top"]}
        assert "Person0" in window._full.GetValue()
    finally:
        window.frame.Destroy()


def test_searching_filters_and_says_the_count_once_after_the_pause(wx_app) -> None:
    window, said, _f = _window()
    try:
        window.start()
        before = len(said)
        window._search.ChangeValue("bridge")
        window._on_search_text()
        assert len(said) == before  # nothing while typing
        window.apply_filter(speak=True)  # what the pause timer runs
        assert window._list.GetCount() == 50
        assert said[-1] == "50 of 100 comments match."
        assert len(said) == before + 1
        window._search.ChangeValue("zebra")
        window.apply_filter(speak=True)
        assert said[-1] == "No comments match zebra."
        assert window._full.GetValue() == ""
    finally:
        window.frame.Destroy()


def test_newest_first_asks_again_in_that_order(wx_app) -> None:
    youtube = _YouTube()
    window, said, _f = _window(youtube)
    try:
        window.start()
        window._sort_choice.SetSelection(1)
        window._on_sort()
        assert youtube.asked[-1]["comment_sort"] == ["new"]
        assert said[-1] == f"{yc.PAGE_SIZE} comments."
    finally:
        window.frame.Destroy()


def test_load_more_asks_for_the_next_hundred_and_keeps_the_place(wx_app) -> None:
    youtube = _YouTube()
    window, said, _f = _window(youtube)
    try:
        window.start()
        window._list.SetSelection(7)
        window._show_selected()
        window.load_more()
        assert youtube.asked[-1]["max_comments"] == ["200"]
        assert window._list.GetCount() == 200
        assert window._list.GetSelection() == 7
        assert window._full.GetValue().startswith("Person7")
        assert said[-1] == "100 more comments, 200 in all."
    finally:
        window.frame.Destroy()


def test_load_more_stops_at_the_cap_and_says_so(wx_app) -> None:
    window, said, _f = _window()
    try:
        window.start()
        window._limit = yc.MAX_COMMENTS
        window.load_more()
        assert "the most Quill Radio reads" in said[-1]
    finally:
        window.frame.Destroy()


def test_a_failure_is_one_sentence_and_goes_to_recent_problems(wx_app) -> None:
    def broken(target, options):
        raise RuntimeError("Comments are turned off for this video")

    window, said, failures = _window(broken)
    try:
        window.start()
        assert said[-1] == "Comments could not be fetched. Comments are turned off for that video."
        assert failures == ["Comments are turned off for that video."]
    finally:
        window.frame.Destroy()


def test_copy_comment_copies_the_whole_selected_comment(wx_app) -> None:
    copied: list[str] = []
    window, said, _f = _window(copy_text=lambda text: copied.append(text) or True)
    try:
        window.start()
        window._list.SetSelection(1)
        window._show_selected()
        window.copy_selected()
        assert copied[0].startswith("Person1 (1 like, 1 day ago)")
        assert said[-1] == "Comment copied."
    finally:
        window.frame.Destroy()


def test_replies_read_as_replies_in_the_list(wx_app) -> None:
    def fetch(target, options):
        return {
            "comments": [
                {"id": "a", "parent": "root", "text": "Lovely", "author": "@Ann"},
                {"id": "a.1", "parent": "a", "text": "Agreed", "author": "@Ben"},
            ]
        }

    window, _said, _f = _window(fetch)
    try:
        window.start()
        assert window._list.GetString(1) == "Ben, reply to Ann: Agreed"
    finally:
        window.frame.Destroy()


def test_escape_closes_and_focus_goes_back(wx_app, monkeypatch) -> None:
    from quill.ui.radio import youtube_comments_window as module

    refocused: list = []
    monkeypatch.setattr(module, "_refocus", refocused.append)
    window, _said, _f = _window()
    window._return_focus = "opener"
    window._wx = type("W", (), {"CallAfter": staticmethod(lambda fn, arg: fn(arg))})
    window._wx.WXK_ESCAPE = wx.WXK_ESCAPE
    window._wx.WXK_F4 = wx.WXK_F4
    closed: list = []
    window.frame.Close = lambda *a: closed.append(True)  # type: ignore[method-assign]

    class _Key:
        def GetKeyCode(self):
            return wx.WXK_ESCAPE

        def ControlDown(self):
            return False

        def Skip(self):
            raise AssertionError("Escape must not be passed on")

    window._on_char_hook(_Key())
    assert closed == [True]

    class _Close:
        def Skip(self):
            pass

    window._on_close(_Close())
    assert refocused == ["opener"]
    window.frame.Destroy()


def test_every_control_has_f1_help_and_unique_access_keys(wx_app) -> None:
    import re

    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()  # SetHelpText stores nothing without one
    window, _said, _f = _window()
    try:
        controls = [
            window._search,
            window._sort_choice,
            window._list,
            window._full,
            window._more,
            window._copy,
            window._close,
        ]
        assert all(control.GetHelpText().strip() for control in controls)
        labels = [
            child.GetLabel()
            for child in window._panel.GetChildren()
            if isinstance(child, (wx.StaticText, wx.Button))
        ]
        keys = [m.group(1).lower() for label in labels if (m := re.search(r"&(.)", label))]
        assert len(keys) == len(set(keys)), keys
        assert "&" not in window._close.GetLabel()  # Close carries none (GATE-14)
    finally:
        window.frame.Destroy()


def test_the_window_title_has_an_f1_purpose() -> None:
    from quill.core.radio import surface_help
    from quill.ui.radio.youtube_comments_window import TITLE

    assert surface_help.purpose_for_title(TITLE)


def test_load_more_appends_and_never_rebuilds_the_list(wx_app, monkeypatch) -> None:
    """Rebuilding would make a screen reader read the list again and could move
    the selection; Load More only adds rows at the end."""
    window, _said, _f = _window()
    try:
        window.start()
        window._list.SetSelection(42)
        window._show_selected()
        rebuilt: list = []
        monkeypatch.setattr(window._list, "Set", lambda items: rebuilt.append(items))
        moved: list = []
        monkeypatch.setattr(window._list, "SetSelection", lambda index: moved.append(index))
        window.load_more()
        assert rebuilt == [] and moved == []
        assert window._list.GetCount() == 200
        assert window._list.GetSelection() == 42
    finally:
        window.frame.Destroy()
