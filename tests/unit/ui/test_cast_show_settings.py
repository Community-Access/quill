"""The rebuilt per-podcast settings window, and the list editors beside it.

The chain and the catalogue are pinned in
``tests/unit/core/podcasts/test_show_settings.py``. What is pinned here is what
only a real widget tree can answer:

* the window is **generated from the catalogue**, so a setting added to the
  catalogue appears with no UI code -- and every control it builds is named,
  helped, and shows the value in force rather than a blank;
* **saving writes only what changed**, which is the whole reason the old
  window's whole-record clone had to go;
* **Follow** appears only where there is an opinion to drop, and dropping one
  falls back to the folder rather than writing today's default over it;
* both window titles resolve to authored F1 help.

Constructed headlessly and never shown, exactly as the Episode Filters dialog
tests are.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.podcasts import settings_catalog, surface_help  # noqa: E402
from quill.core.podcasts.models import PodcastFolder, PodcastShow  # noqa: E402
from quill.core.podcasts.models_episode import PodcastEpisode  # noqa: E402
from quill.core.podcasts.settings_resolver import set_value, value_of  # noqa: E402
from quill.core.podcasts.settings_types import (  # noqa: E402
    CATEGORY_ARRIVAL,
    CATEGORY_PLAYBACK,
    LEVEL_FOLDER,
    LEVEL_SHOW,
)
from quill.core.podcasts.subscriptions import PodcastLibrary  # noqa: E402
from quill.ui.podcasts.show_settings_dialog import ShowSettingsDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    # SetHelpText stores nothing at all without a wx.HelpProvider -- the
    # load-bearing detail behind every F1 answer in this family. The app
    # installs one at activation; a headless test has to do it itself, and
    # without this every assertion about help below would pass vacuously
    # against an empty string.
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    yield app
    app.Destroy()


def _library() -> tuple[PodcastLibrary, PodcastShow]:
    folder = PodcastFolder(id="f-news", name="News")
    show = PodcastShow(
        id="s1",
        title="The Daily",
        feed_url="https://example.test/feed.xml",
        folder_id="f-news",
        episodes=[
            PodcastEpisode(guid="e1", title="Ep. 1: One", audio_url="https://e/1.mp3"),
        ],
    )
    return PodcastLibrary(shows=[show], folders=[folder]), show


def _definition(setting_id: str):
    found = settings_catalog.definition(setting_id)
    assert found is not None
    return found


def _control_for(dialog: ShowSettingsDialog, setting_id: str):
    for built in dialog._controls:
        if built.definition.id == setting_id:
            return built
    return None


def test_the_window_builds_its_controls_from_the_catalogue(wx_app) -> None:
    library, show = _library()
    frame = wx.Frame(None)
    try:
        dialog = ShowSettingsDialog(frame, library=library, show=show)
        try:
            expected = settings_catalog.for_category(CATEGORY_ARRIVAL, level=LEVEL_SHOW)
            assert {b.definition.id for b in dialog._controls} == {d.id for d in expected}
            assert len(dialog._controls) > 10
            for built in dialog._controls:
                assert built.control is not None
                # Everything a person can land on says what it does, and the
                # help carries where the value came from.
                assert built.control.GetHelpText()
                assert "shared default" in built.control.GetHelpText()
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_changing_the_category_rebuilds_the_panel(wx_app) -> None:
    library, show = _library()
    frame = wx.Frame(None)
    try:
        dialog = ShowSettingsDialog(frame, library=library, show=show)
        try:
            said: list[str] = []
            dialog._announce = said.append
            index = dialog._categories.index(CATEGORY_PLAYBACK)
            dialog._category.SetSelection(index)
            dialog._on_category(None)
            assert {b.definition.category for b in dialog._controls} == {CATEGORY_PLAYBACK}
            # The count, not the name: the reader already said the name.
            assert said and "Playback settings" in said[0]
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_a_control_shows_the_value_in_force_not_a_blank(wx_app) -> None:
    """Inherited from the folder, and the help says so."""
    library, show = _library()
    set_value(library, _definition("refresh_minutes"), 60, level=LEVEL_FOLDER, scope_id="f-news")
    frame = wx.Frame(None)
    try:
        dialog = ShowSettingsDialog(frame, library=library, show=show)
        try:
            built = _control_for(dialog, "refresh_minutes")
            assert built is not None
            assert built.control.GetValue() == 60
            assert "folder News" in built.control.GetHelpText()
            # Inherited, so there is nothing of this podcast's own to drop.
            assert built.follow_button is None
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_saving_writes_only_what_changed(wx_app) -> None:
    """The bug the old whole-record clone caused, pinned."""
    library, show = _library()
    frame = wx.Frame(None)
    try:
        dialog = ShowSettingsDialog(frame, library=library, show=show)
        try:
            built = _control_for(dialog, "inbox_max_episodes")
            assert built is not None
            built.control.SetValue(9)
            dialog._on_ok(None)
        finally:
            pass
    finally:
        frame.Destroy()
    stored = library.scope_overrides["show:s1"]
    assert stored == {"inbox_max_episodes": 9}
    # Everything else still follows the shared default, so changing one reaches
    # this podcast.
    library.settings.retention_count = 12
    assert library.effective_settings(show).retention_count == 12


def test_follow_appears_only_where_there_is_an_opinion_to_drop(wx_app) -> None:
    library, show = _library()
    set_value(library, _definition("refresh_minutes"), 30, level=LEVEL_FOLDER, scope_id="f-news")
    set_value(library, _definition("refresh_minutes"), 120, level=LEVEL_SHOW, scope_id="s1")
    frame = wx.Frame(None)
    try:
        dialog = ShowSettingsDialog(frame, library=library, show=show)
        try:
            built = _control_for(dialog, "refresh_minutes")
            assert built is not None
            assert built.follow_button is not None
            said: list[str] = []
            dialog._announce = said.append
            dialog._on_follow(built.definition)
            # Back to the folder, not to the class default.
            assert value_of(library, _definition("refresh_minutes"), show=show) == 30
            assert said and "follows the folder" in said[0]
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_the_window_carries_the_verbs_that_are_not_settings(wx_app) -> None:
    library, show = _library()
    frame = wx.Frame(None)
    try:
        dialog = ShowSettingsDialog(frame, library=library, show=show)
        try:
            assert dialog._favorite.GetValue() is False
            assert dialog._route_inbox.GetValue() is False
            assert dialog._auto_queue.GetValue() is False
            dialog._favorite.SetValue(True)
            dialog._on_ok(None)
            assert show.is_favorite is True
        finally:
            pass
    finally:
        frame.Destroy()


def test_a_list_shaped_setting_opens_its_own_editor(wx_app) -> None:
    from quill.ui.podcasts.show_list_editor import ListSettingDialog

    library, show = _library()
    frame = wx.Frame(None)
    try:
        dialog = ListSettingDialog(
            frame, library=library, show=show, definition=_definition("title_cleanup")
        )
        try:
            said: list[str] = []
            dialog._announce = said.append
            dialog._entries.append(
                __import__("quill.core.podcasts.title_cleanup", fromlist=["TitleRule"]).TitleRule(
                    "Ep. *: "
                )
            )
            dialog._fill()
            assert dialog._list.GetCount() == 1
            assert dialog._list.GetString(0).startswith("Remove 'Ep. *: ' at the start.")
            dialog._on_preview(None)
            assert said and "would change" in said[-1]
            dialog._on_ok(None)
        finally:
            pass
    finally:
        frame.Destroy()
    # Saved as this podcast's own opinion, and readable back as a rule.
    from quill.core.podcasts.show_policy import title_rules

    assert [rule.pattern for rule in title_rules(library, show)] == ["Ep. *: "]


def test_labels_are_stored_beside_the_library_not_as_a_setting(wx_app) -> None:
    from quill.ui.podcasts.show_list_editor import ListSettingDialog

    library, show = _library()
    frame = wx.Frame(None)
    try:
        dialog = ListSettingDialog(
            frame, library=library, show=show, definition=_definition("labels")
        )
        try:
            dialog._entries.extend(["news", "short"])
            dialog._on_ok(None)
        finally:
            pass
    finally:
        frame.Destroy()
    assert library.labels_for("s1") == ["news", "short"]


def test_both_windows_answer_f1_with_authored_help() -> None:
    assert surface_help.is_known_title("Settings for The Daily")
    for subject in ("Tidy Episode Titles", "Skip Chapters", "Labels"):
        assert surface_help.is_known_title(f"{subject} -- The Daily"), subject
        purpose = surface_help.purpose_for_title(f"{subject} -- The Daily")
        assert purpose != surface_help.GENERIC_PURPOSE, subject
