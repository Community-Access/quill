"""Rearrange Library and Inbox: each choice is stored, saved and drawn at once."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.podcasts import library_view
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import library_view_dialog


def _host() -> SimpleNamespace:
    library = PodcastLibrary()
    calls: list[str] = []
    host = SimpleNamespace(
        _podcast_library=library,
        _save_podcast_library=lambda: calls.append("save"),
        _refresh_place=lambda keep=True: calls.append("refresh"),
        calls=calls,
    )

    def set_sort(mode: str, *, announce: bool = True) -> None:
        library.settings.show_sort_mode = mode

    host._set_show_sort_mode = set_sort
    return host


def test_a_choice_is_stored_saved_and_drawn() -> None:
    host = _host()
    assert library_view_dialog.apply(host, "library_layout", "folders_only")
    assert library_view.setting(host._podcast_library, "library_layout") == "folders_only"
    assert host.calls == ["save", "refresh"]


def test_the_same_choice_again_does_nothing() -> None:
    host = _host()
    assert not library_view_dialog.apply(host, "library_layout", "folders_first")
    assert host.calls == []


def test_podcast_order_goes_through_the_existing_sort() -> None:
    host = _host()
    assert library_view_dialog.apply(host, "show_sort_mode", "unheard_first")
    assert host._podcast_library.settings.show_sort_mode == "unheard_first"
