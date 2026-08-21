"""A row that will not play says so, and every other row stays quiet.

Radio Browser runs its own checker against every stream it lists and publishes
the verdict as ``lastcheckok``. Quill Radio downloaded that on every search and
discarded it, so every row made the same silent promise and the only way to
find the dead ones was to press Enter on each in turn.

The trap these guard is over-reach. It would be easy to score rows by bitrate,
votes and codec and call the result confidence; that would be a guess wearing
the clothes of a measurement. The only negative verdict here is the listing
directory's own, and the absence of a check is never read as bad news.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.radio import station_confidence as confidence


def _station(**kwargs: object) -> SimpleNamespace:
    base: dict[str, object] = {"last_check_ok": None, "source": ""}
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_a_failed_directory_check_is_the_one_thing_worth_a_badge() -> None:
    verdict = confidence.assess(_station(last_check_ok=False))
    assert verdict.verdict == confidence.FAILED
    assert verdict.badge == "may not be playable"


def test_a_passing_check_says_nothing_in_the_row() -> None:
    # Good news on every row is a longer list, not a more useful one.
    verdict = confidence.assess(_station(last_check_ok=True))
    assert verdict.verdict == confidence.WORKING
    assert verdict.badge == ""
    # ...but the details panel, which has room, still says it.
    assert "played this stream successfully" in verdict.explanation


def test_no_published_check_is_not_bad_news() -> None:
    # THE CASE THAT KEEPS THIS HONEST: every directory but Radio Browser lands
    # here, and marking them all "unknown" would badge nearly every row in the
    # app to convey nothing.
    verdict = confidence.assess(_station(last_check_ok=None, source="SomaFM"))
    assert verdict.verdict == confidence.UNKNOWN
    assert verdict.badge == ""
    assert "No directory has published a check" in verdict.explanation


def test_rows_that_resolve_at_play_time_say_so() -> None:
    for source in ("TuneIn", "YouTube"):
        verdict = confidence.assess(_station(source=source))
        assert verdict.verdict == confidence.NEEDS_LOOKUP
        assert verdict.badge == "resolved when you play it"


def test_a_failed_check_outranks_needing_a_lookup() -> None:
    # A row has space for one badge, and "this will probably not play" is worth
    # more than "this takes a moment to start".
    verdict = confidence.assess(_station(last_check_ok=False, source="TuneIn"))
    assert verdict.verdict == confidence.FAILED


def test_the_badge_goes_last_so_the_name_still_leads_the_row() -> None:
    label = confidence.label_with_confidence("WQXR (United States)", _station(last_check_ok=False))
    assert label.startswith("WQXR (United States)")
    assert label.endswith("may not be playable")


def test_a_quiet_row_is_returned_untouched() -> None:
    # Not "returned with an empty suffix" -- untouched, so no trailing
    # punctuation appears on the overwhelming majority of rows.
    assert confidence.label_with_confidence("WQXR", _station(last_check_ok=True)) == "WQXR"
    assert confidence.label_with_confidence("WQXR", _station()) == "WQXR"


def test_an_object_without_the_field_at_all_is_simply_unknown() -> None:
    # Favorites saved before the field existed, and any duck-typed stand-in.
    assert confidence.assess(SimpleNamespace()).verdict == confidence.UNKNOWN
    assert confidence.label_with_confidence("Old Favorite", SimpleNamespace()) == "Old Favorite"
