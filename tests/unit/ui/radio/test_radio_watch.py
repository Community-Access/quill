"""Start and Stop Watching for Changes, in the real Quill Radio window (decision 25).

The video engine and the AI are stand-ins, and the worker and CallAfter run
inline, so nothing plays, nothing is captured and nothing leaves the machine.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in tests/conftest.py).
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
        self.slug = "quill-radio"
        self.web_search = False
        self.ended_by_openai = False


class _Engine:
    def __init__(self) -> None:
        self.colour = "red"
        self.shots = 0

    def take_snapshot(self, path: str) -> bool:
        self.shots += 1
        Path(path).write_bytes(_png(self.colour))
        return True


@pytest.fixture
def radio(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.radio import RadioAppFrame
    from quill.ui.change_watch_controller import ChangeWatchController
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    frame.said = []
    frame._announce = lambda message, **_kw: frame.said.append(str(message))
    service = frame._ai_service()
    service._chatgpt = _Account()
    frame._radio_history.ai_connection = ""
    frame._ai_host()._ai_status_text = None
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []

    def describe(path, question, *, on_done, on_error, requires):
        frame.sent.append((question, requires))
        on_done("A new slide shows the agenda.")

    service.describe_image = describe
    frame.questions = []
    frame.box_answer = wx.YES
    monkeypatch.setattr(
        type(frame),
        "_show_message_box",
        lambda self, message, caption, style: frame.questions.append(message) or frame.box_answer,
        raising=False,
    )
    frame.engine = _Engine()
    monkeypatch.setattr("quill.ui.radio.video_commands._engine", lambda _host: frame.engine)

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
        frame._video_window = None
        frame._radio_shutdown()
        set_transition_announcement_policy(None)


def _video_labels(frame) -> list[str]:
    bar = frame.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("Video"))
    return [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]


def test_the_two_rows_sit_with_describe_the_video_on_radios_keys(radio) -> None:
    labels = _video_labels(radio)
    start = next(i for i, label in enumerate(labels) if label.startswith("Start &Watching"))
    assert labels[start].endswith("\tCtrl+F9")
    assert labels[start + 1] == "Sto&p Watching for Changes\tCtrl+Shift+F9"
    assert labels[start - 1].startswith("&Describe the Video")
    for command_id in ("radio.ai_watch_start", "radio.ai_watch_stop"):
        assert radio.commands.get(command_id) is not None


def test_with_no_video_showing_it_says_so_and_asks_nothing(radio) -> None:
    radio._video_window = None
    (lambda w: w.cmd_radio_watch_start())(radio)
    assert radio.said == ["There is no picture to watch. Show the video first."]
    assert radio.questions == [] and radio.engine.shots == 0


def test_start_watches_the_video_and_reports_a_change_then_stop(radio) -> None:
    radio._video_window = SimpleNamespace()
    (lambda w: w.cmd_radio_watch_start())(radio)
    assert radio.said[-1] == "Watching the video for changes."
    assert len(radio.questions) == 1  # 10B.4, before the watch starts
    assert radio._radio_history.ai_picture_consent == ["chatgpt"]
    controller = radio._change_watch_controller
    controller.tick()
    radio.engine.colour = "blue"
    controller.tick()
    assert radio.said[-1] == "A new slide shows the agenda."
    assert radio.sent[0][1] == ("text", "pictures")
    (lambda w: w.cmd_radio_watch_stop())(radio)
    assert radio.said[-1] == "Stopped watching the video."


def test_hiding_the_video_ends_the_watch(radio) -> None:
    radio._video_window = SimpleNamespace()
    radio.cmd_radio_watch_start()
    controller = radio._change_watch_controller
    controller.tick()
    radio._video_window = None
    shots = radio.engine.shots
    controller.tick()
    assert radio.engine.shots == shots
    assert radio.said[-1] == "Stopped watching: the video is no longer showing."


def test_stop_with_nothing_watched_says_so(radio) -> None:
    (lambda w: w.cmd_radio_watch_stop())(radio)
    assert radio.said == ["Nothing was being watched."]


def test_safe_mode_refuses_the_start(radio) -> None:
    radio._safe_mode = True
    radio._video_window = SimpleNamespace()
    (lambda w: w.cmd_radio_watch_start())(radio)
    assert radio.said == ["AI is off in Safe Mode."]
    assert radio.engine.shots == 0


def test_declining_the_picture_consent_starts_nothing(radio) -> None:
    radio.box_answer = wx.NO
    radio._video_window = SimpleNamespace()
    (lambda w: w.cmd_radio_watch_start())(radio)
    assert not radio._change_watch_controller.watching
    assert radio._radio_history.ai_picture_consent == []
