"""Start and Stop Watching for Changes, in the real QUILL Studio window (decision 25).

The screen grab and the AI are stand-ins (a coloured picture and the real
service's describe_image replaced), and the worker and CallAfter run inline,
so nothing is captured from this screen and nothing leaves the machine.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


def _png(colour: str) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (64, 48), colour).save(out, format="PNG")
    return out.getvalue()


class _Account:
    def __init__(self) -> None:
        self.signed_in = True
        self.model = ""
        self.slug = "quill-studio"
        self.web_search = False
        self.ended_by_openai = False


@pytest.fixture
def studio(quill_data_dir, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.studio import StudioAppFrame
    from quill.ui.change_watch_controller import ChangeWatchController
    from quill.ui.dialog_contract import set_transition_announcement_policy

    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: True)
    frame = StudioAppFrame()
    frame.said = []
    frame._announce = lambda message, **_kw: frame.said.append(str(message))
    frame.boxes = []
    frame.box_answer = wx.YES

    def box(message, _caption, _style=None, parent=None):
        frame.boxes.append(str(message))
        return frame.box_answer

    frame._show_message_box = box
    service = frame._ai_service()
    service._chatgpt = _Account()
    frame._ai_host().settings.ai_connection = ""
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []

    def describe(path, question, *, on_done, on_error, requires):
        frame.sent.append((question, requires))
        on_done("A save dialog opened.")

    service.describe_image = describe
    frame.picture = {"now": _png("red")}
    frame.grabs = []

    def grab(target):
        frame.grabs.append(target)
        return frame.picture["now"]

    monkeypatch.setattr("quill.ui.audio_studio.studio_ai_watch._grab", grab)
    target = SimpleNamespace(kind="window", window_handle=42, friendly_label="Notepad")
    monkeypatch.setattr(
        type(frame), "_studio_watch_target", lambda self: (target, "Notepad"), raising=False
    )

    def inline(name, work, *, on_success=None, on_failure=None):
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            on_failure(name, error)
            return
        on_success(name, result)

    frame._change_watch_controller = ChangeWatchController(
        frame, submit=inline, call_after=lambda fn, *a: fn(*a), ocr=lambda _d: ""
    )
    try:
        yield frame
    finally:
        frame._change_watch_controller._stop_timer()
        remove = getattr(frame, "_remove_tray_icon", None)
        if callable(remove):
            remove()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


def _ai_labels(frame) -> list[str]:
    bar = frame.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    return [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]


def test_the_two_rows_are_on_the_ai_menu_with_their_keys(studio) -> None:
    studio._ai_connection_refresh()
    labels = _ai_labels(studio)
    assert "Start Watching for C&hanges\tCtrl+F9" in labels
    assert "S&top Watching for Changes\tCtrl+Shift+F9" in labels
    for command_id in ("studio.ai_watch_start", "studio.ai_watch_stop"):
        assert studio.commands.get(command_id) is not None


def test_start_asks_consent_then_watches_and_reports_a_change(studio) -> None:
    (lambda w: w.cmd_studio_watch_start())(studio)
    assert studio.said[-1] == "Watching Notepad for changes."
    assert [b for b in studio.boxes if b.startswith("Pictures you ask about in QUILL Studio")]
    controller = studio._change_watch_controller
    assert controller.watching and controller._timer.IsRunning()
    controller.tick()  # baseline
    studio.picture["now"] = _png("blue")
    controller.tick()
    assert studio.said[-1] == "A save dialog opened."
    assert studio.sent and studio.sent[0][1] == ("text", "pictures")
    (lambda w: w.cmd_studio_watch_stop())(studio)
    assert studio.said[-1] == "Stopped watching Notepad."
    assert not controller._timer.IsRunning()


def test_stop_with_nothing_watched_says_so(studio) -> None:
    (lambda w: w.cmd_studio_watch_stop())(studio)
    assert studio.said == ["Nothing was being watched."]


def test_safe_mode_refuses_the_start(studio) -> None:
    studio._safe_mode = True
    (lambda w: w.cmd_studio_watch_start())(studio)
    assert studio.said == ["AI is off in Safe Mode."]
    assert studio.grabs == [] and not studio._change_watch_controller.watching


def test_declining_the_picture_consent_starts_nothing(studio) -> None:
    studio.box_answer = wx.NO
    (lambda w: w.cmd_studio_watch_start())(studio)
    assert not studio._change_watch_controller.watching
    assert studio._ai_host().settings.ai_picture_consent == []
    assert studio.said[-1].startswith("Nothing is being watched")


def test_a_connection_that_cannot_see_offers_the_switch_and_starts_nothing(
    studio, monkeypatch
) -> None:
    studio._ai_host().settings.ai_connection = "free"
    monkeypatch.setattr(type(studio._ai_service()), "signed_in", property(lambda self: True))
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.hosted_ai_connections.ask_yes_no",
        lambda _parent, sentence, **_kw: asked.append(sentence) or False,
    )
    (lambda w: w.cmd_studio_watch_start())(studio)
    assert asked and not studio._change_watch_controller.watching


def test_closing_the_window_ends_the_watch(studio) -> None:
    (lambda w: w.cmd_studio_watch_start())(studio)
    controller = studio._change_watch_controller
    controller.tick()
    grabs = len(studio.grabs)
    controller.window_closed()
    controller.tick()
    assert len(studio.grabs) == grabs and not controller.watching
