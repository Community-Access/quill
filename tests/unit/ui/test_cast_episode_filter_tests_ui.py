"""The widened Episode Filter windows build, read back, and reach their new verbs.

Headless, never shown, never modal: the rule editor's tests list, its Match when
choice and Try It; the new Episode Filter Test window and its comparison list
that follows the field; and Filter Episodes Like This, from the episode's own
menu through to a drafted rule in the filter's draft.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.podcasts import quick_actions  # noqa: E402
from quill.core.podcasts.filter_conditions import (  # noqa: E402
    FIELD_DURATION,
    FIELD_NOTES,
    FIELD_TYPE,
    FIELDS,
    OP_AT_MOST,
    OP_CONTAINS,
    OP_IS,
    OP_IS_NOT,
    FilterCondition,
)
from quill.core.podcasts.filter_suggestions import suggest_rule  # noqa: E402
from quill.core.podcasts.models import PodcastEpisode, PodcastShow  # noqa: E402
from quill.core.podcasts.models_filters import PATTERN_NONE, EpisodeFilterRule  # noqa: E402
from quill.core.podcasts.subscriptions import PodcastLibrary  # noqa: E402
from quill.ui.podcasts import manager_menus  # noqa: E402
from quill.ui.podcasts.episode_filter_rule_dialog import EpisodeFilterRuleDialog  # noqa: E402
from quill.ui.podcasts.episode_filter_test_dialog import (  # noqa: E402
    EpisodeFilterTestDialog,
    comparison_choices,
)
from quill.ui.podcasts.episode_filters_dialog import EpisodeFiltersDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _episode(title: str, minutes: int = 30, kind: str = "") -> PodcastEpisode:
    return PodcastEpisode(
        guid=title,
        title=title,
        audio_url=f"https://example.test/{title}.mp3",
        published="Mon, 28 Sep 2026 10:00:00 +0000",
        duration_seconds=minutes * 60,
        episode_type=kind,
    )


def _show() -> PodcastShow:
    return PodcastShow(
        id="s1",
        title="A Show",
        feed_url="https://example.test/feed.xml",
        episodes=[
            _episode("Daily Briefing: Monday", 3),
            _episode("Daily Briefing: Tuesday", 3),
            _episode("The Big Interview", 60),
            _episode("Coming Soon", 2, kind="trailer"),
        ],
    )


def test_the_type_field_offers_whole_phrases_and_numbers_offer_comparisons() -> None:
    rows = comparison_choices(FIELD_TYPE)
    assert ("is a trailer", OP_IS, "trailer") in rows
    assert ("is not a bonus episode", OP_IS_NOT, "bonus") in rows
    assert [op for _label, op, _v in comparison_choices(FIELD_DURATION)][:2] == [
        "at_least",
        "at_most",
    ]


def test_the_test_window_reads_back_what_it_was_given(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        given = FilterCondition(FIELD_NOTES, OP_CONTAINS, "sponsor", case_sensitive=True)
        dialog = EpisodeFilterTestDialog(frame, condition=given)
        assert dialog._drafted() == given
        # Switching the field to the type refills the comparisons and disables
        # the value box, so "is a trailer" is the whole test.
        dialog._field.SetSelection(FIELDS.index(FIELD_TYPE))
        dialog._on_field(None)
        assert not dialog._value.IsEnabled()
        dialog._op.SetSelection(1)
        assert dialog._drafted() == FilterCondition(FIELD_TYPE, OP_IS, "trailer")
        dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_the_rule_editor_keeps_tests_and_match_any(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        rule = EpisodeFilterRule(
            name="Short or trailers",
            pattern_kind=PATTERN_NONE,
            conditions=[
                FilterCondition(FIELD_TYPE, OP_IS, "trailer"),
                FilterCondition(FIELD_DURATION, OP_AT_MOST, "5"),
            ],
            match_any=True,
        )
        dialog = EpisodeFilterRuleDialog(frame, rule=rule, episodes=_show().episodes)
        assert dialog._tests.GetCount() == 2
        drafted = dialog._drafted()
        assert drafted.match_any and drafted.conditions == rule.conditions
        dialog._on_try(None)
        assert dialog._trial.GetValue().startswith("Matches 3 of the 4 newest episodes.")
        dialog._tests.SetSelection(0)
        dialog._on_remove_test(None)
        assert len(dialog._drafted().conditions) == 1
        dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_filter_like_this_is_on_the_episode_menu_and_a_quick_action() -> None:
    assert "filter_like_this" in quick_actions.default_order("episode")
    labels = {action.id: action.label for action in quick_actions.EPISODE_ACTIONS}
    assert labels["filter_like_this"] == "Filter Episodes Like This..."
    src = manager_menus.__file__
    with open(src, encoding="utf-8") as handle:
        text = handle.read()
    assert '"&Filter Episodes Like This..."' in text
    assert "dialog._on_filter_like_this(show, episode)" in text


def test_a_suggestion_opens_the_rule_editor_and_switches_filtering_on(wx_app, monkeypatch) -> None:
    show = _show()
    library = PodcastLibrary(shows=[show])
    suggestion = suggest_rule(show.episodes[1], show.episodes)
    frame = wx.Frame(None)
    try:
        dialog = EpisodeFiltersDialog(frame, library=library, show=show, suggestion=suggestion)
        seen: dict[str, object] = {}

        def fake_rule_dialog(rule=None, *, intro=""):
            seen["rule"], seen["intro"] = rule, intro
            return rule

        monkeypatch.setattr(dialog, "_rule_dialog", fake_rule_dialog)
        dialog._offer_suggestion()
        assert seen["rule"] is suggestion.rule
        assert str(seen["intro"]).startswith("Like this one because")
        assert dialog._draft.enabled and dialog._enabled.GetValue()
        assert dialog._draft.rules[-1] is suggestion.rule
        # Offered once: a second call does nothing.
        dialog._offer_suggestion()
        assert len(dialog._draft.rules) == 1
        dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_declining_the_suggestion_adds_nothing(wx_app, monkeypatch) -> None:
    show = _show()
    library = PodcastLibrary(shows=[show])
    frame = wx.Frame(None)
    try:
        dialog = EpisodeFiltersDialog(
            frame,
            library=library,
            show=show,
            suggestion=suggest_rule(show.episodes[3], show.episodes),
        )
        said: list[str] = []
        dialog._announce = said.append
        monkeypatch.setattr(dialog, "_rule_dialog", lambda rule=None, *, intro="": None)
        dialog._offer_suggestion()
        assert dialog._draft.rules == [] and not dialog._draft.enabled
        assert said == ["No rule added."]
        dialog.dialog.Destroy()
    finally:
        frame.Destroy()
