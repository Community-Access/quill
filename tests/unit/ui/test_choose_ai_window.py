"""Choose Your AI, built for real (codex.md 10A.3), and the one Usage view (10A.11).

The service is a stand-in with the Phase 1a surface the window reads
(``connection_rows``, ``capability_record``, ``choose``, ...), so what is
tested is the window: its five controls, which row it lands on, what the one
button says and does, and that the only things spoken are outcomes.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.ai.connection_caps import record_for
from quill.core.ai.connection_choice import ConnectionFacts, row_states
from quill.ui import hosted_ai_connections as connections
from quill.ui.hosted_ai_connections import ChooseAiFrame, ChooseAiHooks
from quill.ui.hosted_ai_usage import UsageFrame


class _Account:
    def __init__(self, signed_in: bool = False) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.signed_out = 0

    def set_model(self, model: str) -> None:
        self.model = model

    def sign_out(self) -> bool:
        self.signed_out += 1
        self.signed_in = False
        return True

    def cancel_sign_in(self) -> None:
        pass


class _Service:
    """Just the surface Choose Your AI reads, over ConnectionFacts."""

    own_key_provider = "openai"

    def __init__(self, *, stored="free", free=False, chatgpt=False, own_key=False) -> None:
        self.stored = stored
        self.signed_in = free
        self.own_key = own_key
        self.chatgpt = _Account(chatgpt)
        self.chosen: list[str] = []
        self.changed: list[str] = []
        self.free_signed_out = 0

    def facts(self) -> ConnectionFacts:
        return ConnectionFacts(
            stored=self.stored,
            free_connected=self.signed_in,
            chatgpt_signed_in=self.chatgpt.signed_in,
            own_key_ready=self.own_key,
        )

    def connection_rows(self):
        return row_states(self.facts())

    @property
    def connection_in_use(self) -> str:
        from quill.core.ai.connection_choice import in_use

        return in_use(self.facts())

    def capability_record(self, connection=""):
        return record_for(connection or self.stored)

    def connection_model(self, connection=""):
        return self.chatgpt.model if connection == "chatgpt" else ""

    def choose(self, connection: str) -> bool:
        self.chosen.append(connection)
        self.stored = connection
        return True

    def note_readiness(self) -> None:
        pass

    def connection_changed(self, connection: str) -> None:
        self.changed.append(connection)

    def sign_out(self) -> None:
        self.free_signed_out += 1
        self.signed_in = False


def _hooks(said: list[str], **overrides) -> ChooseAiHooks:
    values = {
        "announce": said.append,
        "connect_free": lambda: said.append("<connect>"),
        "own_key": lambda: "",
        "changed": lambda: said.append("<changed>"),
        "list_models": lambda _c: ([("gpt-a", "GPT A"), ("gpt-b", "GPT B")], ""),
    }
    values.update(overrides)
    return ChooseAiHooks(**values)


@pytest.fixture
def window(wx_session_app, monkeypatch, wx_call_after):
    """A factory; every frame it builds is destroyed at teardown."""
    import quill.ui.update_download as download

    # Model discovery answers at once, on this thread, as the worker would.
    def submit(_name, work, *, on_success=None, on_failure=None):
        on_success(_name, work())

    monkeypatch.setattr(download, "thread_submit", submit)
    wx_call_after()  # and its answer lands inline
    built: list[ChooseAiFrame] = []

    def make(service, said, **kwargs):
        select = kwargs.pop("select", "")
        frame = ChooseAiFrame(None, service, _hooks(said, **kwargs), select=select)
        built.append(frame)
        return frame

    yield make
    for frame in built:
        if frame:
            frame.Destroy()


def _row_texts(frame) -> list[str]:
    return [frame._list.GetString(i) for i in range(frame._list.GetCount())]


def test_five_controls_and_focus_on_the_row_in_use(window) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()  # SetHelpText stores nothing without one
    said: list[str] = []
    frame = window(_Service(stored="chatgpt", chatgpt=True), said)

    assert frame.GetTitle() == "Choose Your AI"
    assert _row_texts(frame)[1] == "My ChatGPT plan, in use"
    assert frame._list.GetSelection() == 1
    assert frame._focus_target is frame._list
    assert frame._action.GetLabel() == "Sign &Out"
    assert frame._about.GetValue().startswith("Text and pictures")
    for control in (frame._list, frame._about, frame._model, frame._action):
        assert control.GetHelpText(), control
    assert said == [], "nothing is spoken on open (GATE-13)"


def test_the_button_follows_the_row(window) -> None:
    frame = window(_Service(stored="free", free=True, chatgpt=True), [])

    frame.select("chatgpt")
    assert frame._action.GetLabel() == "&Use This"
    frame.select("own_key")
    assert frame._action.GetLabel() == "&Sign In..."
    frame.select("copilot")
    assert _row_texts(frame)[2] == "My GitHub Copilot, not available yet"


def test_the_free_ai_chooses_no_model_and_a_signed_out_row_has_none(window) -> None:
    frame = window(_Service(stored="free"), [])

    assert frame._model.GetString(0) == "QUILL chooses the model"
    assert not frame._model.IsEnabled()
    frame.select("own_key")
    assert frame._model.GetString(0) == "Sign in to see the models"


def test_the_plan_lists_its_models_recommended_first_and_saves_a_choice(window) -> None:
    service = _Service(stored="chatgpt", chatgpt=True)
    frame = window(service, [])

    assert frame._model.GetString(0) == "GPT A (recommended)"
    assert frame._model.IsEnabled()
    frame._model.SetSelection(1)
    frame._on_model_chosen()
    assert service.chatgpt.model == "gpt-b"


def test_a_failed_model_list_says_the_recommended_model_is_used(window) -> None:
    frame = window(
        _Service(stored="chatgpt", chatgpt=True), [], list_models=lambda _c: ([], "no network")
    )

    assert frame._model.GetString(0) == (
        "Could not read the model list. The recommended model is used."
    )


def test_use_this_chooses_and_says_so_once(window) -> None:
    said: list[str] = []
    service = _Service(stored="free", free=True, chatgpt=True)
    frame = window(service, said, select="chatgpt")

    frame.do_action()

    assert service.chosen == ["chatgpt"]
    assert said == ["<changed>", "Now using My ChatGPT plan."]
    assert _row_texts(frame)[1] == "My ChatGPT plan, in use"


def test_delete_signs_out_of_the_row_in_use_after_a_no_default_question(
    window, monkeypatch
) -> None:
    asked: list[tuple[str, bool]] = []

    def answer(_parent, sentence, *, default_yes):
        asked.append((sentence, default_yes))
        return True

    monkeypatch.setattr(connections, "ask_yes_no", answer)
    said: list[str] = []
    service = _Service(stored="chatgpt", chatgpt=True)
    frame = window(service, said)

    frame._ask_sign_out()

    assert asked == [("Sign out of My ChatGPT plan?", False)]
    assert service.chatgpt.signed_out == 1
    assert said[-1] == "Signed out. No AI is in use until you choose one."
    assert "in use" not in _row_texts(frame)[1]


def test_no_to_the_question_changes_nothing(window, monkeypatch) -> None:
    monkeypatch.setattr(connections, "ask_yes_no", lambda *_a, **_k: False)
    service = _Service(stored="chatgpt", chatgpt=True)
    frame = window(service, [])

    frame._ask_sign_out()

    assert service.chatgpt.signed_out == 0


def test_the_free_ai_sign_in_chooses_it_and_opens_connect(window) -> None:
    said: list[str] = []
    service = _Service(stored="chatgpt", chatgpt=True)
    frame = window(service, said, select="free")

    frame.do_action()

    assert service.chosen == ["free"]
    assert said[-1] == "<connect>"


def test_an_own_key_saved_in_its_step_is_signed_in_and_in_use(window) -> None:
    said: list[str] = []
    service = _Service(stored="free", free=True)

    def own_key() -> str:
        service.own_key = True
        service.stored = "own_key"  # signing in is choosing (the service does this)
        return "AI help uses your own OpenAI key, with no limits."

    frame = window(service, said, select="own_key", own_key=own_key)
    frame.do_action()

    assert service.changed == ["own_key"]
    assert said[-1] == "Signed in to My own key. It is now in use."


def test_cancelling_the_own_key_step_says_nothing(window) -> None:
    said: list[str] = []
    frame = window(_Service(), said, select="own_key")

    frame.do_action()

    assert said == []


def test_the_plan_sign_in_step_reports_success(window, monkeypatch) -> None:
    said: list[str] = []
    service = _Service(stored="free", free=True)

    def show(step, _title):
        service.chatgpt.signed_in = True
        service.stored = "chatgpt"
        assert "approve QUILL on OpenAI's page" in step.status.GetValue()
        return wx.ID_OK

    monkeypatch.setattr(connections, "show_modal_dialog", show)
    frame = window(service, said, select="chatgpt")
    frame.do_action()

    assert service.changed == ["chatgpt"]
    assert said[-1] == "Signed in to My ChatGPT plan. It is now in use."


def test_cancelling_the_plan_sign_in_says_nothing(window, monkeypatch) -> None:
    said: list[str] = []
    monkeypatch.setattr(connections, "show_modal_dialog", lambda _s, _t: wx.ID_CANCEL)
    frame = window(_Service(), said, select="chatgpt")

    frame.do_action()

    assert said == []


def test_copilot_and_codex_say_not_available_yet(window) -> None:
    said: list[str] = []
    frame = window(_Service(), said, select="copilot")

    frame.do_action()

    assert said == ["My GitHub Copilot is not available yet. It comes in a later update."]


def test_safe_mode_says_ai_is_off_and_signs_nothing_in(window) -> None:
    said: list[str] = []
    service = _Service()
    frame = window(service, said, select="chatgpt", safe_mode=True)

    assert "Safe Mode" in frame._about.GetValue()
    frame.do_action()
    assert service.chosen == []
    assert "Safe Mode" in said[-1]


def test_escape_closes_the_window(window) -> None:
    frame = window(_Service(), [])
    closed = []
    frame.Bind(wx.EVT_CLOSE, lambda event: (closed.append(True), event.Skip()))
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)
    event.SetEventObject(frame)
    frame.GetEventHandler().ProcessEvent(event)
    assert closed == [True]


# --------------------------------------------------------------------------- #
# The one Usage view
# --------------------------------------------------------------------------- #


def _usage_service(rows):
    return SimpleNamespace(
        usage_rows=lambda _quota=None: rows,
        connection_in_use="chatgpt",
        fetch_quota=lambda **_k: None,
    )


def test_usage_is_one_list_of_sentences_on_the_row_in_use(wx_session_app) -> None:
    rows = [
        SimpleNamespace(
            connection="free", sentence="QUILL's free AI: no count yet.", detail="", manage_url=""
        ),
        SimpleNamespace(
            connection="chatgpt",
            sentence="My ChatGPT plan: 3 requests today from QUILL, counted on this computer.",
            detail="This week, 9 requests.",
            manage_url="https://chatgpt.com/settings/usage",
        ),
    ]
    frame = UsageFrame(None, _usage_service(rows), lambda _t: None)
    try:
        assert frame.GetTitle() == "AI Usage"
        assert frame._list.GetCount() == 2
        assert frame._list.GetSelection() == 1
        assert frame._list.GetString(1).endswith("This week, 9 requests.")
        assert frame._focus_target is frame._list
    finally:
        frame.Destroy()


def test_manage_usage_on_a_row_without_a_page_says_so(wx_session_app) -> None:
    said: list[str] = []
    rows = [SimpleNamespace(connection="free", sentence="Free.", detail="", manage_url="")]
    frame = UsageFrame(None, _usage_service(rows), said.append)
    try:
        frame._list.SetSelection(0)
        frame.manage()
        assert said == ["This connection has no usage page. The count here is the whole story."]
    finally:
        frame.Destroy()


def test_the_free_count_arriving_is_spoken_once(wx_session_app) -> None:
    said: list[str] = []
    service = _usage_service([])
    service.usage_rows = lambda quota=None: [
        SimpleNamespace(
            connection="free",
            sentence="QUILL's free AI: 4 of 50 requests today." if quota else "no count",
            detail="",
            manage_url="",
        )
    ]
    frame = UsageFrame(None, service, said.append)
    try:
        frame._free_arrived(object())
        assert said == ["QUILL's free AI: 4 of 50 requests today."]
        assert frame._list.GetString(0) == "QUILL's free AI: 4 of 50 requests today."
    finally:
        frame.Destroy()
