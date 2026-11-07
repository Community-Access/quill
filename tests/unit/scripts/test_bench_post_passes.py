"""The pure parts of the D-27 to D-30 measurement script, and the LibriVox
tooling's 2026-10-17 additions. Tiny synthetic inputs; no model, no audio,
no network."""

from __future__ import annotations

import datetime as dt
import importlib
import struct
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _load(name: str) -> Any:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module(name)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _piece(text: str, score: float, kind: int = 1) -> bytes:
    raw = text.encode("utf-8")
    body = b"\x0a" + _varint(len(raw)) + raw + b"\x15" + struct.pack("<f", score)
    body += b"\x18" + _varint(kind)
    return b"\x0a" + _varint(len(body)) + body


def _model(pieces: list[tuple[str, float, int]]) -> bytes:
    # A trainer spec (field 2) the reader must skip, then the pieces.
    return b"\x12\x02\x08\x01" + b"".join(_piece(*p) for p in pieces)


_PIECES = [
    ("<unk>", 0.0, 2),
    ("▁QUILL", -3.0, 1),
    ("▁QU", -2.0, 1),
    ("ILL", -2.5, 1),
    ("▁HEY", -1.0, 1),
    ("▁", -4.0, 1),
    ("Q", -6.0, 1),
    ("U", -6.0, 1),
    ("I", -6.0, 1),
    ("L", -6.0, 1),
]


def test_a_sentencepiece_model_is_read_without_the_package() -> None:
    passes = _load("bench_post_passes")
    found = passes.sentencepiece_vocab(_model(_PIECES))
    assert [p for p, _s, _k in found] == [p for p, _s, _k in _PIECES]
    assert found[1][1] == -3.0 and found[0][2] == 2


def test_bpe_vocab_is_one_piece_and_score_a_line(tmp_path: Path) -> None:
    passes = _load("bench_post_passes")
    path = passes.write_bpe_vocab([("▁A", -1.5, 1), ("B", -2.0, 1)], tmp_path / "bpe.vocab")
    assert path.read_text(encoding="utf-8") == "▁A\t-1.5\nB\t-2\n"


def test_encoding_takes_the_highest_scoring_split() -> None:
    passes = _load("bench_post_passes")
    pieces = passes.sentencepiece_vocab(_model(_PIECES))
    assert passes.encode("QUILL", pieces) == ["▁QUILL"]  # -3 beats -2 + -2.5
    assert passes.encode("HEY QUILL", pieces) == ["▁HEY", "▁QUILL"]


def test_keyword_lines_carry_the_command_word_and_hey(tmp_path: Path) -> None:
    passes = _load("bench_post_passes")
    pieces = passes.sentencepiece_vocab(_model(_PIECES))
    path = passes.keyword_file(["quill"], pieces, tmp_path / "k.txt", boost=1.0, threshold=0.25)
    assert path.read_text(encoding="utf-8").splitlines() == [
        "▁QUILL :1 #0.25 @QUILL",
        "▁HEY ▁QUILL :1 #0.25 @HEY_QUILL",
    ]


def test_a_name_counts_only_when_every_word_is_heard() -> None:
    passes = _load("bench_post_passes")
    assert passes.name_recognised("Siobhan Okonkwo", "send it to siobhan okonkwo today")
    assert not passes.name_recognised("Siobhan Okonkwo", "send it to shivon okonkwo today")


def test_stripping_marks_leaves_the_words_lower_case() -> None:
    passes = _load("bench_post_passes")
    assert passes.strip_marks("Well, Mr. Brown -- go!") == "well mr brown go"


def test_conversations_alternate_speakers_and_are_seeded() -> None:
    passes = _load("bench_post_passes")
    table = {s: [f"{s}-{n}.wav" for n in range(6)] for s in ("a", "b", "c", "d")}
    first = passes.conversations(table, count=3, voices=2, turns=6, seed=2)
    assert first == passes.conversations(table, count=3, voices=2, turns=6, seed=2)
    for talk in first:
        assert len({speaker for speaker, _f in talk}) == 2
        assert all(x[0] != y[0] for x, y in zip(talk, talk[1:], strict=False))


def test_speaker_accuracy_uses_the_best_one_to_one_mapping() -> None:
    passes = _load("bench_post_passes")
    truth = ["a", "a", "b", "b", "c"]
    assert passes.best_mapping_accuracy(truth, ["S2", "S2", "S1", "S1", "S3"]) == 1.0
    assert passes.best_mapping_accuracy(truth, ["S1", "S1", "S1", "S1", "S1"]) == 0.4
    assert passes.best_mapping_accuracy(truth, ["", "", "", "", ""]) == 0.0


def test_the_catalogue_date_comes_from_the_archive_identifier() -> None:
    librivox = _load("bench_librivox")
    since = dt.date(2024, 10, 21)
    project = {"url_iarchive": "https://archive.org/details/somepsalms_2412_librivox"}
    assert librivox.catalogue_date(project, since) == dt.date(2024, 12, 1)
    assert librivox.catalogue_date({"date_catalog": "2025-02-03"}, since) == dt.date(2025, 2, 3)
    assert librivox.catalogue_date({"url_iarchive": "nothing"}, since) == since
    assert librivox.catalogue_date({"url_zip_file": "x_2413_librivox.zip"}, since) == since


def test_a_long_section_counts_only_as_much_as_is_used() -> None:
    librivox = _load("bench_librivox")
    projects = [
        {
            "id": pid,
            "language": "English",
            "url_text_source": f"https://www.gutenberg.org/ebooks/{pid}",
            "url_iarchive": f"https://archive.org/details/book{pid}_2503_librivox",
            "sections": [
                {"section_number": 1, "playtime": 40 * 60, "readers": [{"display_name": r}]}
            ],
        }
        for pid, r in ((1, "A"), (2, "B"), (3, "C"))
    ]
    kwargs = {"language": "en", "since": dt.date(2024, 11, 1), "limits": {}}
    assert len(librivox.select(projects, total_minutes=45, **kwargs)) == 1
    assert len(librivox.select(projects, total_minutes=45, max_section_minutes=6, **kwargs)) == 3


def test_a_fetched_section_has_a_stable_file_name() -> None:
    librivox = _load("bench_librivox")
    assert librivox.section_audio_name({"project": 21201, "section": "50"}) == "lv21201-050.mp3"


def test_the_committed_b1a_selections_load_by_set(tmp_path: Path) -> None:
    librivox = _load("bench_librivox")
    committed = _SCRIPTS / "bench_librivox_sets.json"
    english = librivox.load_selection(committed, "librivox-heldout-en")
    spanish = librivox.load_selection(committed, "librivox-heldout-es")
    assert len(english) == 17 and len(spanish) == 13
    assert all(s["listen_url"].startswith("https://") for s in english + spanish)
    plain = tmp_path / "selection.json"
    plain.write_text('[{"project": 1}]', encoding="utf-8")
    assert librivox.load_selection(plain) == [{"project": 1}]
