"""QUILL Studio's AI, in the real window (codex.md Phase 3).

Studio's own picture chooser folded into Choose Your AI: the AI menu, Ask with
Studio's facts, Which AI, Usage, the AI status cell, Describe a Picture through
picture_prep with the 10B.4 consent, and the Screenshot Inspector sending to
the connection in use. The AI is a stand-in on the real service, so nothing
leaves the machine.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


class _Account:
    """A ChatGPT sign-in that is (or is not) there, and never touches a store."""

    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-studio"
        self.web_search = False
        self.ended_by_openai = False


class _Tasks:
    """Runs a task at once, on this thread, the way the UI would see it finish."""

    def submit(self, name, work, *, on_success=None, on_failure=None, **_kw):
        from quill.stability.task_manager import CancellationToken

        handle = SimpleNamespace(cancellation_token=CancellationToken())
        try:
            result = work(cancellation_token=handle.cancellation_token)
        except Exception as error:  # noqa: BLE001 - delivered like the real one
            if on_failure is not None:
                on_failure(name, error)
            return handle
        if on_success is not None:
            on_success(name, result)
        return handle


def _png(path: Path, width: int = 3000, height: int = 1500) -> Path:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(out, format="PNG")
    path.write_bytes(out.getvalue())
    return path


@pytest.fixture
def studio(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch, request):
    from quill.apps.studio import StudioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: True)
    frame = StudioAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    boxes: list[str] = []
    frame.box_answer = wx.YES

    def box(message, _caption, _style=None, parent=None):
        boxes.append(str(message))
        return frame.box_answer

    frame._show_message_box = box
    frame.boxes = boxes
    service = frame._ai_service()
    service._chatgpt = _Account(signed_in=True)
    frame._ai_host().settings.ai_connection = ""
    frame._ai_host()._ai_status_text = None
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame._task_manager = _Tasks()
    frame.sent = []

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append((message, list(excerpts), requires))
        on_done("An answer.", None, 0)

    service.converse = converse
    try:
        yield frame
    finally:
        for window in list(getattr(frame, "_ai_windows", {}).values()):
            if window:
                window.Destroy()
        remove = getattr(frame, "_remove_tray_icon", None)
        if callable(remove):
            remove()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


def _ai_menu(frame):
    bar = frame.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    return [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]


def test_the_ai_menu_has_the_family_rows_on_the_editors_keys(studio) -> None:
    # Built at start on the free AI, which cannot see; the plan's sign-in
    # (faked after the build) clears the Describe row's "needs".
    studio._ai_connection_refresh()
    assert _ai_menu(studio) == [
        "&Ask...\tCtrl+6",
        "&Which AI Am I Using\tCtrl+8",
        "&Choose Your AI...\tCtrl+4",
        # The agent tasks say what they need on the ChatGPT plan (codex.md 10A.8).
        "&Recording Pre-flight Check (needs Copilot or Codex)...\tCtrl+3",
        "&Narrate a Recording (needs Copilot or Codex)...\tCtrl+Shift+3",
        "&Describe a Picture...\tCtrl+F5",
        "Start Watching for C&hanges\tCtrl+F9",
        "S&top Watching for Changes\tCtrl+Shift+F9",
        "Use My Chat&GPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI U&sage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tAlt+Shift+F2",
        "Set &Up AI...\tCtrl+Alt+Shift+A",
    ]
    for command_id in (
        "tools.hosted_ai_which",
        "studio.describe_picture",
        "studio.chatgpt_account",
    ):
        assert studio.commands.get(command_id) is not None


def test_the_capture_menu_no_longer_holds_the_chatgpt_row(studio) -> None:
    bar = studio.frame.GetMenuBar()
    capture = bar.GetMenu(bar.FindMenu("Capture"))
    labels = [item.GetItemLabelText() for item in capture.GetMenuItems()]
    assert not any("ChatGPT" in label for label in labels)


def test_an_existing_studio_sign_in_stays_in_use_after_the_upgrade(studio) -> None:
    assert studio._ai_service()._app.ai_agent_name == "QUILL Studio"
    assert studio._ai_service().connection == "chatgpt"
    assert studio._ai_host().settings.ai_connection == "chatgpt"


def test_the_choice_is_saved_in_studios_own_file(studio, quill_data_dir: Path) -> None:
    from quill.core.audio_studio.ai_settings import load_ai_settings

    studio._ai_service().connection  # noqa: B018 - reading it runs the migration
    assert load_ai_settings(quill_data_dir).ai_connection == "chatgpt"


def test_ask_is_the_family_window_about_the_recording_setup(studio, quill_data_dir) -> None:
    from quill.core.demo_recording import Finding
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    studio._studio_last_check = (
        "Ready to record the whole screen.",
        (Finding("warning", "The laptop is on battery."),),
        SimpleNamespace(display_count=2, video_backend="ddagrab", on_battery=True),
    )
    studio._active_book_path = str(quill_data_dir / "Sea Stories.m4b")
    studio.cmd_ai_chat_key()
    frame = studio._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about your recording setup.")
    frame._message.SetValue("Is my setup ready?")
    frame._send()
    message, excerpts, requires = studio.sent[0]
    assert message == "Is my setup ready?" and requires == ("text",)
    facts = excerpts[0]
    assert "Recording plan: Ready to record the whole screen." in facts
    assert "warning: The laptop is on battery." in facts
    assert "Displays: 2" in facts and "Power: on battery" in facts
    assert "Book open: Sea Stories" in facts
    assert str(quill_data_dir) not in facts  # the name, never the path
    assert list((quill_data_dir / "ai-sessions" / "studio").glob("*.json"))


def test_the_quick_list_starts_with_studios_own_questions(studio) -> None:
    studio.cmd_ai_chat_key()
    frame = studio._ai_windows["ask"]
    labels = [frame._quick.GetString(i) for i in range(frame._quick.GetCount())]
    assert labels[1:3] == ["Is my setup ready?", "Does this recording look right?"]
    assert "What can I do here?" in labels


def test_which_ai_speaks_and_pressed_twice_opens_choose_your_ai(studio, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(studio), "_ai_open_choose", lambda self, *a, **k: opened.append("x"))
    studio.cmd_ai_which()
    assert studio.said and "ChatGPT plan" in studio.said[-1]
    studio.cmd_ai_which()
    assert opened == ["x"]


def test_usage_opens_the_one_usage_list(studio, monkeypatch) -> None:
    built: list[str] = []
    monkeypatch.setattr(
        type(studio), "_open_ai_window", lambda self, name, build: built.append(name)
    )
    studio.cmd_ai_usage()
    assert built == ["usage"]


def test_the_status_bar_ends_with_the_ai_cell(studio) -> None:
    specs = studio._status_bar._build_specs()
    assert specs[-1].key == "ai"
    assert specs[-1].text() == "AI: ChatGPT plan"
    assert "Choose Your AI" in specs[-1].help


def test_safe_mode_refuses_every_ai_command(studio) -> None:
    studio._safe_mode = True
    sent: list = []
    studio._ai_service().describe_image = lambda *a, **k: sent.append(a)
    for command in (
        studio.cmd_ai_chat_key,
        studio.cmd_ai_which,
        studio.cmd_ai_choose,
        studio.cmd_ai_usage,
        studio.cmd_studio_describe_picture,
    ):
        studio.said.clear()
        command()
        assert studio.said == ["AI is off in Safe Mode."], command.__name__
    assert sent == [] and studio.sent == []


def test_describe_sends_nothing_where_the_connection_cannot_see(studio, monkeypatch) -> None:
    studio._ai_host().settings.ai_connection = "free"
    monkeypatch.setattr(type(studio._ai_service()), "signed_in", property(lambda self: True))
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.hosted_ai_connections.ask_yes_no",
        lambda _parent, sentence, **_kw: asked.append(sentence) or False,
    )
    chose: list = []
    monkeypatch.setattr(type(studio), "_studio_choose_picture", lambda self: chose.append(1))
    sent: list = []
    studio._ai_service().describe_image = lambda *a, **k: sent.append(a)
    studio.cmd_studio_describe_picture()
    assert sent == [] and chose == []
    assert asked and "My ChatGPT plan can" in asked[0]


def test_describe_asks_the_picture_consent_once_then_fits_and_caches(
    studio, monkeypatch, tmp_path: Path
) -> None:
    from PIL import Image

    picture = _png(tmp_path / "frame.png")
    monkeypatch.setattr(type(studio), "_studio_choose_picture", lambda self: picture)
    shown: list = []
    monkeypatch.setattr(type(studio), "_show_ai_window", lambda self, frame: shown.append(frame))
    asked: list[tuple] = []

    def describe(path, question, *, on_done, on_error, requires):
        with Image.open(path) as opened:
            asked.append((max(opened.size), requires))
        on_done("A blue square.")

    studio._ai_service().describe_image = describe
    studio.cmd_studio_describe_picture()
    consent = [b for b in studio.boxes if b.startswith("Pictures you ask about in QUILL Studio")]
    assert consent == [
        "Pictures you ask about in QUILL Studio go to OpenAI on your ChatGPT plan. Nothing is "
        "sent until you ask. Send pictures you ask about this way?"
    ]
    assert asked == [(asked[0][0], ("text", "pictures"))] and asked[0][0] <= 2048
    assert any("Described by My ChatGPT plan. A blue square." in s for s in studio.said)
    assert len(shown) == 1
    studio.cmd_studio_describe_picture()  # the same picture: from the cache, no consent
    assert len(asked) == 1
    assert len([b for b in studio.boxes if b.startswith("Pictures you ask")]) == 1
    assert any("Nothing was sent" in s for s in studio.said)


def test_declining_the_picture_consent_sends_nothing(studio, monkeypatch, tmp_path) -> None:
    studio.box_answer = wx.NO
    monkeypatch.setattr(type(studio), "_studio_choose_picture", lambda self: tmp_path / "x.png")
    sent: list = []
    studio._ai_service().describe_image = lambda *a, **k: sent.append(a)
    studio.cmd_studio_describe_picture()
    assert sent == []
    assert studio._ai_host().settings.ai_picture_consent == []


def test_a_video_frame_is_described_with_its_time(studio, monkeypatch, tmp_path: Path) -> None:
    from quill.core.ai import picture_prep

    video = tmp_path / "talk.mp4"
    video.write_bytes(b"not really a video")
    monkeypatch.setattr(type(studio), "_studio_choose_picture", lambda self: video)
    monkeypatch.setattr(type(studio), "_studio_ask_time", lambda self: 130.0)
    monkeypatch.setattr(type(studio), "_demo_ffmpeg", lambda self: "ffmpeg.exe")
    taken: list = []

    def frames(ffmpeg, path, times, scratch, **_kw):
        taken.append((path, list(times)))
        return [picture_prep.Frame(times[0], _png(scratch / "f.png", 800, 600))]

    monkeypatch.setattr(picture_prep, "extract_frames", frames)
    monkeypatch.setattr(type(studio), "_show_ai_window", lambda self, frame: None)
    studio._ai_service().describe_image = lambda path, q, *, on_done, on_error, requires: on_done(
        "A speaker at a lectern."
    )
    studio.cmd_studio_describe_picture()
    assert taken == [(video, [130.0])]
    assert any("2:10" in s and "A speaker at a lectern." in s for s in studio.said)


def test_the_describe_row_says_what_it_needs_on_a_connection_that_cannot_see(studio) -> None:
    studio._ai_host().settings.ai_connection = "free"
    studio._ai_connection_refresh()
    describe = next(label for label in _ai_menu(studio) if label.startswith("&Describe"))
    assert "(needs a connection that sees)" in describe


def test_the_adapter_has_no_command_of_its_own() -> None:
    """The adapter is hooks only; a second implementation is how the family forks."""
    from quill.ui.audio_studio.studio_ai_host import StudioAiHost, StudioAiMixin

    assert [name for name in vars(StudioAiMixin) if name.startswith("cmd_")] == []
    assert [name for name in vars(StudioAiHost) if name.startswith("cmd_")] == []
