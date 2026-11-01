"""Quill Radio's AI, in the real window (codex.md Phase 3).

Ask QUILL Radio folded into Ask, the family's one conversation window, with
Radio's facts; Choose Your AI, Which AI, Usage and the AI status cell from the
shared code; and Describe the Video through picture_prep. The AI itself is a
stand-in on the real service, so nothing leaves the machine.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

#: Serialized onto one worker: builds a real Quill Radio window, which registers
#: system-wide hotkeys.
pytestmark = pytest.mark.machine_global


class _Account:
    """A ChatGPT sign-in that is (or is not) there, and never touches a store."""

    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-radio"
        self.web_search = False
        self.ended_by_openai = False


def _png(width: int = 3000, height: int = 1500) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def radio(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    service = frame._ai_service()
    service._chatgpt = _Account(signed_in=True)
    # Building the menus read the real (empty) sign-in and migrated to the free
    # AI; start this test from a profile that has not been migrated yet.
    frame._radio_history.ai_connection = ""
    frame._ai_host()._ai_status_text = None
    frame.sent: list[tuple] = []

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append((message, list(excerpts), requires))
        on_done(f"Answer {len(frame.sent)}", None, 0)

    service.converse = converse
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame._radio_now_playing_text = lambda: frame.playing
    frame.playing = "Blue in Green by Miles Davis"
    frame._radio_controller.state.station = SimpleNamespace(name="KJAZZ", station_uuid="k1")
    try:
        yield frame
    finally:
        for window in list(getattr(frame, "_ai_windows", {}).values()):
            if window:
                window.Destroy()
        frame._radio_shutdown()
        set_transition_announcement_policy(None)


def _labels(menu) -> list[str]:
    return [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]


def _community(frame):
    bar = frame.frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu("Community"))


def test_community_opens_on_ask_then_the_ai_submenu_on_radios_own_keys(radio) -> None:
    community = _community(radio)
    first = community.GetMenuItems()[0]
    assert first.GetItemLabel() == "&Ask...\tCtrl+Shift+8"
    sub = next(i.GetSubMenu() for i in community.GetMenuItems() if i.GetSubMenu() is not None)
    assert _labels(sub) == [
        # codex.md 6.5: the agent task, gated on the ChatGPT plan (10A.8).
        "&Find and Record (needs Copilot or Codex)...\tCtrl+F3",
        "&Which AI Am I Using\tCtrl+F8",
        "&Choose Your AI...\tCtrl+Shift+F8",
        "Use My Chat&GPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI &Usage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tAlt+Shift+F2",
    ]
    assert radio.commands.get("radio.describe_video") is not None


def test_an_existing_chatgpt_sign_in_stays_in_use_after_the_upgrade(radio) -> None:
    assert radio._radio_history.ai_connection == ""
    assert radio._ai_service().connection == "chatgpt"
    assert radio._radio_history.ai_connection == "chatgpt"


def test_ask_is_the_family_window_about_this_station_and_saves_each_exchange(
    radio, quill_data_dir: Path
) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    radio.cmd_ai_chat_key()
    frame = radio._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame.GetTitle() == "Ask"
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about this station.")
    frame._message.SetValue("What is this song?")
    frame._send()
    message, excerpts, requires = radio.sent[0]
    assert message == "What is this song?"
    assert "Station: KJAZZ" in excerpts[0]
    assert "Now playing: Blue in Green by Miles Davis" in excerpts[0]
    assert requires == ("text",)
    saved = list((quill_data_dir / "ai-sessions" / "radio").glob("*.json"))
    assert len(saved) == 1
    # The facts are read fresh, and a change is said once.
    radio.playing = "So What by Miles Davis"
    frame._message.SetValue("And now?")
    frame._send()
    assert radio.sent[1][1][0].startswith("Now playing changed since your last question.")
    assert "Now playing changed since your last question." in radio.said


def test_a_second_press_raises_the_open_ask_rather_than_building_another(radio) -> None:
    radio.cmd_ai_chat_key()
    first = radio._ai_windows["ask"]
    radio.cmd_ai_chat_key()
    assert radio._ai_windows["ask"] is first


def test_the_quick_list_keeps_radios_nine_then_its_own_then_the_familys(radio) -> None:
    from quill.core.ai.family_prompt_catalogue import FAMILY_PROMPTS
    from quill.core.radio.assistant_prompt import QUICK_QUESTIONS

    radio.cmd_ai_chat_key()
    frame = radio._ai_windows["ask"]
    labels = [row.label for row in frame._rows]
    assert labels[:9] == [q.label for q in QUICK_QUESTIONS]
    assert labels[9:11] == ["What is on next?", "Record this whenever it is on"]
    assert labels[11:] == [p.label for p in FAMILY_PROMPTS]


def test_what_can_i_do_here_is_answered_on_this_computer(radio) -> None:
    radio.cmd_ai_chat_key()
    frame = radio._ai_windows["ask"]
    local = next(i for i, row in enumerate(frame._rows) if row.local)
    frame.use_quick(local)
    assert radio.sent == []
    assert "favorite stations" in frame._conversation.last_answer()
    assert "The Community menu, Alt+C" in frame._conversation.last_answer()
    assert radio.said[-1].endswith("Answered on this computer. Nothing was sent.")


def test_listening_history_goes_only_with_the_question_that_asks_for_it(
    radio, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.radio import radio_ai_features

    monkeypatch.setattr(
        radio_ai_features, "_listening", lambda _host: [("WBGO", ["Song A", "Song B"])]
    )
    radio.cmd_ai_chat_key()
    frame = radio._ai_windows["ask"]
    frame._message.SetValue("What is my listening history across my stations?")
    frame._send()
    assert "Listening history" not in radio.sent[0][1][0]
    discover = next(i for i, row in enumerate(frame._rows) if row.consents)
    frame.use_quick(discover)
    frame._send()
    assert "WBGO: Song A; Song B" in radio.sent[1][1][0]


def test_alt_f5_opens_choose_your_ai_on_the_chatgpt_row(radio, monkeypatch) -> None:
    opened: list[tuple] = []
    monkeypatch.setattr(
        type(radio),
        "_ai_open_choose",
        lambda self, select="", *, sign_in=False: opened.append((select, sign_in)),
    )
    radio.commands.get("radio.chatgpt_account").handler()
    assert opened == [("chatgpt", False)]


def test_which_ai_speaks_and_pressed_twice_opens_the_window(radio, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(radio), "cmd_ai_choose", lambda self: opened.append("choose"))
    radio.cmd_ai_which()
    assert radio.said[-1].startswith("My ChatGPT plan")
    radio.cmd_ai_which()
    assert opened == ["choose"]


def test_a_route_sentence_names_radios_choose_key(radio) -> None:
    sentence = radio._ai_service()._keyed("Press Ctrl+4 to choose another.")
    assert sentence == "Press Ctrl+Shift+F8 to choose another."


def test_the_status_bar_ends_with_the_ai_cell(radio) -> None:
    specs = radio._status_bar._build_specs()
    assert specs[-1].key == "ai"
    assert specs[-1].text() == "AI: ChatGPT plan"


def test_safe_mode_refuses_every_ai_command(radio) -> None:
    radio._safe_mode = True
    radio.cmd_ai_chat_key()
    radio.cmd_ai_choose()
    assert "ask" not in getattr(radio, "_ai_windows", {})
    assert radio.said == ["AI is off in Safe Mode.", "AI is off in Safe Mode."]


class _Engine:
    def __init__(self) -> None:
        self.shots = 0

    def take_snapshot(self, path: str) -> bool:
        self.shots += 1
        Path(path).write_bytes(_png())
        return True


def test_describe_the_video_sends_nothing_where_the_connection_cannot_see(
    radio, monkeypatch: pytest.MonkeyPatch
) -> None:
    radio._radio_history.ai_connection = "free"
    monkeypatch.setattr(type(radio._ai_service()), "signed_in", property(lambda self: True))
    engine = _Engine()
    monkeypatch.setattr("quill.ui.radio.video_commands._engine", lambda _host: engine)
    radio._video_window = object()
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.hosted_ai_connections.ask_yes_no",
        lambda _parent, sentence, **_kw: asked.append(sentence) or False,
    )
    sent: list = []
    radio._ai_service().describe_image = lambda *a, **k: sent.append(a)
    radio.cmd_radio_describe_video()
    assert sent == []
    assert asked and "My ChatGPT plan can" in asked[0]
    assert engine.shots == 0


def test_describe_the_video_fits_one_picture_and_asks_once(
    radio, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PIL import Image

    engine = _Engine()
    monkeypatch.setattr("quill.ui.radio.video_commands._engine", lambda _host: engine)
    radio._video_window = object()
    shown: list = []
    monkeypatch.setattr(type(radio), "_show_ai_window", lambda self, frame: shown.append(frame))
    asked: list[tuple] = []

    def describe(path, question, *, on_done, on_error, requires):
        with Image.open(path) as picture:
            asked.append((max(picture.size), question, requires))
        on_done("A trumpet player on a stage.")

    radio._ai_service().describe_image = describe
    questions: list[str] = []
    monkeypatch.setattr(
        type(radio),
        "_show_message_box",
        lambda self, message, caption, style: questions.append(message) or wx.YES,
        raising=False,
    )
    radio.cmd_radio_describe_video()
    assert len(asked) == 1
    assert len(questions) == 1  # 10B.4: asked once, on the first picture
    assert questions[0].startswith(
        "Pictures you ask about in QUILL Radio go to OpenAI on your ChatGPT plan."
    )
    assert radio._radio_history.ai_picture_consent == ["chatgpt"]
    assert asked[0][0] <= 2048
    assert asked[0][2] == ("text", "pictures")
    assert len(shown) == 1
    assert any("Described by My ChatGPT plan. A trumpet player" in s for s in radio.said)
    radio.cmd_radio_describe_video()  # the same picture: answered from the cache
    assert len(asked) == 1
    assert any("Nothing was sent" in s for s in radio.said)
    assert len(questions) == 1  # not asked again on the same connection


def test_describe_the_video_sends_nothing_when_the_picture_consent_is_no(
    radio, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _Engine()
    monkeypatch.setattr("quill.ui.radio.video_commands._engine", lambda _host: engine)
    radio._video_window = object()
    asked: list[str] = []
    radio._ai_service().describe_image = lambda *a, **k: asked.append("sent")
    monkeypatch.setattr(type(radio), "_show_message_box", lambda self, *a: wx.NO, raising=False)
    radio.cmd_radio_describe_video()
    assert asked == []
    assert radio._radio_history.ai_picture_consent == []


def test_the_adapter_has_no_command_of_its_own() -> None:
    """Radio's adapter is hooks only; its commands are the shared module's and
    radio_ai_features' -- a second implementation is how the family forks."""
    from quill.ui.radio.radio_ai_host import RadioAiHost, RadioAiMixin

    assert [name for name in vars(RadioAiMixin) if name.startswith("cmd_")] == []
    assert [name for name in vars(RadioAiHost) if name.startswith("cmd_")] == []
