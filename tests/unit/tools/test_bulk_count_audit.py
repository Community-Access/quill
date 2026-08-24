"""GATE-BULK-COUNT: a verb that touches many rows says how many (11.4).

"Removed downloads" is the sentence this rule exists to prevent: it tells a
listener who cannot see the list neither how many files went nor whether the
ones it could not touch were mentioned. Download All was made to count on
2026-08-24; this gate keeps the other thirty-six honest.
"""

from __future__ import annotations

from quill.core.counted import Counted, plural
from quill.tools import bulk_count_audit


def test_every_bulk_action_counts_or_is_a_reviewed_exception() -> None:
    sites = bulk_count_audit.scan()
    committed = bulk_count_audit.load_snapshot()
    live = bulk_count_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Bulk-action sites changed. Run "
        "'python -m quill.tools.bulk_count_audit --write', then make each new "
        "verb end by saying eligible / done / skipped (or classify it "
        "deliberately)."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], "These verbs act on many rows and announce no count: " + ", ".join(
        missing
    )
    assert set(committed.values()) <= bulk_count_audit.STATUSES


def test_a_bulk_name_is_a_word_not_a_substring() -> None:
    """ "install" and "allowed" contain "all"; neither is a bulk verb."""
    assert bulk_count_audit._is_bulk_name("mark_all_played")
    assert bulk_count_audit._is_bulk_name("_on_bulk_queue")
    assert bulk_count_audit._is_bulk_name("download_all")
    assert not bulk_count_audit._is_bulk_name("_install_youtube_support")
    assert not bulk_count_audit._is_bulk_name("_youtube_allowed")
    assert not bulk_count_audit._is_bulk_name("_selected_show")


def test_the_detector_believes_the_tallying_idiom_this_family_writes() -> None:
    import ast

    counted = ast.parse(
        "def f(self):\n"
        "    changed = 0\n"
        "    for row in rows:\n"
        "        changed += 1\n"
        '    self._announce(f"Marked {changed} episode(s)")\n'
    ).body[0]
    silent = ast.parse('def f(self):\n    self._announce("Marked them as played")\n').body[0]
    assert bulk_count_audit._announces_a_count(counted)
    assert not bulk_count_audit._announces_a_count(silent)


# -- the shared vocabulary -------------------------------------------------------


def test_every_clause_of_a_counted_sentence_carries_a_number() -> None:
    tally = Counted(done=12, skipped=3, skipped_because="already downloaded")
    assert tally.sentence("Downloaded", "The Daily", noun="episode") == (
        "Downloaded for The Daily: 15 episodes eligible, 12 done, 3 skipped, already downloaded."
    )


def test_nothing_eligible_says_why_rather_than_announcing_a_zero() -> None:
    tally = Counted(nothing_because="it has no episodes yet")
    assert tally.sentence("Download", "The Daily") == (
        "Nothing to download for The Daily: it has no episodes yet."
    )


def test_everything_skipped_is_its_own_answer() -> None:
    tally = Counted(skipped=40, skipped_because="all are already here")
    assert tally.sentence("Download", "The Daily", noun="episode") == (
        "Nothing to download for The Daily: all 40 episodes were skipped -- all are already here."
    )


def test_failures_are_never_folded_into_skipped() -> None:
    tally = Counted(done=2, skipped=1, failed=3, skipped_because="marked Keep This Episode")
    sentence = tally.sentence("Removed", noun="file")
    assert "3 failed" in sentence
    assert "1 skipped, marked Keep This Episode" in sentence
    assert sentence.startswith("Removed: 6 files eligible, 2 done")


def test_eligible_can_be_larger_than_what_was_considered() -> None:
    """A capped batch considered more rows than it acted on."""
    tally = Counted(done=50, _eligible=800)
    assert tally.sentence("Downloaded", noun="episode").startswith(
        "Downloaded: 800 episodes eligible, 50 done"
    )


def test_plural_agrees() -> None:
    assert plural(1, "episode") == "1 episode"
    assert plural(0, "episode") == "0 episodes"
    assert plural(2, "entry", "entries") == "2 entries"
