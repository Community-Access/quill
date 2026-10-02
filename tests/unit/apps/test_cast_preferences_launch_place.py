"""Cast's Preferences offers "Where to land on launch" and saves it (Phase 1).

The field, ``PodcastSettings.default_launch_view``, existed for a release with
nothing exposing it. These drive the real ``_open_preferences`` with a fake
Preferences dialog that answers as a listener would, and check the row's
place, its default, and that choosing a place saves the *library* -- where the
field lives -- only when it changed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.podcasts_preferences import CastPreferencesMixin
from quill.core.podcasts import launch_place


class _FakeDialog:
    built: list[_FakeDialog] = []
    answer_launch_index = 0

    def __init__(self, _parent: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs
        _FakeDialog.built.append(self)

    def show(self) -> Any:
        checkboxes = [c.value for c in self.kwargs["checkboxes"]]
        choices = [c.selected_index for c in self.kwargs["choices"]]
        choices[2] = _FakeDialog.answer_launch_index
        return checkboxes, choices, []


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch, tmp_path) -> SimpleNamespace:
    import quill.ui.app_preferences_dialog as prefs
    from quill.core.podcasts import history as podcast_history

    _FakeDialog.built = []
    monkeypatch.setattr(prefs, "PreferencesDialog", _FakeDialog)
    monkeypatch.setattr(podcast_history, "save_history", lambda *_a, **_k: None)
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    history = SimpleNamespace(
        resume_on_launch=False,
        check_updates_on_startup=True,
        announce_dialog_transitions=False,
        alt_f4_to_tray=False,
        winamp_playback_keys=True,
        ai_help_enabled=False,
        switch_to_now_playing=False,
        podcast_check_enabled=False,
        podcast_check_interval_minutes=0,
        close_action="exit",
    )
    saved: list[str] = []
    spoken: list[str] = []
    library = SimpleNamespace(settings=SimpleNamespace(default_launch_view=""))
    frame = SimpleNamespace(GetMenuBar=lambda: None)
    obj = SimpleNamespace(
        frame=frame,
        _podcast_history=history,
        _podcast_library=library,
        _announce=spoken.append,
        _save_podcast_library=lambda: saved.append(library.settings.default_launch_view),
        _resume_menu_item_id=1,
        _PODCASTS=CastPreferencesMixin._PODCASTS,
        saved=saved,
        spoken=spoken,
    )
    obj._preferences_app_title = lambda: "QUILL Cast"
    obj.open = lambda: CastPreferencesMixin._open_preferences(obj)
    return obj


def test_the_row_is_offered_in_the_podcasts_group_with_every_place(host) -> None:
    host.open()
    row = _FakeDialog.built[0].kwargs["choices"][2]
    assert row.name == "Where to land on la&unch:"
    assert row.options == [label for _value, label in launch_place.CHOICES]
    assert row.group == CastPreferencesMixin._PODCASTS


def test_the_default_is_the_automatic_rule(host) -> None:
    host.open()
    assert _FakeDialog.built[0].kwargs["choices"][2].selected_index == 0


def test_choosing_a_place_saves_it_on_the_library(host) -> None:
    _FakeDialog.answer_launch_index = 1  # Inbox
    host.open()
    assert host._podcast_library.settings.default_launch_view == "inbox"
    assert host.saved == ["inbox"]
    assert host.spoken and host.spoken[-1].startswith("Preferences saved")


def test_leaving_it_alone_does_not_rewrite_the_library(host) -> None:
    _FakeDialog.answer_launch_index = 0
    host.open()
    assert host.saved == []


def test_a_stored_place_reopens_selected(host) -> None:
    host._podcast_library.settings.default_launch_view = "favorites"
    _FakeDialog.answer_launch_index = launch_place.index_for("favorites")
    host.open()
    assert _FakeDialog.built[0].kwargs["choices"][2].selected_index == launch_place.index_for(
        "favorites"
    )
    assert host.saved == []
