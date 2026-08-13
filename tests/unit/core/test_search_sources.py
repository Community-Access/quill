"""Tests for choosing which directories Find Stations searches.

The reason this exists: one search fans out across eight places, which is what
you want when hunting a station and noise when you already know what you want.
So each source can be switched off -- and, critically, a source that is off is
never *contacted*, so the toggles govern network traffic and not just display.
"""

import pytest

from quill.core.radio import search_sources as ss
from quill.core.radio.spotify_search import youtube_search_stations


def test_the_registry_has_no_duplicate_ids_or_labels() -> None:
    ids = [s.id for s in ss.SEARCH_SOURCES]
    labels = [s.label for s in ss.SEARCH_SOURCES]
    assert len(ids) == len(set(ids))
    assert len(labels) == len(set(labels))


def test_everything_is_on_out_of_the_box() -> None:
    assert set(ss.DEFAULT_ENABLED) == set(ss.SOURCE_IDS)


def test_an_unset_selection_means_the_defaults() -> None:
    """Missing/unusable settings mean "not configured yet", not "all off"."""
    for missing in (None, "mono", b"x", 17):
        assert ss.normalize(missing) == ss.DEFAULT_ENABLED


def test_an_explicitly_empty_selection_is_preserved() -> None:
    """Turning everything off is a real choice; re-enabling it would be a bug."""
    assert ss.normalize([]) == ()
    assert ss.describe_selection([]).startswith("No search sources")


def test_unknown_ids_are_dropped_not_kept() -> None:
    """A source removed in a later build must not linger in a stored list."""
    assert ss.normalize(["youtube", "gopher_radio"]) == ("youtube",)


def test_selection_is_returned_in_registry_order() -> None:
    """Order comes from the registry, never from how it was stored."""
    assert ss.normalize(["youtube", "tunein"]) == ("tunein", "youtube")


def test_an_unknown_source_still_searches() -> None:
    """A source this build knows but the stored selection predates must not
    silently vanish."""
    assert ss.is_enabled(["tunein"], "a_source_added_later") is True
    assert ss.is_enabled(["tunein"], "youtube") is False
    assert ss.is_enabled(["tunein"], "tunein") is True


def test_toggling_flips_one_source_and_leaves_the_rest() -> None:
    after = ss.toggle(ss.DEFAULT_ENABLED, "youtube")
    assert "youtube" not in after
    assert "tunein" in after
    assert "youtube" in ss.toggle(after, "youtube")


def test_toggling_an_unknown_source_changes_nothing() -> None:
    assert ss.toggle(["tunein"], "nope") == ("tunein",)


def test_the_summary_names_sources_rather_than_counting_them() -> None:
    """ "3 sources" does not answer "am I searching Spotify?"."""
    summary = ss.describe_selection(["tunein", "youtube"])
    assert "TuneIn" in summary
    assert "YouTube" in summary


def test_the_summary_stays_short_when_everything_is_on() -> None:
    assert ss.describe_selection(ss.DEFAULT_ENABLED) == "Searching all sources."


# -- YouTube rows ------------------------------------------------------------


class _Entry:
    def __init__(self, url: str, title: str, uploader: str = "") -> None:
        self.page_url = url
        self.title = title
        self.uploader = uploader
        self.duration_ms = 0


def test_a_youtube_row_stores_the_page_url_not_a_stream() -> None:
    """A YouTube media URL dies within hours; the page link is durable, which
    is why a saved YouTube station re-resolves on every play."""
    rows = youtube_search_stations(
        "x", search=lambda q, limit=8: [_Entry("https://youtu.be/abc", "A talk", "Someone")]
    )
    assert rows[0].stream_url == "https://youtu.be/abc"
    assert rows[0].source == "YouTube"
    assert rows[0].name == "A talk - Someone"


def test_rows_with_nothing_playable_are_dropped() -> None:
    rows = youtube_search_stations(
        "x", search=lambda q, limit=8: [_Entry("", "No link"), _Entry("https://y/1", "  ")]
    )
    assert rows == []


def test_a_failing_youtube_search_never_blanks_the_other_sources() -> None:
    def _boom(query: str, limit: int = 8) -> list[_Entry]:
        raise RuntimeError("yt-dlp is stale")

    assert youtube_search_stations("x", search=_boom) == []


def test_safe_mode_and_empty_queries_search_nothing() -> None:
    called: list[str] = []

    def _spy(query: str, limit: int = 8) -> list[_Entry]:
        called.append(query)
        return []

    assert youtube_search_stations("x", safe_mode=True, search=_spy) == []
    assert youtube_search_stations("   ", search=_spy) == []
    assert called == []


@pytest.mark.parametrize("cap", [0, -1])
def test_a_zero_cap_searches_nothing(cap: int) -> None:
    assert youtube_search_stations("x", cap=cap, search=lambda q, limit=8: [_Entry("u", "t")]) == []
