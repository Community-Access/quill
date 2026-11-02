"""The shared Tell-me-when-this-changes controller (codex.md decision 25).

A fake clock, picture source, OCR and AI service, an inline worker and an
inline CallAfter: the rules of quill.core.ai.change_watch, driven the way the
window drives them, with nothing grabbed from a screen and nothing sent.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from quill.ui import change_watch_controller as cwc


def _png(colour: str, size: tuple[int, int] = (40, 30)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, colour).save(out, format="PNG")
    return out.getvalue()


RED, BLUE, GREEN = _png("red"), _png("blue"), _png("green")


def _inline_submit(name, work, *, on_success=None, on_failure=None):
    try:
        result = work()
    except Exception as error:  # noqa: BLE001 - delivered like the real one
        on_failure(name, error)
        return
    on_success(name, result)


class _Service:
    def __init__(self) -> None:
        self.connection_in_use = "chatgpt"
        self.answer = "A dialog opened."
        self.error = ""
        self.sent: list[tuple[str, str, tuple]] = []
        self.sizes: list[tuple[int, int]] = []

    def describe_image(self, path, question, *, on_done, on_error, requires):
        with Image.open(path) as picture:
            self.sizes.append(picture.size)
        self.sent.append((str(path), question, requires))
        if self.error:
            on_error(self.error)
        else:
            on_done(self.answer)


class _Host:
    """The app frame, as the controller sees it; no wx window."""

    def __init__(self) -> None:
        self.said: list[str] = []
        self.service = _Service()
        self._safe_mode = False
        self.capable = True
        self.ready = True
        self.consent = True
        self.consent_asked: list[str] = []
        self.frame = None

    def _announce(self, message, **_kw):
        self.said.append(str(message))

    def _ai_service(self):
        return self.service

    def _ai_switched_on(self):
        if self._safe_mode:
            self._announce("AI is off in Safe Mode.")
            return False
        return True

    def _ai_capable(self, capability):
        assert capability == "pictures"
        return self.capable

    def _ai_ready(self):
        return self.ready


class _Rig:
    def __init__(self) -> None:
        self.now = 0.0
        self.picture = RED
        self.words = ""
        self.grabs = 0

    def grab(self) -> bytes:
        self.grabs += 1
        return self.picture

    def ocr(self, _data: bytes) -> str:
        return self.words


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch):
    host = _Host()
    state = _Rig()

    def consent(h, connection):
        h.consent_asked.append(connection)
        return h.consent

    monkeypatch.setattr("quill.ui.hosted_ai_picture_consent.ask_picture_consent", consent)
    monkeypatch.setattr(cwc.ChangeWatchController, "_start_timer", lambda self: None)
    controller = cwc.ChangeWatchController(
        host,
        submit=_inline_submit,
        call_after=lambda fn, *a: fn(*a),
        clock=lambda: state.now,
        ocr=state.ocr,
    )
    return SimpleNamespace(host=host, state=state, controller=controller)


def _start(rig, **kw) -> bool:
    return rig.controller.request_start(subject="the screen", grab=rig.state.grab, **kw)


def test_start_and_stop_are_each_said_once(rig) -> None:
    assert _start(rig) is True
    assert rig.host.said == ["Watching the screen for changes."]
    assert rig.host.consent_asked == ["chatgpt"]
    rig.controller.stop()
    assert rig.host.said[-1] == "Stopped watching the screen."
    assert not rig.controller.watching


def test_starting_twice_and_stopping_nothing_each_say_so(rig) -> None:
    rig.controller.stop()
    assert rig.host.said == ["Nothing was being watched."]
    _start(rig, stop_key="Ctrl+Shift+F9")
    assert _start(rig, stop_key="Ctrl+Shift+F9") is False
    assert rig.host.said[-1] == "Already watching the screen. Ctrl+Shift+F9 stops it."
    assert rig.host.consent_asked == ["chatgpt"]  # not asked again for a refused start


def test_safe_mode_refuses_with_a_sentence_and_grabs_nothing(rig) -> None:
    rig.host._safe_mode = True
    assert _start(rig) is False
    assert rig.host.said == ["AI is off in Safe Mode."]
    assert rig.host.consent_asked == [] and rig.state.grabs == 0


def test_the_core_refuses_safe_mode_even_when_the_app_gate_is_passed(rig) -> None:
    rig.host._safe_mode = True
    started = rig.controller.begin(subject="the screen", grab=rig.state.grab, connection="x")
    assert started is False
    assert rig.host.said == ["Watching for changes is off in Safe Mode."]


def test_declining_the_picture_consent_refuses_the_start(rig) -> None:
    rig.host.consent = False
    assert _start(rig) is False
    assert not rig.controller.watching
    assert rig.host.said == ["Nothing is being watched: pictures were not agreed for this AI."]
    rig.controller.tick()
    assert rig.state.grabs == 0


def test_a_connection_that_cannot_see_starts_nothing(rig) -> None:
    rig.host.capable = False
    assert _start(rig) is False
    assert rig.host.consent_asked == [] and not rig.controller.watching


def test_a_report_is_spoken_only_when_something_changed(rig) -> None:
    _start(rig)
    rig.controller.tick()  # the first look is the baseline
    rig.controller.tick()  # the same picture: nothing said
    assert rig.host.said == ["Watching the screen for changes."]
    rig.state.picture = BLUE  # changed, no words: the AI is asked once
    rig.controller.tick()
    assert rig.host.said[-1] == "A dialog opened."
    assert len(rig.host.service.sent) == 1
    _path, question, requires = rig.host.service.sent[0]
    assert requires == ("text", "pictures")
    assert "labelled Before" in question
    # One picture: before and after side by side, wider than either alone.
    assert rig.host.service.sizes[0][0] > 2 * 40
    assert rig.controller.asks_sent == 1


def test_changed_words_are_read_locally_and_nothing_is_sent(rig) -> None:
    _start(rig)
    rig.controller.tick()
    rig.state.picture, rig.state.words = BLUE, "Recording stopped"
    rig.controller.tick()
    assert rig.host.said[-1] == "The words changed to: Recording stopped"
    assert rig.host.service.sent == []


def test_a_no_change_answer_says_nothing(rig) -> None:
    rig.host.service.answer = "No change."
    _start(rig)
    rig.controller.tick()
    rig.state.picture = BLUE
    rig.controller.tick()
    assert rig.host.said == ["Watching the screen for changes."]


def test_closing_the_window_ends_it_and_nothing_more_is_grabbed(rig) -> None:
    _start(rig)
    rig.controller.tick()
    grabs = rig.state.grabs
    rig.controller.window_closed()
    rig.state.picture = BLUE
    rig.controller.tick()
    assert rig.state.grabs == grabs
    assert rig.host.service.sent == []
    assert rig.host.said == ["Watching the screen for changes."]  # silent close
    assert _start(rig) is False
    assert rig.host.said[-1] == "This window has closed, so there is nothing to watch."


def test_a_close_while_the_answer_is_on_its_way_sends_and_says_nothing(rig) -> None:
    held: list = []
    rig.controller._call_after = lambda fn, *a: held.append((fn, a))
    _start(rig)
    rig.controller.tick()  # baseline look; its delivery is held
    for fn, args in held:
        fn(*args)
    held.clear()
    rig.state.picture = BLUE
    rig.controller._ask_timeout = 0.01
    rig.controller.tick()  # the send is held on the "UI thread", then times out
    rig.controller.window_closed()
    for fn, args in held:
        fn(*args)
    assert rig.host.service.sent == []
    assert rig.host.said == ["Watching the screen for changes."]


def test_thirty_asks_then_the_watch_stops_and_says_so(rig) -> None:
    _start(rig)
    rig.controller.tick()
    colours = [BLUE, RED]
    for index in range(30):
        rig.state.now += 61
        rig.state.picture = colours[index % 2]
        rig.controller.tick()
    assert len(rig.host.service.sent) == 30
    assert not rig.controller.watching
    assert "that was 30 questions to the AI" in rig.host.said[-1]
    rig.state.now += 61
    rig.state.picture = GREEN
    rig.controller.tick()
    assert len(rig.host.service.sent) == 30


def test_at_most_one_ask_a_minute(rig) -> None:
    _start(rig)
    rig.controller.tick()
    rig.state.picture = BLUE
    rig.controller.tick()
    rig.state.picture, rig.state.now = RED, 30.0
    rig.controller.tick()
    assert len(rig.host.service.sent) == 1


def test_a_failed_ask_ends_the_watch_in_one_sentence(rig) -> None:
    rig.host.service.error = "My ChatGPT plan is busy."
    _start(rig)
    rig.controller.tick()
    rig.state.picture = BLUE
    rig.controller.tick()
    assert not rig.controller.watching
    assert rig.host.said[-1].startswith("Stopped watching: the AI could not answer")


def test_a_changed_connection_stops_the_watch_before_anything_goes(rig) -> None:
    _start(rig)
    rig.controller.tick()
    rig.host.service.connection_in_use = "own_key"
    rig.state.picture = BLUE
    rig.controller.tick()
    assert rig.host.service.sent == []
    assert rig.host.said[-1].startswith("Stopped watching: the AI in use changed")


def test_a_target_that_goes_away_ends_the_watch_with_its_sentence(rig) -> None:
    showing = {"yes": True}
    _start(rig, available=lambda: "" if showing["yes"] else "Stopped watching: gone.")
    rig.controller.tick()
    showing["yes"] = False
    grabs = rig.state.grabs
    rig.controller.tick()
    assert rig.state.grabs == grabs
    assert rig.host.said[-1] == "Stopped watching: gone."
    assert not rig.controller.watching


def test_a_refusal_is_said_and_nothing_is_asked(rig) -> None:
    assert _start(rig, refusal=lambda: "There is no picture to watch.") is False
    assert rig.host.said == ["There is no picture to watch."]
    assert rig.host.consent_asked == []


def test_a_late_result_after_stop_is_not_spoken(rig) -> None:
    held: list = []
    rig.controller._call_after = lambda fn, *a: held.append((fn, a))
    _start(rig)
    rig.controller.tick()
    rig.controller.stop()
    for fn, args in held:
        fn(*args)
    assert rig.host.said == ["Watching the screen for changes.", "Stopped watching the screen."]


def test_on_start_and_on_end_bracket_the_watch(rig) -> None:
    events: list[str] = []
    _start(rig, on_start=lambda: events.append("start"), on_end=lambda: events.append("end"))
    rig.controller.stop()
    assert events == ["start", "end"]


def test_before_after_picture_is_one_labelled_sheet() -> None:
    sheet = cwc.before_after_picture(_png("red", (200, 100)), _png("blue", (200, 100)))
    with Image.open(io.BytesIO(sheet)) as picture:
        assert picture.width > 400 and picture.height > 100
