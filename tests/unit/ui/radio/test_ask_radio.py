"""Ask QUILL Radio: the wiring, what it knows, and the conversation window."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.ui.radio import ask_radio_wiring as wiring


class _Commands:
    def __init__(self) -> None:
        self.registered: dict[str, tuple] = {}

    def try_register(self, command_id, title, handler, binding=None, *, feature_id=""):
        self.registered[command_id] = (title, handler, binding, feature_id)


class _Host:
    def __init__(self, *, station: str = "", playing: str = "", safe: bool = False) -> None:
        self.commands = _Commands()
        self.announcements: list[str] = []
        self._safe_mode = safe
        self._windows = None
        self._wx = SimpleNamespace(CallAfter=lambda fn, *a: fn(*a))
        self.frame = None
        self._radio_controller = SimpleNamespace(
            state=SimpleNamespace(station=SimpleNamespace(name=station) if station else None)
        )
        self._playing = playing

    def _binding_for(self, command_id: str) -> str:
        return {"radio.ask_quill_radio": "Ctrl+Shift+8", "radio.chatgpt_account": "Alt+F5"}[
            command_id
        ]

    def _announce(self, message: str, **_kwargs) -> None:
        self.announcements.append(message)

    def _radio_now_playing_text(self) -> str:
        return self._playing

    def _menu_label(self, title: str, command_id: str) -> str:
        return f"{title}\t{self._binding_for(command_id)}"

    def _keep_menu_ids(self, *ids) -> None:
        self.kept = ids


def test_register_puts_both_commands_in_the_palette_with_their_keys() -> None:
    host = _Host()
    wiring.register(host)
    assert host.commands.registered["radio.ask_quill_radio"][2] == "Ctrl+Shift+8"
    assert host.commands.registered["radio.chatgpt_account"][2] == "Alt+F5"
    assert all(v[3] == "core.radio" for v in host.commands.registered.values())


def test_the_keys_are_in_the_radio_keymap() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS

    assert APP_KEYMAPS["radio"]["radio.ask_quill_radio"] == "Ctrl+Shift+8"
    assert APP_KEYMAPS["radio"]["radio.chatgpt_account"] == "Alt+F5"


def test_what_is_on_reads_the_station_and_the_title_and_never_raises() -> None:
    assert wiring.what_is_on(_Host(station="KEXP", playing="A song")) == ("KEXP", "A song")
    assert wiring.what_is_on(_Host()) == ("", "")
    assert wiring.what_is_on(SimpleNamespace()) == ("", "")


def test_the_account_signs_in_as_quill_radio_and_is_kept(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host()
    account = wiring.account_for(host)
    assert account.agent_name == "QUILL Radio"
    assert account.slug == "quill-radio"
    assert wiring.account_for(host) is account


def test_safe_mode_refuses_both_doors(monkeypatch) -> None:
    host = _Host(safe=True)
    assert wiring.open_ask(host) is None
    assert wiring.open_account(host) is None
    assert host.announcements and all("Safe Mode" in s for s in host.announcements)


def test_without_a_sign_in_ask_opens_the_account_window_and_says_why(monkeypatch) -> None:
    host = _Host()
    host._chatgpt_account = SimpleNamespace(signed_in=False)
    opened = []
    monkeypatch.setattr(wiring, "open_account", lambda h: opened.append(h) or "account")
    assert wiring.open_ask(host) == "account"
    assert opened == [host]
    assert any("Continue with ChatGPT" in s for s in host.announcements)


def test_an_open_window_is_raised_rather_than_built_again(monkeypatch) -> None:
    host = _Host()

    class Windows:
        def activate_title(self, title):
            return "already" if title == wiring.TITLE else None

    host._windows = Windows()
    assert wiring.open_ask(host) == "already"


def test_the_menu_rows_carry_their_keys(monkeypatch) -> None:
    host = _Host()
    host.frame = SimpleNamespace(Bind=lambda *a, **k: None)
    appended = []
    menu = SimpleNamespace(Append=lambda item_id, label: appended.append(label))
    wx = SimpleNamespace(NewIdRef=lambda: object(), EVT_MENU=object())
    ids = wiring.append_menu_items(host, menu, wx)
    assert len(ids) == 2
    assert appended == [
        "Ask QUILL &Radio...\tCtrl+Shift+8",
        "Use My Chat&GPT Subscription...\tAlt+F5",
    ]
    assert host.kept == ids


# --------------------------------------------------------------------------- #
# The window itself
# --------------------------------------------------------------------------- #

wx_lib = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx_lib.App()
    yield app
    app.Destroy()


class _Account:
    signed_in = True
    model = "gpt-6"
    web_search = False


def _frame(*, station="KEXP", playing="A song", submit=None):
    from quill.ui.radio.ask_radio_window import AskRadioFrame

    said: list[str] = []
    calls: list[dict] = []

    def run(name, work, *, on_done, on_error):
        calls.append({"name": name, "work": work})
        on_done("Because it is a classic.")

    frame = AskRadioFrame(
        None,
        account=_Account(),
        announce=said.append,
        what_is_on=lambda: (station, playing),
        submit=submit or run,
        open_account=lambda: said.append("account window"),
    )
    return frame, said, calls


def test_the_window_says_what_it_knows(wx_app) -> None:
    frame, _said, _calls = _frame()
    try:
        about = frame._about.GetValue()
        assert "KEXP" in about and "A song" in about
        assert "gpt-6" in about
        assert "Web search is off" in about
    finally:
        frame.Destroy()


def test_a_message_goes_with_what_is_playing_and_the_reply_is_spoken(wx_app, monkeypatch) -> None:
    frame, said, calls = _frame()
    sent = {}
    monkeypatch.setattr(
        "quill.core.ai.chatgpt_ai_help.converse_with_chatgpt",
        lambda account, prompt, chunks, history, *, instructions: (
            sent.update(prompt=prompt, history=history, instructions=instructions)
            or "Because it is a classic."
        ),
    )
    try:
        frame._message.SetValue("Why is this famous?")
        frame._send()
        calls[0]["work"]()
        assert sent["prompt"] == "Why is this famous?"
        assert "KEXP" in sent["instructions"] and "A song" in sent["instructions"]
        assert "You: Why is this famous?" in frame._transcript.GetValue()
        assert said[-1] == "Because it is a classic."
        assert frame._message.GetValue() == ""
    finally:
        frame.Destroy()


def test_ask_about_whats_playing_needs_no_typing_and_cycles(wx_app) -> None:
    frame, said, calls = _frame()
    try:
        frame._ask_about_playing()
        first = frame._conversation.turns[0].text
        frame._ask_about_playing()
        second = frame._conversation.turns[2].text
        assert first != second
        assert "song" in first.lower()
    finally:
        frame.Destroy()


def test_with_nothing_playing_the_button_says_so(wx_app) -> None:
    frame, said, calls = _frame(station="", playing="")
    try:
        frame._ask_about_playing()
        assert calls == []
        assert any("Nothing is playing" in s for s in said)
    finally:
        frame.Destroy()


def test_an_empty_message_sends_nothing(wx_app) -> None:
    frame, said, calls = _frame()
    try:
        frame._send()
        assert calls == []
        assert "Type a message first." in said
    finally:
        frame.Destroy()


def test_every_button_and_field_has_help_for_f1(wx_app) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx_lib)  # SetHelpText stores nothing without a provider
    frame, _said, _calls = _frame()
    try:
        pending = list(frame.GetChildren())
        seen = 0
        while pending:
            window = pending.pop(0)
            pending.extend(window.GetChildren())
            if isinstance(window, (wx_lib.Button, wx_lib.TextCtrl)):
                seen += 1
                assert window.GetHelpText(), window.GetLabel() or window.GetName()
        assert seen >= 8
    finally:
        frame.Destroy()


# --------------------------------------------------------------------------- #
# Quick questions
# --------------------------------------------------------------------------- #


def test_extra_for_reads_favorites_and_the_song_log_and_never_raises(monkeypatch) -> None:
    from quill.core.radio.assistant_prompt import (
        NEEDS_FAVORITES,
        NEEDS_LISTENING,
        NEEDS_PLAYING,
        NEEDS_RECENT_SONGS,
    )
    from quill.core.radio.song_history import SongHistory, SongPlay, StationSongs

    host = _Host(station="KEXP", playing="A song")
    host._radio_controller.state.station.station_uuid = "uuid-1"
    host._radio_favorites = SimpleNamespace(
        favorites=[
            SimpleNamespace(station=SimpleNamespace(name="ACB Media 1"), folder="ACB"),
            SimpleNamespace(station=SimpleNamespace(name="KEXP"), folder=""),
        ]
    )
    log = SongHistory(
        stations=[
            StationSongs("uuid-1", "KEXP", [SongPlay("Blue", "Joni"), SongPlay("Red", "Band")]),
            StationSongs("uuid-2", "WNYC", [SongPlay("Talk", "")]),
        ]
    )
    host._radio_song_log = log
    text, count = wiring.extra_for(host, NEEDS_FAVORITES)
    assert count == 2 and "ACB Media 1 (in ACB)" in text and "KEXP" in text
    text, count = wiring.extra_for(host, NEEDS_RECENT_SONGS)
    assert count == 2 and text.startswith("Songs heard on this station")
    assert "Blue by Joni" in text
    text, count = wiring.extra_for(host, NEEDS_LISTENING)
    assert count == 2 and "WNYC: Talk" in text
    assert wiring.extra_for(host, NEEDS_PLAYING) == ("", 0)
    assert wiring.extra_for(SimpleNamespace(), NEEDS_FAVORITES) == ("", 0)


def test_a_quick_question_is_put_in_the_box_and_says_what_it_sends(wx_app) -> None:
    from quill.core.radio.assistant_prompt import NEEDS_FAVORITES, QUICK_QUESTIONS

    frame, said, calls = _frame()
    favorites = ("Favorite stations: X; Y", 2)
    frame._extra_for = lambda needs: favorites if needs == NEEDS_FAVORITES else ("", 0)
    try:
        row = next(i for i, q in enumerate(QUICK_QUESTIONS) if q.needs == NEEDS_FAVORITES)
        frame._quick.SetSelection(row + 1)
        frame._use_quick()
        assert frame._message.GetValue() == QUICK_QUESTIONS[row].question
        assert "2 favorite" in frame._status.GetValue()
        assert any("2 favorite" in s and "Press Enter" in s for s in said)
        assert calls == [], "chosen is not sent"
        # The list keeps its place: arrowing back to it lands where you were.
        assert frame._quick.GetSelection() == row + 1
    finally:
        frame.Destroy()


def test_arrowing_the_quick_questions_never_moves_focus_or_fills_the_box(wx_app) -> None:
    """A wx.Choice fires its selection event on every arrow press; the window
    must not act on it (reported 2026-09-29: focus jumped to the message box)."""
    frame, said, calls = _frame()
    try:
        frame._quick.SetSelection(2)
        event = wx_lib.CommandEvent(wx_lib.wxEVT_CHOICE, frame._quick.GetId())
        event.SetInt(2)
        frame._quick.GetEventHandler().ProcessEvent(event)
        assert frame._message.GetValue() == ""
        assert said == []
        assert frame._quick.GetSelection() == 2
    finally:
        frame.Destroy()


def test_enter_on_the_quick_questions_uses_the_highlighted_one(wx_app) -> None:
    frame, said, calls = _frame()
    try:
        from quill.core.radio.assistant_prompt import QUICK_QUESTIONS

        frame._quick.SetSelection(1)
        event = wx_lib.KeyEvent(wx_lib.wxEVT_CHAR_HOOK)
        event.SetKeyCode(wx_lib.WXK_RETURN)
        frame._on_quick_key(event)
        assert frame._message.GetValue() == QUICK_QUESTIONS[0].question
        assert calls == []
    finally:
        frame.Destroy()


def test_the_chosen_extra_goes_once_and_only_when_chosen(wx_app, monkeypatch) -> None:
    from quill.core.radio.assistant_prompt import NEEDS_FAVORITES, QUICK_QUESTIONS

    frame, said, calls = _frame()
    favorites = ("Favorite stations: X", 1)
    frame._extra_for = lambda needs: favorites if needs == NEEDS_FAVORITES else ("", 0)
    seen = []
    monkeypatch.setattr(
        "quill.core.ai.chatgpt_ai_help.converse_with_chatgpt",
        lambda account, prompt, chunks, history, *, instructions: seen.append(instructions) or "ok",
    )
    try:
        row = next(i for i, q in enumerate(QUICK_QUESTIONS) if q.needs == NEEDS_FAVORITES)
        frame._quick.SetSelection(row + 1)
        frame._use_quick()
        frame._send()
        calls[0]["work"]()
        assert "Favorite stations: X" in seen[0]
        frame._message.SetValue("And now a plain question")
        frame._send()
        calls[1]["work"]()
        assert "Favorite stations" not in seen[1]
    finally:
        frame.Destroy()
