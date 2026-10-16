"""The screen reader's read-back, heard by the open microphone, is not written again."""

from __future__ import annotations

from quill.core.windows_dictation.echo_guard import ECHO_START_S, ECHO_WINDOW_S, EchoGuard


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _guard(*written: str) -> tuple[EchoGuard, _Clock]:
    clock = _Clock()
    guard = EchoGuard(clock)
    for text in written:
        guard.wrote(text)
    return guard, clock


def test_the_read_back_of_a_phrase_is_an_echo() -> None:
    guard, _ = _guard("Please send the report by Friday.")
    assert guard.is_echo("please send the report by friday")
    # A reader with punctuation on says the marks; the recogniser hears them.
    assert guard.is_echo("please send the report by friday period")
    # A reader that only caught the end of it is still an echo.
    assert guard.is_echo("the report by friday")


def test_new_words_are_not_an_echo() -> None:
    guard, _ = _guard("Please send the report by Friday.")
    assert not guard.is_echo("and copy Maria on it")
    assert not guard.is_echo("send it to Maria instead of Friday")


def test_one_word_is_an_echo_only_when_it_was_a_whole_phrase() -> None:
    guard, _ = _guard("Thanks.", "See you on the weekend.")
    assert guard.is_echo("thanks")
    assert not guard.is_echo("the")  # a word said again on purpose


def test_the_echo_window_closes() -> None:
    guard, clock = _guard("Please send the report by Friday.")
    clock.now += ECHO_WINDOW_S + 0.1
    assert not guard.is_echo("please send the report by friday")


def test_an_echo_begins_as_the_text_goes_in() -> None:
    guard, clock = _guard("Please send the report by Friday.")
    written = clock.now
    clock.now += 2.5
    assert guard.is_echo("please send the report by friday", started=written + 0.4)


def test_the_same_words_said_again_later_are_written() -> None:
    """Reported 2026-10-12: a phrase said twice on purpose was not dictated."""
    guard, clock = _guard("Please send the report by Friday.")
    written = clock.now
    clock.now += 4.0
    assert not guard.is_echo("please send the report by friday", started=written + 2.0)


def test_a_phrase_begun_before_the_write_is_not_its_echo() -> None:
    """Said while the last phrase was still being recognised: the person, not the reader."""
    guard, clock = _guard("Thanks.")
    assert not guard.is_echo("thanks", started=clock.now - 0.5)


def test_a_long_read_back_heard_as_two_phrases_is_dropped_whole() -> None:
    guard, clock = _guard("Please send the report by Friday and copy Maria on it.")
    written = clock.now
    clock.now += 2.0
    assert guard.is_echo("please send the report by friday", started=written + 0.3)
    first_ended = clock.now
    clock.now += 2.0
    assert guard.is_echo("and copy maria on it", started=first_ended + ECHO_START_S / 2)


def test_nothing_written_means_no_echo() -> None:
    guard, _ = _guard()
    assert not guard.is_echo("anything at all")
    assert not guard.is_echo("")


def test_the_controller_does_not_write_the_echo() -> None:
    from quill.core.windows_dictation.ports import Moment
    from tests.unit.core.test_windows_dictation import _controller, _hear

    controller, _recognizer, document, feedback = _controller()
    controller.start()
    _hear(controller, "please send the report by friday")
    written = document.text
    _hear(controller, "please send the report by friday period")
    assert document.text == written
    assert feedback.cues.count(Moment.PHRASE) == 1  # no tone, no read-back: nothing went in
    _hear(controller, "and copy Maria")
    assert document.text.startswith(written) and len(document.text) > len(written)


def test_the_controller_writes_a_phrase_said_again_after_a_pause() -> None:
    from tests.unit.core.test_windows_dictation import _controller, _hear

    clock = _Clock()
    controller, _recognizer, document, _feedback = _controller()
    controller._clock = clock
    controller._echo = EchoGuard(clock)
    controller.start()
    controller.on_speech_started()
    _hear(controller, "thank you")
    once = document.text
    clock.now += 3.0
    controller.on_speech_started()
    clock.now += 1.0
    _hear(controller, "thank you")
    assert document.text.lower().count("thank you") == 2, (once, document.text)


def test_with_the_reader_captured_the_same_words_are_always_written(monkeypatch) -> None:
    """The gate silences JAWS, NVDA or Narrator before a built-in model hears
    it, so nothing it says can come back: the same phrase again is meant."""
    from quill.core.windows_dictation.reader_gate import ReaderGate
    from tests.unit.core.test_windows_dictation import _controller, _hear

    clock = _Clock()
    gate = ReaderGate(clock)
    gate.readers.add("nvda.exe")
    monkeypatch.setattr("quill.core.windows_dictation.microphone_owner.started_gate", lambda: gate)
    controller, recognizer, document, _feedback = _controller()
    recognizer.hears_reader = False  # a built-in model: its audio is gated
    controller._clock = clock
    controller._echo = EchoGuard(clock)
    controller.start()
    for _ in range(2):
        controller.on_speech_started()
        clock.now += 0.5
        _hear(controller, "thank you")
    assert document.text.lower().count("thank you") == 2, document.text
    # An engine that hears the microphone itself still has the echo guard.
    recognizer.hears_reader = True
    controller.on_speech_started()
    clock.now += 0.5
    _hear(controller, "thank you")
    assert document.text.lower().count("thank you") == 2, document.text


def test_the_reader_is_hushed_only_when_phrases_are_not_spoken() -> None:
    """With the read-back on, what the reader says is wanted, marks and all."""
    from types import SimpleNamespace

    from quill.ui.windows_dictation_external import ExternalDocument, hush_unless_spoken

    for feedback, hushed in (("sound", True), ("silent", True), ("speech", False), ("both", False)):
        prefs = SimpleNamespace(phrase_feedback=feedback, continuous=False)
        assert hush_unless_spoken(lambda prefs=prefs: prefs)() is hushed, feedback
        typed: list[tuple[str, bool]] = []
        document = ExternalDocument(
            problem=lambda: "",
            where=lambda: "here",
            type_text=lambda text, hush=False, typed=typed: typed.append((text, hush)) or True,
            hush=hush_unless_spoken(lambda prefs=prefs: prefs),
        )
        document.insert("Hello.")
        assert typed == [("Hello.", hushed)], feedback
