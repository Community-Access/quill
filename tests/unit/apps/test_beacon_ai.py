"""QuillBeacon's AI, in the real window (codex.md Phase 3, 10E.11, 10B.5).

Its own "QUILL Beacon" sign-in, the AI rows after the three local helpers in
Assist on decision 14's keys, Ask about the note or the search, Describe a
Saved Picture (OCR here first, then the gate, the consent and one picture),
the AI line and Safe Mode. The AI is a stand-in on the real service, OCR is a
stand-in, and the library is a temporary one, so nothing leaves the machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-beacon"
        self.web_search = False
        self.ended_by_openai = False


@pytest.fixture
def beacon(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    import quill.apps.beacon.app as beacon_app
    from quill.apps.beacon import ai as beacon_ai
    from quill.apps.beacon.announce import Announcer

    class _StatusBarOnly(Announcer):
        def _speak(self, *_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setenv("QUILLBEACON_DATA", str(quill_data_dir / "beacon"))
    monkeypatch.setattr(beacon_app, "Announcer", _StatusBarOnly)
    monkeypatch.setattr(beacon_app, "init_app_sound", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.app_sounds, "apply", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_setup_auto_sync", lambda self: None)
    monkeypatch.setattr(beacon_ai, "_ocr_text", lambda path: "SALE 50 PERCENT")
    frame = beacon_app.BeaconFrame()
    frame._safe_mode = False
    said: list[str] = []
    frame._announce = lambda message, *_a, **_kw: said.append(str(message))
    frame.said = said
    # Background work and "once the window is up" run straight through here.
    frame._beacon_ai_submit = lambda name, work, ok, bad: ok(name, work())
    frame._beacon_ai_call_after = lambda func, *args: func(*args)
    frame._ai_later = lambda func, *args: func(*args)
    frame.questions = []
    frame.answer_yes = False

    def yes_no(message, caption, parent):
        frame.questions.append((message, caption))
        return frame.answer_yes

    frame._beacon_ai_yes_no = yes_no
    frame._show_message_box = lambda message, caption, style: wx.ID_YES  # picture consent
    service = frame._ai_service()
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []

    def ask(feature, prompt, chunks, *, on_done, on_error, language="", requires=("text",)):
        frame.sent.append((feature, prompt, requires))
        on_done("An answer.", None)

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append(("converse", message, list(excerpts)))
        on_done("An answer.", None, 0)

    def describe_image(path, question, *, on_done, on_error, requires=("text", "pictures")):
        frame.sent.append(("describe", question, requires, Path(path).read_bytes()[:4]))
        on_done("A red sale poster.")

    service.ask = ask
    service.converse = converse
    service.describe_image = describe_image
    service._chatgpt = _Account(signed_in=True)
    frame._ai_host().settings.ai_connection = "chatgpt"
    frame.shown = []
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: frame.shown.append(window))
    try:
        yield frame
    finally:
        for window in [*getattr(frame, "_ai_windows", {}).values(), *frame.shown]:
            if window:
                window.Destroy()
        frame.Close()
        if frame:
            frame.Destroy()


def _seed(frame, title: str, *, note: str = "", tags=(), uri: str = "https://x.test/a"):
    from quill.apps.beacon.model import Beacon, Resource

    res = Resource(title=title, type="web", primary_uri=uri)
    b = Beacon(resource_id=res.resource_id, title=title, note=note, tags=list(tags))
    frame.store.put_beacon(b, resource=res)
    return b


def _select(frame, title: str):
    frame.last_query = ""
    frame._refresh_results()
    for index, row in enumerate(frame._results_cache):
        if row.title == title:
            frame.results.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            return row
    raise AssertionError(title)


def _picture(tmp: Path) -> Path:
    path = tmp / "shot.png"
    image = wx.Image(16, 16)
    image.SetRGB(wx.Rect(0, 0, 16, 16), 200, 20, 20)
    assert image.SaveFile(str(path), wx.BITMAP_TYPE_PNG)
    return path


def _attach(frame, b, path: Path) -> None:
    from quill.apps.beacon.model import Attachment

    frame.store.put_attachment(
        Attachment(beacon_id=b.beacon_id, name=path.name, kind="file", uri=str(path))
    )


def _assist(frame):
    bar = frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu("Assist"))


def test_the_ai_rows_follow_the_three_local_helpers_in_assist(beacon) -> None:
    beacon._app_ai_relabel()  # the plan in use can see, so no "(needs ...)" (10A.8)
    labels = [i.GetItemLabel() for i in _assist(beacon).GetMenuItems() if not i.IsSeparator()]
    assert labels == [
        "Suggest &Tags\tCtrl+Shift+T",
        "Suggest &Relationships\tCtrl+Shift+K",
        "&Summarize Note\tCtrl+Shift+M",
        "&Ask...\tCtrl+6",
        "&Which AI Am I Using\tCtrl+8",
        "&Choose Your AI...\tCtrl+4",
        "&Describe a Saved Picture...\tCtrl+F5",
        "Or&ganize What I Saved (needs Copilot or Codex)...\tCtrl+3",
        "Use My C&hatGPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "A&I Usage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tCtrl+Alt+Shift+K",
    ]
    letters = [label[label.index("&") + 1].upper() for label in labels]
    assert len(letters) == len(set(letters))
    bar = beacon.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert "A&I" not in titles and "&AI" not in titles  # no new top-level menu


def test_beacon_signs_in_as_itself(beacon) -> None:
    service = beacon._ai_service()
    assert service._app.ai_agent_name == "QUILL Beacon"
    del service._chatgpt
    assert service.chatgpt.agent_name == "QUILL Beacon"


def test_the_choice_is_kept_in_beacons_own_file(beacon) -> None:
    from quill.core.paths import app_data_dir

    beacon._ai_host().save_settings()
    saved = json.loads((app_data_dir() / "beacon-ai.json").read_text(encoding="utf-8"))
    assert saved["ai_connection"] == "chatgpt"


def test_ask_sends_the_selected_beacon_and_never_a_path(beacon) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    _seed(beacon, "Grant notes", note="Due on Friday.", tags=["work"], uri="C:\\secret\\a.txt")
    _select(beacon, "Grant notes")
    beacon.cmd_ai_chat_key()
    frame = beacon._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about this beacon")
    frame._message.SetValue("When is it due?")
    frame._send()
    facts = beacon.sent[0][2][0]
    assert "Note: Grant notes" in facts and "Due on Friday." in facts and "work" in facts
    assert "secret" not in facts and "beacons.db" not in facts


def test_ask_sends_the_search_and_its_results_when_a_search_is_typed(beacon) -> None:
    _seed(beacon, "Soup recipe", note="Lentils and cumin.")
    _seed(beacon, "Bread recipe", note="Flour, water, salt.")
    beacon.last_query = "recipe"
    beacon._refresh_results()
    facts = beacon._app_ask_facts("what did I save?", "")
    from quill.core.ai.app_ask_context import facts_text

    text = facts_text(facts)
    assert "Search: recipe" in text
    assert "- Soup recipe: Lentils and cumin." in text and "Bread recipe" in text


def test_describe_reads_here_first_then_sends_one_picture_and_offers_a_note(
    beacon, tmp_path
) -> None:
    b = _seed(beacon, "Poster", note="Seen downtown.")
    _attach(beacon, b, _picture(tmp_path))
    _select(beacon, "Poster")
    beacon.answer_yes = True
    beacon.cmd_beacon_describe_picture()
    kind, question, requires, head = beacon.sent[0]
    assert kind == "describe" and requires == ("text", "pictures")
    assert "SALE 50 PERCENT" in question  # OCR went with it
    assert head == b"\x89PNG" or head[:3] == b"\xff\xd8\xff"  # the fitted picture
    window = beacon.shown[0]
    assert window.GetTitle() == "Describe a Saved Picture"
    assert window._text.endswith("A red sale poster.")
    assert beacon.questions == [("Add this to the beacon's note?", "Add to Note")]
    note = beacon.store.get_beacon(b.beacon_id).note
    assert note.startswith("Seen downtown.\n\n") and note.endswith("A red sale poster.")
    beacon._on_undo(None)
    assert beacon.store.get_beacon(b.beacon_id).note == "Seen downtown."


def test_describe_no_keeps_the_note_and_asking_again_sends_nothing(beacon, tmp_path) -> None:
    b = _seed(beacon, "Poster", note="Seen downtown.")
    _attach(beacon, b, _picture(tmp_path))
    _select(beacon, "Poster")
    beacon.cmd_beacon_describe_picture()
    assert beacon.store.get_beacon(b.beacon_id).note == "Seen downtown."
    beacon.cmd_beacon_describe_picture()
    assert len(beacon.sent) == 1  # the cache answered
    assert "Nothing was sent" in beacon.shown[1]._text


def test_describe_with_no_picture_says_so_and_sends_nothing(beacon) -> None:
    _seed(beacon, "Plain link")
    _select(beacon, "Plain link")
    beacon.cmd_beacon_describe_picture()
    assert beacon.said[-1] == "This beacon has no saved picture. Nothing was sent."
    assert beacon.sent == []


def test_describe_a_saved_screenshot_file(beacon, tmp_path) -> None:
    path = _picture(tmp_path)
    _seed(beacon, "Screenshot", uri=str(path))
    _select(beacon, "Screenshot")
    beacon.cmd_beacon_describe_picture()
    assert beacon.sent and beacon.sent[0][0] == "describe"


def test_refusing_the_picture_consent_sends_nothing(beacon, tmp_path) -> None:
    b = _seed(beacon, "Poster")
    _attach(beacon, b, _picture(tmp_path))
    _select(beacon, "Poster")
    beacon._show_message_box = lambda message, caption, style: wx.ID_NO
    beacon.cmd_beacon_describe_picture()
    assert beacon.sent == [] and beacon.said[-1] == "Nothing was sent."


def test_a_connection_that_cannot_see_gets_the_words_read_here(
    beacon, tmp_path, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    b = _seed(beacon, "Poster")
    _attach(beacon, b, _picture(tmp_path))
    _select(beacon, "Poster")
    service = beacon._ai_service()
    monkeypatch.setattr(type(service), "can_do", lambda self, capability: capability != "pictures")
    offered: list[str] = []
    monkeypatch.setattr(
        connections,
        "ask_yes_no",
        lambda parent, sentence, default_yes=True: offered.append(sentence) or False,
    )
    beacon.cmd_beacon_describe_picture()
    assert beacon.sent == []
    window = beacon.shown[-1]
    assert window.GetTitle() == "Read on This Computer"
    assert "Nothing was sent" in window._text and "SALE 50 PERCENT" in window._text


def test_safe_mode_refuses_every_ai_command(beacon, tmp_path) -> None:
    b = _seed(beacon, "Poster")
    _attach(beacon, b, _picture(tmp_path))
    _select(beacon, "Poster")
    beacon._safe_mode = True
    for command in (
        lambda w: w.cmd_ai_chat_key(),
        lambda w: w.cmd_ai_which(),
        lambda w: w.cmd_ai_choose(),
        lambda w: w.cmd_ai_usage(),
        lambda w: w.cmd_ai_chatgpt(),
        lambda w: w.cmd_ai_own_key(),
        lambda w: w.cmd_beacon_describe_picture(),
    ):
        beacon.said.clear()
        command(beacon)
        assert beacon.said == ["AI is off in Safe Mode."]
    assert beacon.sent == []


def test_the_ai_line_says_which_ai_and_enter_opens_choose(beacon, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(beacon), "cmd_ai_choose", lambda self: opened.append("x"))
    assert beacon._ai_text.GetValue().startswith("AI")
    assert beacon._ai_text.GetParent().GetName() == "Results and details"
    assert "Choose Your AI" in beacon._ai_text.GetHelpText()
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_RETURN)
    beacon._on_ai_line_key(event)
    assert opened == ["x"]


def test_every_ai_window_title_has_an_authored_purpose() -> None:
    from quill.apps.beacon import surface_help
    from quill.apps.beacon.ai import DESCRIBE_TITLE, LOCAL_TITLE

    for title in (
        "Ask",
        DESCRIBE_TITLE,
        LOCAL_TITLE,
        "Choose Your AI",
        "Sign In to Your AI",
        "AI Usage",
    ):
        assert title in surface_help.PURPOSES


def test_the_adapter_has_no_command_of_its_own() -> None:
    from quill.apps.beacon.ai import BeaconAiMixin
    from quill.ui.hosted_ai_app_adapter import AppAiHost, AppAiMixin

    for cls in (BeaconAiMixin, AppAiMixin, AppAiHost):
        assert [name for name in vars(cls) if name.startswith("cmd_")] == []
