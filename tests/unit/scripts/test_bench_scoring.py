"""The benchmark's scoring pipeline, the LibriVox set's text work (B-1a), and
the generated command script (B-1c). Tiny synthetic text and tones only."""

from __future__ import annotations

import datetime as dt
import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _load(name: str) -> Any:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module(name)


# -- scoring ------------------------------------------------------------------- #


def test_punctuation_is_scored_only_after_words_both_texts_share() -> None:
    scoring = _load("bench_scoring")
    scores = scoring.punctuation_scores(
        "Hello, world. How are you? Fine.", "hello world. how are you. fine"
    )
    assert scores["comma"].as_dict()["missed"] == 1
    assert scores["period"].hits == 1  # after "world"
    assert scores["question"].missed == 1
    assert scores["period"].extra == 1  # "you." where a question mark was
    assert scores["comma"].recall == 0.0 and scores["comma"].precision is None


def test_f1_is_the_balance_of_precision_and_recall() -> None:
    score = _load("bench_scoring").MarkScore(hits=3, extra=1, missed=1)
    assert (score.precision, score.recall, score.f1) == (0.75, 0.75, 0.75)


def test_a_paragraph_break_is_a_mark_and_quotes_are_never_scored() -> None:
    scoring = _load("bench_scoring")
    scores = scoring.punctuation_scores(
        'He left.\n\n"Gone," she said.', "He left.\nGone, she said."
    )
    assert scores["paragraph"].hits == 1
    assert scores["comma"].hits == 1


def test_capitals_count_sentences_that_start_with_one() -> None:
    assert _load("bench_scoring").capital_rate("One. two? Three! four") == (2, 4)


def test_mostly_quoted_text_is_dialogue() -> None:
    scoring = _load("bench_scoring")
    assert scoring.is_dialogue('"I will not go there today, not ever," he said.')
    assert not scoring.is_dialogue('He said "no" and walked out of the room slowly.')


def test_the_gutenberg_prepass_joins_hyphens_and_unwraps_lines() -> None:
    text = "A long sen-\ntence that\nwraps.\n\nNext para-\ngraph."
    assert _load("bench_scoring").gutenberg_prepass(text) == (
        "A long sentence that wraps.\n\nNext paragraph."
    )


def test_spanish_is_normalized_without_accents() -> None:
    name, normal = _load("bench_scoring").normalizer("es")
    assert "accents" in name
    assert normal("¿Dónde está?") == ["donde", "esta"]


@pytest.mark.parametrize(
    ("reference", "heard", "outcome"),
    [
        ("new paragraph", "New paragraph.", "parsed"),
        ("new paragraph", "knew paragon", "typed"),
        ("new paragraph", "", "nothing"),
        ("scratch that", "new paragraph", "other command"),
        ("quill scratch that", "Quill, scratch that.", "parsed"),
        ("quill scratch that", "scratch that", "typed"),
    ],
)
def test_a_spoken_command_is_parsed_or_typed(reference: str, heard: str, outcome: str) -> None:
    assert _load("bench_scoring").command_outcome(reference, heard) == outcome


def test_model_families_group_distil_with_whisper() -> None:
    family = _load("bench_scoring").model_family
    assert family("distil_small_en") == "whisper" == family("whisper_turbo")
    assert family("moonshine_base") == "moonshine"


# -- B-1a: LibriVox and Gutenberg --------------------------------------------- #

_BOOK = """The Project Gutenberg eBook of A Small Test

*** START OF THE PROJECT GUTENBERG EBOOK A SMALL TEST ***

Produced by volunteers for Project Gutenberg.

CHAPTER ONE

The cat sat on the warm mat by the fire. It was a quiet
evening in the old house, and nobody spoke.

"Will it rain?" asked the boy. His mother looked out of the
window and said that it would.

*** END OF THE PROJECT GUTENBERG EBOOK A SMALL TEST ***
License text that must go.
"""


def test_gutenberg_text_loses_its_header_footer_and_every_mention() -> None:
    clean = _load("bench_librivox").clean_gutenberg(_BOOK)
    assert "gutenberg" not in clean.lower()
    assert "License text" not in clean
    assert "It was a quiet evening in the old house" in clean


def test_a_gutenberg_link_gives_its_ebook_number() -> None:
    number = _load("bench_librivox").gutenberg_number
    assert number("https://www.gutenberg.org/ebooks/1342") == 1342
    assert number("http://www.gutenberg.org/etext/84") == 84
    assert number("https://archive.org/details/x") is None


def test_held_out_means_catalogued_after_the_cutoff_and_unknown_is_never() -> None:
    librivox = _load("bench_librivox")
    limits = {"moonshine": dt.date(2024, 10, 21), "parakeet": None}
    assert librivox.held_out_for(dt.date(2025, 1, 1), limits) == {
        "moonshine": True,
        "parakeet": False,
    }
    assert librivox.held_out_for(dt.date(2024, 10, 21), limits)["moonshine"] is False


def _project(
    pid: int, reader: str, minutes: float, text: str = "https://www.gutenberg.org/ebooks/9"
) -> dict:
    return {
        "id": pid,
        "language": "English",
        "url_text_source": text,
        "url_zip_file": f"https://archive.org/download/p{pid}.zip",
        "date_catalog": "2025-03-01",
        "sections": [
            {"section_number": n, "playtime": minutes * 60, "readers": [{"display_name": reader}]}
            for n in range(1, 6)
        ],
    }


def test_the_selection_is_seeded_balanced_across_readers_and_gutenberg_only() -> None:
    librivox = _load("bench_librivox")
    projects = [
        _project(1, "Prolific", 4),
        _project(2, "Second", 4),
        _project(3, "Third", 4),
        _project(4, "Elsewhere", 4, text="https://example.org/book"),
    ]
    kwargs = {
        "language": "en",
        "since": dt.date(2024, 11, 1),
        "limits": {"moonshine": dt.date(2024, 10, 21)},
        "minutes_per_reader": 8,
        "total_minutes": 100,
    }
    chosen = librivox.select(projects, **kwargs)
    again = librivox.select(projects, **kwargs)
    assert [(c.project, c.section) for c in chosen] == [(c.project, c.section) for c in again]
    readers = {c.reader for c in chosen}
    assert readers == {"Prolific", "Second", "Third"}
    for reader in readers:
        assert sum(c.seconds for c in chosen if c.reader == reader) / 60 <= 8
    assert all(c.held_out == {"moonshine": True} for c in chosen)


def test_librivox_boilerplate_is_found_by_its_words() -> None:
    librivox = _load("bench_librivox")
    assert librivox.is_boilerplate("This is a LibriVox recording. All LibriVox recordings")
    assert librivox.is_boilerplate("End of chapter one.")
    assert not librivox.is_boilerplate("The cat sat on the warm mat.")


def test_utterances_take_the_books_words_and_reject_poor_matches() -> None:
    librivox = _load("bench_librivox")
    book = librivox.clean_gutenberg(_BOOK)
    stretches = [
        librivox.Stretch(0.0, 3.0, "this is a librivox recording"),
        librivox.Stretch(3.5, 7.0, "the cat sat on the warm mat by the fire"),
        librivox.Stretch(7.5, 12.0, "it was a quiet evening in the old house and nobody spoke"),
        librivox.Stretch(12.5, 18.5, "purple engines dance loudly under bright cold moons"),
        librivox.Stretch(19.0, 26.0, "his mother looked out of the window and said that it would"),
        librivox.Stretch(26.5, 28.0, "end of chapter one"),
    ]
    found = librivox.utterances(stretches, book)
    kept = [u for u in found if u.kept]
    assert kept, found
    first = kept[0]
    assert first.reference.startswith("The cat sat on the warm mat by the fire.")
    assert 5 <= first.end - first.start <= 20
    assert all("librivox" not in u.heard for u in found)
    assert any(not u.kept for u in found)
    report = librivox.keep_report(("9", "Reader", u) for u in found)
    assert report["by_reader"]["Reader"]["kept"] == len(kept)


# -- B-1c: the command script ---------------------------------------------------- #


def test_the_command_script_covers_commands_the_word_inserts_and_punctuation() -> None:
    commands = _load("bench_commands")
    lines = commands.script("en")
    spoken = {line.spoken for line in lines}
    assert {"new paragraph", "scratch that", "quill scratch that"} <= spoken
    assert "insert snippet sign off" in spoken
    sentences = [line for line in lines if line.kind == "sentence"]
    assert any(line.reference == "Send the report today, please." for line in sentences)
    assert all(line.reference.startswith("!") for line in lines if line.kind != "sentence")
    assert len({line.name for line in lines}) == len(lines)


def test_the_spanish_script_has_spanish_punctuation_words() -> None:
    lines = _load("bench_commands").script("es")
    assert any("¿" in line.reference for line in lines if line.kind == "sentence")
    assert any(line.kind == "command" for line in lines)


def test_mixing_sets_the_noise_level_asked_for() -> None:
    np = pytest.importorskip("numpy")
    commands = _load("bench_commands")
    speech = np.sin(np.arange(16_000) * 0.05).astype("float32") * 0.5
    noise = np.random.default_rng(1).standard_normal(4_000).astype("float32") * 0.1
    mixed = commands.mix(speech, noise, 10.0)
    added = mixed - speech
    ratio = 10 * np.log10(np.mean(speech**2) / np.mean(added**2))
    assert abs(ratio - 10.0) < 0.1


def test_a_mixed_folder_names_each_condition_as_a_group(tmp_path: Path) -> None:
    np = pytest.importorskip("numpy")
    commands = _load("bench_commands")
    source, beds, out = tmp_path / "clean", tmp_path / "beds", tmp_path / "mixed"
    commands.write_wav(source / "a.wav", np.zeros(1_600) + 0.1)
    (source / "transcripts.txt").write_text("a.wav\t!new paragraph\n", encoding="utf-8")
    commands.write_wav(beds / "hum.wav", np.ones(800) * 0.01)
    count = commands.mix_folder(source, out, [beds / "hum.wav"], [10, 0], "noise")
    assert count == 2
    speakers = (out / "speakers.tsv").read_text(encoding="utf-8")
    assert "noise 10 dB" in speakers and "noise 0 dB" in speakers
    assert "!new paragraph" in (out / "transcripts.txt").read_text(encoding="utf-8")
