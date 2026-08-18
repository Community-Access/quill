"""May this be saved to a file? The rights question, and its four refusals.

The failure this prevents is QUILL writing somebody a file it had no right to
write. So the rule is affirmative -- a source must be *on the list* -- and every
refusal carries the real reason, because "Download is missing from the menu" and
"this is copy-protected" and "this is live so there is no file" are completely
different things to know.
"""

from __future__ import annotations

import pytest

from quill.core.radio.downloadable import (
    ALLOWED_SOURCES,
    LIVE_REASON,
    UNKNOWN_REASON,
    can_download,
    describe,
    licence_note,
    suggested_filename,
)
from quill.core.radio.models import RadioStation


def _row(source: str, *, recording: bool = True, url: str = "https://a/x.mp3", **kwargs):
    return RadioStation(
        name=kwargs.pop("name", "A Thing"),
        stream_url=url,
        source=source,
        is_recording=recording,
        **kwargs,
    )


@pytest.mark.parametrize("source", sorted(ALLOWED_SOURCES))
def test_every_allowed_source_can_be_saved_and_says_on_what_basis(source: str) -> None:
    decision = can_download(_row(source))
    assert decision.allowed is True
    # The basis is shown in the confirmation, so a listener knows *why* they may.
    assert decision.basis


def test_every_surface_that_lists_podcast_episodes_can_download_them() -> None:
    # The same episode reaches the menu under different source names depending
    # on where it was found: "Podcasts (Apple)" from search results,
    # "Apple Podcasts" from the browse tree, "Subscribed Podcasts" from
    # Subscriptions. The allowlist knew only the first, so Download silently
    # vanished from the tree (reported 2026-08-18). PODCAST_EPISODE_SOURCES is
    # the canonical set of tree-side names -- pin the whole thing so a renamed
    # source breaks here instead of dropping the menu item.
    from quill.core.podcasts.radio_listens import PODCAST_EPISODE_SOURCES

    for source in sorted(PODCAST_EPISODE_SOURCES) + ["Podcasts (Apple)"]:
        decision = can_download(_row(source))
        assert decision.allowed is True, f"Download missing for source {source!r}"


def test_a_live_station_is_refused_and_pointed_at_the_command_that_works() -> None:
    # Not a rights refusal: a broadcast has no end, so there is no file. Wanting
    # to keep it is reasonable, and Record Station is how.
    decision = can_download(_row("Radio Browser", recording=False))
    assert decision.allowed is False
    assert decision.reason == LIVE_REASON
    assert "Record Station" in decision.reason


def test_spotify_is_refused_because_it_is_copy_protected() -> None:
    decision = can_download(_row("Spotify", url="spotify:episode:1"))
    assert decision.allowed is False
    assert "copy-protected" in decision.reason


def test_youtube_is_refused_as_a_decision_rather_than_a_limitation() -> None:
    decision = can_download(_row("YouTube"))
    assert decision.allowed is False
    assert "deliberately does not" in decision.reason


def test_mixcloud_is_refused_because_there_is_no_stream_to_save() -> None:
    decision = can_download(_row("Mixcloud", recording=False))
    assert decision.allowed is False
    assert "never takes a stream" in decision.reason


def test_audius_is_refused_rather_than_guessed_at() -> None:
    # Whether a track may be downloaded is the artist's choice, and the listing
    # does not say. Guessing would be QUILL deciding on the artist's behalf.
    decision = can_download(_row("Audius"))
    assert decision.allowed is False
    assert "does not guess" in decision.reason


def test_an_unknown_source_is_refused_by_default() -> None:
    # Never assume a downloadable-looking file may be redistributed.
    decision = can_download(_row("Some New Directory"))
    assert decision.allowed is False
    assert decision.reason == UNKNOWN_REASON


def test_a_row_with_no_address_is_refused() -> None:
    assert can_download(_row("LibriVox", url="")).allowed is False


def test_a_named_refusal_beats_the_generic_live_one() -> None:
    # A Spotify row is not a station; telling somebody it is "live" would be
    # true of nothing and useless to everybody.
    assert "copy-protected" in can_download(_row("Spotify", recording=False)).reason


def test_a_creative_commons_licence_travels_with_the_file() -> None:
    row = _row("ccMixter", tags=("Attribution Noncommercial (4.0)",))
    assert licence_note(row) == "Attribution Noncommercial (4.0)"
    assert licence_note(_row("LibriVox")) == ""


def test_the_filename_is_the_name_a_person_would_recognise() -> None:
    # A LibriVox chapter's address is a string of digits, and a folder of those
    # is a folder nobody can read.
    row = _row("LibriVox", name="Middlemarch: chapter 4/5?", url="https://a/00412.ogg")
    assert suggested_filename(row) == "Middlemarch chapter 45.ogg"


def test_a_filename_falls_back_rather_than_ending_up_bare() -> None:
    row = _row("LibriVox", name="", url="https://a/stream")
    assert suggested_filename(row) == "download.mp3"


def test_the_confirmation_names_the_thing_and_its_basis() -> None:
    row = _row("LibriVox", name="Middlemarch, chapter 4")
    said = describe(can_download(row), row)
    assert "Middlemarch, chapter 4" in said
    assert "public domain" in said


def test_a_refusal_describes_itself_rather_than_saying_nothing() -> None:
    row = _row("Radio Browser", recording=False)
    assert describe(can_download(row), row) == LIVE_REASON
