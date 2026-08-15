"""The Inbox, opt-in or opt-out, from one flag read two ways.

Cast's Inbox has always been opt-in: a show is in it because you marked it.
Opt-out inverts the same mark -- every show is in the Inbox except the ones you
mark -- which is a completely different object over a large library, and is why
the Inbox caps had to exist first.

The rule these pin: **one flag, one helper.** Every surface that asks "is this
show in the Inbox?" asks `in_inbox`, so auto-download, trimming, the republish
sweep and the list itself can never disagree about what the mark means.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.inbox import in_inbox, inbox_pairs
from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library(mode: str, *marks: bool) -> PodcastLibrary:
    library = PodcastLibrary()
    library.settings = PodcastSettings(inbox_mode=mode)
    for index, marked in enumerate(marks):
        library.shows.append(
            PodcastShow(
                id=f"s{index}",
                title=f"Show {index}",
                feed_url=f"https://f/{index}",
                route_to_inbox=marked,
                episodes=[
                    PodcastEpisode(
                        guid=f"e{index}",
                        title=f"Episode {index}",
                        audio_url=f"https://a/{index}.mp3",
                    )
                ],
            )
        )
    return library


def test_include_mode_is_the_behaviour_cast_has_always_had() -> None:
    library = _library("include", True, False)
    assert in_inbox(library, library.shows[0]) is True
    assert in_inbox(library, library.shows[1]) is False


def test_exclude_mode_inverts_the_same_mark() -> None:
    # The mark now reads "keep this one out", which is why the menu label and the
    # spoken confirmation both change with the mode.
    library = _library("exclude", True, False)
    assert in_inbox(library, library.shows[0]) is False
    assert in_inbox(library, library.shows[1]) is True


def test_the_inbox_listing_follows_the_mode() -> None:
    marked_only = _library("include", True, False)
    assert [s.id for s, _e in inbox_pairs(marked_only)] == ["s0"]

    everything_else = _library("exclude", True, False)
    assert [s.id for s, _e in inbox_pairs(everything_else)] == ["s1"]


@pytest.mark.parametrize("stored", ["sideways", "", "EXCLUDE ", "Include"])
def test_a_stored_mode_is_validated_and_never_widens_the_inbox_by_accident(stored: str) -> None:
    # A settings file is somebody else's input. An unknown value must fall back
    # to "include", which can only ever show *fewer* shows than expected --
    # silently sweeping a 1,300-show library into the Inbox would be the one
    # unrecoverable direction to be wrong in.
    settings = PodcastSettings.from_dict({"inbox_mode": stored})
    assert settings.inbox_mode in {"include", "exclude"}
    if stored.strip().lower() != "exclude":
        assert settings.inbox_mode == "include"


def test_the_mode_round_trips_through_settings() -> None:
    saved = PodcastSettings(inbox_mode="exclude").to_dict()
    assert saved["inbox_mode"] == "exclude"
    assert PodcastSettings.from_dict(saved).inbox_mode == "exclude"


def test_the_default_is_unchanged_for_everyone_who_never_touches_it() -> None:
    assert PodcastSettings().inbox_mode == "include"
    assert PodcastSettings.from_dict({}).inbox_mode == "include"
