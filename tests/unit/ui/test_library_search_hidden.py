"""Find Stations never searches a library hidden in Choose Browse Sources."""

from __future__ import annotations

from quill.core.radio import browse_visibility
from quill.ui.radio.library_search import shown_libraries

LIBRARIES = ("librivox", "gutenberg", "archive", "apple_podcasts", "audius")


def test_the_defaults_search_every_library() -> None:
    assert shown_libraries(LIBRARIES, None) == LIBRARIES


def test_a_hidden_library_is_not_searched() -> None:
    choice = browse_visibility.toggle(None, "librivox")
    assert "librivox" not in shown_libraries(LIBRARIES, choice)


def test_apple_podcasts_follows_its_browse_branch() -> None:
    choice = browse_visibility.toggle(None, "apple")
    assert "apple_podcasts" not in shown_libraries(LIBRARIES, choice)
