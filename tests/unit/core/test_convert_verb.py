"""FUX-02: Explorer's Convert with Quill is never a silent exit."""

from __future__ import annotations

from quill.core import convert_verb


def test_a_missing_converter_is_said_with_the_file_name() -> None:
    told: list[str] = []
    started = convert_verb.hand_to_converter(
        [r"C:\Music\talk.wav"], launch=lambda *_a, **_k: False, tell=told.append
    )
    assert started is False
    assert told == [
        "Quill Converter is not installed with this copy of QUILL, so talk.wav was not converted."
    ]


def test_several_files_are_counted() -> None:
    assert "so 3 files were not converted" in convert_verb.missing_sentence(["a", "b", "c"])


def test_a_started_converter_says_nothing_and_gets_the_files() -> None:
    told: list[str] = []
    launched: list[tuple[str, tuple[str, ...]]] = []
    started = convert_verb.hand_to_converter(
        ["a.wav", "b.wav"],
        launch=lambda key, *, extra_args: launched.append((key, extra_args)) or True,
        tell=told.append,
    )
    assert started is True and told == []
    assert launched == [("converter", ("a.wav", "b.wav"))]
