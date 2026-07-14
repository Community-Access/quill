"""Braille code auto-detection: pure scoring/picking, plus one real
round-trip through the pack's lou_translate CLI when the pack is present
(it is checked into the repo, so CI exercises the full path)."""

from __future__ import annotations

import pytest

from quill.core.braille_detect import (
    CANDIDATE_TABLES,
    build_sample,
    pick_best,
    rank_candidates,
    score_backtranslation,
)

ENGLISH = (
    "The quick brown fox jumps over the lazy dog and then it runs away. "
    "We want to know that this works well for all of the people who need it."
)
GARBAGE = "q~x zz@#k lmnop yyz !!$ qqq wxyz kj zx cv bnm ,,;; ::"


def test_english_scores_much_higher_than_garbage():
    assert score_backtranslation(ENGLISH) > 0.5
    assert score_backtranslation(GARBAGE) < 0.25
    assert score_backtranslation(ENGLISH) > score_backtranslation(GARBAGE) * 2


def test_empty_and_blank_score_zero():
    assert score_backtranslation("") == 0.0
    assert score_backtranslation("   \n\n  ") == 0.0
    assert score_backtranslation("!!! ??? ...") == 0.0


def test_build_sample_skips_title_lines_in_long_files():
    lines = [f"TITLE LINE {i}" for i in range(4)] + [f"body text line {i}" for i in range(20)]
    sample = build_sample("\n".join(lines))
    assert sample.startswith("body text line 0")


def test_build_sample_keeps_everything_in_short_files():
    sample = build_sample("one line\ntwo line")
    assert sample == "one line\ntwo line"


def test_build_sample_empty_document():
    assert build_sample("") == ""
    assert build_sample("\n\n\n") == ""


def test_rank_candidates_orders_by_score():
    ranking = rank_candidates({"en-ueb-g2": ENGLISH, "en-us-comp8": GARBAGE})
    assert [table for table, _, _ in ranking] == ["en-ueb-g2", "en-us-comp8"]
    assert ranking[0][2] > ranking[1][2]


def test_pick_best_prefers_uncontracted_when_outputs_identical():
    # A Grade 1 file back-translates to the same text through both tables --
    # the honest label is "uncontracted".
    table, label, _score, _ranking = pick_best({"en-ueb-g2": ENGLISH, "en-ueb-g1": ENGLISH})
    assert table == "en-ueb-g1"
    assert "uncontracted" in label.lower()


def test_pick_best_keeps_contracted_when_outputs_differ():
    slightly_off = ENGLISH.replace("the", "th")
    table, _label, _score, _ranking = pick_best({"en-ueb-g2": ENGLISH, "en-ueb-g1": slightly_off})
    assert table == "en-ueb-g2"


def test_pick_best_empty_results():
    table, label, score, ranking = pick_best({})
    assert table == "" and label == "" and score == 0.0 and ranking == []


def _pack_available() -> bool:
    from quill.core.braille_pack import find_lou_translate, tables_dir

    return find_lou_translate() is not None and tables_dir() is not None


@pytest.mark.skipif(not _pack_available(), reason="braille pack (lou_translate) not available")
def test_real_round_trip_detects_ueb_grade_2():
    from quill.core import braille_worker_client as worker
    from quill.core.braille_detect import detect_braille_table

    brf = worker.forward_translate(ENGLISH * 4, table="en-ueb-g2")
    assert brf.strip()
    detection = detect_braille_table(brf)
    assert detection.table == "en-ueb-g2"
    assert detection.score > 0.4
    assert len(detection.ranking) == len(CANDIDATE_TABLES)


@pytest.mark.skipif(not _pack_available(), reason="braille pack (lou_translate) not available")
def test_real_round_trip_detects_uncontracted_as_grade_1():
    from quill.core import braille_worker_client as worker
    from quill.core.braille_detect import detect_braille_table

    brf = worker.forward_translate(ENGLISH * 4, table="en-ueb-g1")
    detection = detect_braille_table(brf)
    assert detection.table == "en-ueb-g1"
