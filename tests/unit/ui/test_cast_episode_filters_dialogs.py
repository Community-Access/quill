"""Both Episode Filters windows actually build, and read back what they were given.

The wiring tests in ``test_cast_episode_filters.py`` deliberately never touch
wx. This file is the other half: it constructs the two real dialogs headlessly
(never showing them) and checks the three things only a real widget tree can
answer --

* every control the save path reads exists and holds the stored value;
* the eight scope checkboxes are **eight checkboxes**, and reading them back
  reproduces the configuration they were built from (A11Y-SR-1 rules out the
  check-list that would have been one control, so the round trip is worth
  pinning);
* the rule editor's validation refuses a rule that would never match, and
  accepts one that would.

Nothing is shown, nothing is modal, and no library is written.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.podcasts import episode_filter_maintenance as maintenance  # noqa: E402
from quill.core.podcasts.models import PodcastEpisode, PodcastShow  # noqa: E402
from quill.core.podcasts.models_filters import (  # noqa: E402
    FILTER_SCOPES,
    MODE_KEEP_MATCHING,
    PATTERN_WILDCARD,
    SCOPE_LIBRARY,
    SCOPE_QUEUE,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
)
from quill.core.podcasts.subscriptions import PodcastLibrary  # noqa: E402
from quill.ui.podcasts.episode_filter_rule_dialog import EpisodeFilterRuleDialog  # noqa: E402
from quill.ui.podcasts.episode_filters_dialog import EpisodeFiltersDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _episode(title: str, minutes: int = 30) -> PodcastEpisode:
    return PodcastEpisode(
        guid=title,
        title=title,
        audio_url=f"https://example.test/{title}.mp3",
        published="2026-08-01",
        duration_seconds=minutes * 60,
    )


def _library() -> tuple[PodcastLibrary, PodcastShow]:
    show = PodcastShow(
        id="s1",
        title="A Show",
        feed_url="https://example.test/feed.xml",
        episodes=[_episode("The Main Episode"), _episode("Daily Segment", 2)],
    )
    return PodcastLibrary(shows=[show]), show


def test_the_filters_window_builds_and_shows_the_stored_configuration(wx_app, tmp_path) -> None:
    library, show = _library()
    stored = EpisodeFilterConfiguration(
        enabled=True,
        mode=MODE_KEEP_MATCHING,
        scopes={SCOPE_LIBRARY, SCOPE_QUEUE},
        rules=[EpisodeFilterRule(name="Segments", pattern_kind=PATTERN_WILDCARD, pattern="*Seg*")],
    )
    maintenance.set_filter(library, show, stored)

    frame = wx.Frame(None)
    try:
        dialog = EpisodeFiltersDialog(frame, library=library, show=show)
        try:
            assert dialog._enabled.GetValue() is True
            assert dialog._rules.GetCount() == 1
            assert dialog._rules.GetString(0).startswith("Segments, enabled.")
            # Eight independent checkboxes, ticked to match what was stored.
            assert len(dialog._scope_boxes) == len(FILTER_SCOPES)
            for scope, box in dialog._scope_boxes.items():
                assert isinstance(box, wx.CheckBox)
                assert box.GetValue() is (scope in stored.scopes)
            # And reading them back reproduces the configuration.
            dialog._sync_draft()
            assert dialog._draft.scopes == stored.scopes
            assert dialog._draft.mode == MODE_KEEP_MATCHING
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_the_filters_window_previews_without_touching_anything(wx_app) -> None:
    library, show = _library()
    maintenance.set_filter(
        library,
        show,
        EpisodeFilterConfiguration(
            enabled=False,  # switched off: Preview must still evaluate the draft
            rules=[
                EpisodeFilterRule(name="Segments", pattern_kind=PATTERN_WILDCARD, pattern="*Seg*")
            ],
        ),
    )
    frame = wx.Frame(None)
    try:
        dialog = EpisodeFiltersDialog(frame, library=library, show=show)
        try:
            said: list[str] = []
            dialog._announce = said.append
            dialog._on_preview(None)
            assert dialog._preview_list.GetCount() == 2
            rows = [dialog._preview_list.GetString(i) for i in range(2)]
            assert any(row.startswith("Filtered, Daily Segment") for row in rows)
            assert said and "would be filtered out" in said[0]
            # A dry run changes nothing at all.
            assert library.queue == []
            assert library.inbox_assignments == {}
            assert len(show.episodes) == 2
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_the_rule_editor_builds_and_reads_back_a_rule(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        rule = EpisodeFilterRule(
            name="Segments",
            pattern_kind=PATTERN_WILDCARD,
            pattern="*Seg*",
            case_sensitive=True,
            min_duration_minutes=5,
        )
        dialog = EpisodeFilterRuleDialog(frame, rule=rule)
        try:
            assert dialog._name.GetValue() == "Segments"
            assert dialog._pattern.GetValue() == "*Seg*"
            assert dialog._case.GetValue() is True
            assert dialog._duration.GetValue() == 5
            drafted = dialog._drafted()
            assert drafted.pattern_kind == PATTERN_WILDCARD
            assert drafted.min_duration_minutes == 5
            assert drafted.is_usable
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_the_rule_editor_refuses_a_rule_that_could_never_match(wx_app, monkeypatch) -> None:
    """No title, no length: the one rule that is always wrong."""
    frame = wx.Frame(None)
    refused: list[str] = []
    try:
        dialog = EpisodeFilterRuleDialog(frame)
        try:
            monkeypatch.setattr(dialog, "_refuse", lambda message, focus: refused.append(message))
            dialog._pattern.SetValue("")
            dialog._duration.SetValue(0)
            dialog._on_ok(None)
            assert refused and "never match" in refused[0]
            assert dialog._result is None
        finally:
            dialog.dialog.Destroy()
    finally:
        frame.Destroy()
