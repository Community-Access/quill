"""Tiers 1 and 2, the argument reader, and the help list (command-key.md 5.4, 6.3, 11.1)."""

from __future__ import annotations

import pytest

from quill.core.command_catalogue import rows_for_app
from quill.core.command_catalogue.args import read_args
from quill.core.command_catalogue.help_list import count_line, help_rows, nothing_about_line
from quill.core.command_catalogue.resolver import Candidate, resolve
from quill.core.command_catalogue.words import content_words, normalize, similar, stem


def _candidates(app: str) -> list[Candidate]:
    return [Candidate(spec) for spec in rows_for_app(app) if spec.offered]


# -- words ----------------------------------------------------------------------


def test_normalize_joins_apostrophes_and_drops_punctuation() -> None:
    assert normalize("What's  playing?!") == "whats playing"
    assert normalize("It’s too LOUD") == "its too loud"


def test_filler_goes_and_synonyms_meet() -> None:
    assert content_words("could you please make it louder") == ("louder",)
    assert stem("favorites") == stem("favourite") == "favourit"
    assert stem("headings") == "heading"
    assert stem("recording") == "recording"  # not "record"
    assert stem("class") == "class"


@pytest.mark.parametrize(
    ("left", "right", "same"),
    [
        ("faster", "fastr", True),
        ("heading", "haeding", True),  # one swapped pair
        ("heading", "header", False),
        ("bookmark", "bokmark", True),
        ("mute", "mike", False),
        ("record", "rekord", True),
        ("louder", "powder", False),
        ("spelling", "spleling", True),
    ],
)
def test_one_typo_in_a_long_word(left: str, right: str, same: bool) -> None:
    assert similar(left, right) is same


# -- arguments ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "number", "seconds", "size", "remainder"),
    [
        ("play favourite 3", 3, None, "", "play favourite"),
        ("play my third favourite", 3, None, "", "play my favourite"),
        ("skip back 30 seconds", None, 30, "", "skip back"),
        ("sleep in twenty five minutes", None, 1500, "", "sleep in"),
        ("stop in an hour and a half", None, 5400, "", "stop in"),
        ("back half an hour", None, 1800, "", "back"),
        ("a lot louder", None, None, "large", "louder"),
        ("turn it down a bit", None, None, "small", "turn it down"),
        ("bookmark 2nd", 2, None, "", "bookmark"),
        ("forward 1 minute and a half", None, 90, "", "forward"),
    ],
)
def test_the_reader(
    text: str, number: int | None, seconds: int | None, size: str, remainder: str
) -> None:
    found = read_args(normalize(text))
    assert (found.number, found.seconds, found.size, found.remainder) == (
        number,
        seconds,
        size,
        remainder,
    )


def test_steps_and_as_dict() -> None:
    assert read_args("much louder").steps == 3
    assert read_args("louder").steps == 1
    assert read_args("favourite 3").as_dict() == {"number": 3}
    assert read_args("back 30 seconds a bit").as_dict() == {"seconds": 30, "size": "small"}


# -- the tiers ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("app", "text", "expect"),
    [
        ("radio", "louder", "radio.volume_up"),
        ("radio", "it's too loud", "radio.volume_down"),
        ("radio", "the radio is way too loud", "radio.volume_down"),
        ("radio", "play favourite 3", "radio.play_favorite"),
        ("radio", "favorit 2", "radio.play_favorite"),
        ("radio", "make it fastr", "radio.transport.speed_up"),
        ("radio", "what song is this", "radio.identify_song"),
        ("radio", "sleep in 20 minutes", "media.sleep_timer"),
        ("quill", "save", "file.save"),
        ("quill", "go to line 120", "navigate.go_to_line"),
        ("quill", "how many words", "tools.word_count"),
        ("quill", "make the font bigger", "format.grow_font"),
        ("lite", "save my work", "lite.cmd_save"),
        ("lite", "next heading please", "lite.cmd_next_heading"),
    ],
)
def test_confident_matches(app: str, text: str, expect: str) -> None:
    found = resolve(text, _candidates(app))
    assert found.confident and found.best is not None and found.best.id == expect


def test_press_uses_the_key_this_window_has() -> None:
    from quill.core.command_catalogue import row

    spec = row("file.save")
    assert spec is not None
    found = resolve("press control s", [Candidate(spec, "Ctrl+S")])
    assert found.confident and found.best is not None and found.best.tier == 1


def test_a_tie_is_not_confident_and_offers_both() -> None:
    found = resolve("headings", _candidates("quill"))
    assert not found.confident
    assert {item.id for item in found.close} == {
        "navigate.next_heading",
        "navigate.previous_heading",
        "navigate.outline_navigator",
    }


@pytest.mark.parametrize("text", ["flibbertigibbet", "saev", "", "!!!"])
def test_nothing_close(text: str) -> None:
    found = resolve(text, _candidates("quill"))
    assert not found.confident and not found.close


def test_an_empty_list_matches_nothing() -> None:
    assert resolve("save", []).best is None


def test_every_example_resolves_to_its_own_command() -> None:
    """Section 11.3: every example is a test, in every app, through tiers 1 and 2."""
    misses: list[str] = []
    for app in ("quill", "lite", "radio"):
        candidates = _candidates(app)
        for item in candidates:
            for example in item.spec.examples:
                found = resolve(example, candidates)
                if not (
                    found.confident and found.best is not None and found.best.id == item.spec.id
                ):
                    misses.append(f"{app}: {example!r} -> {found.best.id if found.best else None}")
    assert not misses, "\n".join(misses)


# -- the help list ----------------------------------------------------------------


def test_help_rows_group_and_count() -> None:
    rows = help_rows(_candidates("radio"))
    headings = [row for row in rows if row.is_heading]
    commands = [row for row in rows if not row.is_heading]
    assert headings and len(commands) == len(_candidates("radio"))
    assert count_line(rows).startswith(f"{len(commands)} things you can do here, in ")


def test_help_row_has_name_example_and_key() -> None:
    from quill.core.command_catalogue import row

    spec = row("radio.volume_down", "radio")
    assert spec is not None
    rows = help_rows([Candidate(spec, "Ctrl+Down")])
    assert rows[0].label == "Volume, 1"
    assert rows[1].label == "Volume Down. Say 'turn it down a bit'. Ctrl+Down."
    assert count_line(rows) == "1 thing you can do here."


def test_help_filter_and_usage_order() -> None:
    rows = help_rows(_candidates("quill"), help_filter="bookmarks")
    titles = {row.candidate.spec.title for row in rows if row.candidate is not None}
    assert titles == {"Next Bookmark", "Set Bookmark", "Clear Bookmarks"}
    assert help_rows(_candidates("quill"), help_filter="zebras") == ()
    assert nothing_about_line("zebras") == "Nothing about zebras here. Here is everything."
    used = help_rows(_candidates("radio"), usage={"radio.lyrics": 9})
    assert used[0].label.startswith("Song,") and used[1].candidate.spec.id == "radio.lyrics"  # type: ignore[union-attr]
