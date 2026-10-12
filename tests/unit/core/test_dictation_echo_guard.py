"""The screen reader's read-back, heard by the open microphone, is not written again."""

from __future__ import annotations

from quill.core.windows_dictation.echo_guard import ECHO_WINDOW_S, EchoGuard


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
