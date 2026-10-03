"""Cast's Preferences offers "Where to land on launch" and saves it (Phase 1, kept by Phase 5).

The field, ``PodcastSettings.default_launch_view``, is a library setting: it
names a place, and travels with a synced data folder. Preferences now has
eight sections (qc.md 13); the row lives in *When Cast opens*, offered as the
places it can name, and a saved choice is written to the library through the
catalogue -- only when it changed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.podcasts_preferences import CastPreferencesMixin, app_rows
from quill.core.podcasts import launch_place, settings_catalog
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.preferences_window import section_of


class _FakeWindow:
    answer: Any = None
    built: list[dict[str, Any]] = []

    def __init__(self, _parent: Any, **kwargs: Any) -> None:
        _FakeWindow.built.append(kwargs)

    def show(self) -> Any:
        return _FakeWindow.answer


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch, tmp_path) -> SimpleNamespace:
    import quill.ui.podcasts.preferences_window as window_module
    from quill.core.podcasts import history as podcast_history

    _FakeWindow.built = []
    _FakeWindow.answer = None
    monkeypatch.setattr(window_module, "CastPreferencesWindow", _FakeWindow)
    monkeypatch.setattr(podcast_history, "save_history", lambda *_a, **_k: None)
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    library = PodcastLibrary()
    saved: list[str] = []
    spoken: list[str] = []
    obj = SimpleNamespace(
        frame=SimpleNamespace(GetMenuBar=lambda: None),
        _podcast_history=SimpleNamespace(resume_on_launch=False),
        _podcast_library=library,
        _announce=spoken.append,
        _save_podcast_library=lambda: saved.append(library.settings.default_launch_view),
        _refresh_place=lambda **_k: None,
        saved=saved,
        spoken=spoken,
    )
    obj.open = lambda: CastPreferencesMixin._open_preferences(obj)
    return obj


def test_the_row_is_in_when_cast_opens_with_every_place() -> None:
    definition = settings_catalog.definition("default_launch_view")
    assert definition is not None
    assert section_of(definition) == "opens"
    values = [value for value, _label in launch_place.CHOICES]
    assert values[0] == launch_place.AUTOMATIC
    for place in ("inbox", "new_episodes", "continue_listening", "favorites", "queue", "podcasts"):
        assert place in values, place


def test_the_default_is_the_automatic_rule() -> None:
    assert launch_place.index_for("") == 0
    assert launch_place.index_for("bogus") == 0
    assert launch_place.view_at(99) == launch_place.AUTOMATIC


def test_choosing_a_place_saves_it_on_the_library(host) -> None:
    _FakeWindow.answer = ({}, {"default_launch_view": "inbox"})
    host.open()
    assert host._podcast_library.settings.default_launch_view == "inbox"
    assert host.saved == ["inbox"]
    assert host.spoken[-1].startswith("Preferences saved")


def test_leaving_it_alone_does_not_rewrite_the_library(host) -> None:
    _FakeWindow.answer = ({}, {})
    host.open()
    assert host.saved == []
    assert host.spoken[-1] == "Preferences closed; nothing changed."


def test_cancel_changes_nothing(host) -> None:
    _FakeWindow.answer = None
    host.open()
    assert host.saved == [] and host.spoken == []


def test_every_app_row_has_a_section_and_help_that_says_what_it_does_not_do() -> None:
    sections = {"opens", "playing", "fetching", "inbox", "chapters", "telling", "window", "data"}
    rows = app_rows(SimpleNamespace(open_cast_data_folder=lambda: None))
    keys = [row.key for row in rows]
    assert len(keys) == len(set(keys))
    for row in rows:
        assert row.section in sections, row.key
        lowered = row.help.lower()
        assert any(word in lowered for word in ("not", "never", "nothing", "off")), row.key
