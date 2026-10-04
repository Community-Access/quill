"""The Live Chat window, screen-reader-first: appends never move you, follow is opt-in,
pause counts, speech toggles on one key, and a failed send keeps your words."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.radio import youtube_live_chat as lc  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Reader:
    """Stands in for ChatReader: nothing threaded, nothing networked."""

    def __init__(self) -> None:
        self.waiting: list[lc.ChatMessage] = []
        self.stopped = False

    def start(self) -> None:
        pass

    def stop(self, timeout: float = 0) -> None:
        self.stopped = True

    def drain(self, limit: int = 500) -> list[lc.ChatMessage]:
        out, self.waiting = self.waiting, []
        return out


def _m(author: str, text: str = "hi") -> lc.ChatMessage:
    return lc.ChatMessage(message_id=f"{author}{text}", author=author, text=text)


@pytest.fixture
def window(wx_app):
    from quill.ui.radio.youtube_live_chat_window import YouTubeLiveChatWindow

    said: list[str] = []
    sent: list[str] = []
    outcome = {"ok": True}

    def send(text, done, failed):
        sent.append(text)
        if outcome["ok"]:
            done()
        else:
            said.append("YouTube refused.")
            failed("YouTube refused.")

    frame = wx.Frame(None)
    win = YouTubeLiveChatWindow(
        frame,
        video_title="A stream",
        page_url="https://www.youtube.com/watch?v=abcdefghijk",
        announce=said.append,
        reader=_Reader(),
        can_send=True,
        send=send,
    )
    win.said, win.sent, win.outcome = said, sent, outcome
    yield win
    win._timer.Stop()
    win.frame.Destroy()
    frame.Destroy()


def _rows(win) -> list[str]:
    return [win._list.GetItemText(i) for i in range(win._list.GetItemCount())]


def test_new_messages_append_without_moving_the_selection(window) -> None:
    window.receive([_m("A"), _m("B"), _m("C")])
    window._list.Select(1)
    window._list.Focus(1)
    window.receive([_m("D"), _m("E")])
    assert _rows(window)[-2:] == ["D: hi", "E: hi"]
    assert window._list.GetFirstSelected() == 1
    assert window._list.GetFocusedItem() == 1


def test_last_row_does_not_follow_unless_asked(window, monkeypatch) -> None:
    monkeypatch.setattr(window, "_list_has_focus", lambda: True)
    window.receive([_m("A"), _m("B")])
    window._list.Select(1)
    window.receive([_m("C")])
    assert window._list.GetFirstSelected() == 1  # Follow is off by default


def test_follow_moves_only_from_the_last_row_with_focus(window, monkeypatch) -> None:
    window._follow.SetValue(True)
    focus = {"on": True}
    monkeypatch.setattr(window, "_list_has_focus", lambda: focus["on"])
    window.receive([_m("A"), _m("B")])
    window._list.Select(1)
    window.receive([_m("C")])
    assert window._list.GetFirstSelected() == 2
    window._list.Select(0)
    window.receive([_m("D")])
    assert window._list.GetFirstSelected() == 0, "not on the last row: nothing moves"
    window._list.Select(3)
    focus["on"] = False
    window.receive([_m("E")])
    assert window._list.GetFirstSelected() == 3, "focus elsewhere: nothing moves"


def test_pause_counts_and_resume_says_how_many(window) -> None:
    window.receive([_m("A")])
    window.set_paused(True)
    window.receive([_m("B"), _m("C")])
    assert _rows(window) == ["A: hi"]
    assert "2 waiting" in window._status.GetLabel()
    window.set_paused(False)
    assert _rows(window) == ["A: hi", "B: hi", "C: hi"]
    assert window.said[-1] == "Resumed. 2 new messages while paused."


def test_pause_from_the_check_box_does_not_repeat_the_reader(window) -> None:
    window.set_paused(True, from_box=True)
    assert window.said == []  # the reader already said "checked"


def test_one_key_toggles_speaking(window) -> None:
    window.toggle_speech()
    assert window._announcer.mode == lc.SPEAK_ALL
    assert window.said[-1] == "Speaking new messages: every message."
    window.toggle_speech()
    assert window._announcer.mode == lc.SPEAK_OFF


def test_newest_is_read_without_moving_and_jump_goes_there(window) -> None:
    window.receive([_m("A"), _m("B", "latest")])
    window._list.Select(0)
    window.read_newest()
    assert window.said[-1] == "B: latest"
    assert window._list.GetFirstSelected() == 0
    window.jump_to_newest()
    assert window._list.GetFirstSelected() == 1


def test_same_author_jump(window) -> None:
    window.receive([_m("A", "1"), _m("B"), _m("A", "2")])
    window._list.Select(0)
    window.jump(1)
    assert window._list.GetFirstSelected() == 2
    window.jump(1)
    assert window.said[-1] == "No later message from A."


def test_send_clears_on_success_and_keeps_text_on_failure(window) -> None:
    window._send_box.SetValue("hello chat")
    window.send_typed()
    assert window.sent == ["hello chat"] and window._send_box.GetValue() == ""
    assert window.said[-1] == "Message sent."
    window.outcome["ok"] = False
    window._send_box.SetValue("try again")
    window.send_typed()
    assert window._send_box.GetValue() == "try again"
    assert window.said[-1] == "YouTube refused."


def test_failure_is_said_once(window) -> None:
    window._failed("Chat is turned off for this video.")
    window._failed("Chat is turned off for this video.")
    assert window.said.count("Live chat stopped. Chat is turned off for this video.") == 1


def test_filter_shows_matching_rows_and_new_ones_that_match(window) -> None:
    window.receive([_m("A", "the bridge"), _m("B", "nothing")])
    window._filter.ChangeValue("bridge")
    window.apply_filter()
    assert _rows(window) == ["A: the bridge"]
    window.receive([_m("C", "another bridge"), _m("D", "no")])
    assert _rows(window) == ["A: the bridge", "C: another bridge"]


def test_closing_stops_the_reader(window) -> None:
    window.frame.Close()
    assert window._reader.stopped
