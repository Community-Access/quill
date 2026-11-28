"""Alert choices: rule matching, presets, quiet hours with Extreme break-through,
place on/off, defaults that preserve earlier behaviour, and persistence."""

from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

from quill.core.weather import alert_rules as ar
from quill.core.weather import alert_rules_store as store
from quill.core.weather import alert_rules_text as text
from quill.core.weather import monitor
from quill.core.weather.alert_delivery import hidden_ids, plan_poll
from quill.core.weather.models import WeatherAlert


def alert(
    event: str, severity: str = "Moderate", urgency: str = "Expected", i: str = ""
) -> WeatherAlert:
    return WeatherAlert(id=i or event, event=event, severity=severity, urgency=urgency)


NIGHT = time(23, 30)
NOON = time(12, 0)


# -- categories and kinds -----------------------------------------------------


@pytest.mark.parametrize(
    ("event", "category", "kind"),
    [
        ("Tornado Warning", "Tornado", "Warning"),
        ("Severe Thunderstorm Watch", "Severe thunderstorm", "Watch"),
        ("Flash Flood Warning", "Flash flood and flood", "Warning"),
        ("Winter Weather Advisory", "Winter weather", "Advisory"),
        ("Excessive Heat Warning", "Heat and cold", "Warning"),
        ("Wind Chill Advisory", "Heat and cold", "Advisory"),
        ("High Wind Warning", "Wind", "Warning"),
        ("Red Flag Warning", "Fire weather", "Warning"),
        ("Hurricane Local Statement", "Hurricane and tropical", "Statement"),
        ("Small Craft Advisory", "Coastal and marine", "Advisory"),
        ("Coastal Flood Warning", "Coastal and marine", "Warning"),
        ("Air Quality Alert", "Air quality", "Advisory"),
        ("Special Weather Statement", "Other", "Statement"),
        ("Brand New Product Warning", "Other", "Warning"),
        ("Dust Storm Warning", "Wind", "Warning"),
    ],
)
def test_category_and_kind(event: str, category: str, kind: str) -> None:
    assert ar.category_of(event) == category
    assert ar.kind_of(event) == kind


def test_every_listed_event_lands_in_its_own_category() -> None:
    for category, events in ar.EVENTS_BY_CATEGORY.items():
        for event in events:
            assert ar.category_of(event) == category


# -- defaults preserve earlier behaviour ----------------------------------------


def test_default_choices_tell_about_everything_as_before() -> None:
    choices = ar.AlertChoices()
    assert choices.is_default()
    for event, severity in [
        ("Tornado Warning", "Extreme"),
        ("Special Weather Statement", "Minor"),
        ("Brand New Product Warning", "Unknown"),
    ]:
        assert not ar.decide(alert(event, severity), "home", choices, NIGHT).hidden
    urgent = ar.decide(alert("Flash Flood Warning", "Severe", "Immediate"), "h", choices)
    calm = ar.decide(alert("Heat Advisory", "Moderate"), "h", choices)
    assert urgent.delivery is ar.Delivery.INTERRUPT  # as monitor.should_force_speech did
    assert calm.delivery is ar.Delivery.QUIET


# -- presets ----------------------------------------------------------------------


def _tells(preset: str, a: WeatherAlert) -> bool:
    choices = ar.AlertChoices(general=ar.RuleSet(ar.Selection(preset)))
    return not ar.decide(a, "p", choices).hidden


def test_essentials() -> None:
    assert _tells("essentials", alert("Tornado Warning", "Extreme"))
    assert _tells("essentials", alert("Severe Thunderstorm Warning", "Severe"))
    assert _tells("essentials", alert("Flash Flood Warning", "Severe"))
    assert _tells("essentials", alert("Earthquake Warning", "Extreme"))  # any Extreme
    assert not _tells("essentials", alert("Tornado Watch", "Severe"))
    assert not _tells("essentials", alert("Heat Advisory", "Moderate"))


def test_safety() -> None:
    assert _tells("safety", alert("Winter Storm Warning", "Moderate"))
    assert _tells("safety", alert("Tornado Watch", "Severe"))
    assert not _tells("safety", alert("Flood Watch", "Moderate"))
    assert not _tells("safety", alert("Wind Advisory", "Minor"))


def test_everything() -> None:
    assert _tells("everything", alert("Dense Fog Advisory", "Minor"))


# -- custom rule matching ---------------------------------------------------------


def _custom(**clause: list[str]) -> ar.AlertChoices:
    return ar.AlertChoices(
        general=ar.RuleSet(ar.Selection("custom", ar.Clause(**clause))), extreme_always=False
    )


def test_custom_by_category() -> None:
    c = _custom(categories=["Winter weather"])
    assert not ar.decide(alert("Winter Storm Warning"), "p", c).hidden
    assert ar.decide(alert("Heat Advisory"), "p", c).hidden


def test_custom_event_inside_and_outside_a_category() -> None:
    c = _custom(
        categories=["Winter weather"], events=["Wind Advisory"], skip_events=["Blizzard Warning"]
    )
    assert not ar.decide(alert("Wind Advisory"), "p", c).hidden
    assert ar.decide(alert("Blizzard Warning"), "p", c).hidden
    assert not ar.decide(alert("Ice Storm Warning"), "p", c).hidden


def test_custom_by_kind_and_severity_together() -> None:
    c = _custom(kinds=["Warning", "Watch"], severities=["Extreme", "Severe"])
    assert not ar.decide(alert("Tornado Watch", "Severe"), "p", c).hidden
    assert ar.decide(alert("Tornado Watch", "Moderate"), "p", c).hidden
    assert ar.decide(alert("Heat Advisory", "Severe"), "p", c).hidden


# -- Extreme is never hidden by accident ---------------------------------------


def test_extreme_is_told_even_when_the_selection_excludes_it() -> None:
    c = _custom(categories=["Winter weather"])
    c.extreme_always = True
    d = ar.decide(alert("Tornado Warning", "Extreme", "Immediate"), "p", c, NOON)
    assert not d.hidden and d.forced_extreme
    assert "always told" in text.describe_decision(d, "Home")


def test_extreme_can_be_hidden_only_by_turning_the_guarantee_off() -> None:
    c = _custom(categories=["Winter weather"])
    assert ar.decide(alert("Tornado Warning", "Extreme"), "p", c).hidden
    assert "Extreme alerts follow your choices" in text.describe_choices(c, 1)


def test_extreme_is_never_list_only_by_accident() -> None:
    general = ar.RuleSet(ar.Selection("custom", ar.Clause(categories=["Wind"])), ar.Delivery.LIST)
    c = ar.AlertChoices(general=general)
    d = ar.decide(alert("Tornado Warning", "Extreme", "Immediate"), "p", c)
    assert d.delivery is ar.Delivery.INTERRUPT


# -- delivery ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("delivery", "speaks", "sounds", "hidden"),
    [
        (ar.Delivery.INTERRUPT, True, True, False),
        (ar.Delivery.QUIET, True, True, False),
        (ar.Delivery.SOUND, False, True, False),
        (ar.Delivery.LIST, False, False, True),
    ],
)
def test_delivery_modes(delivery: ar.Delivery, speaks: bool, sounds: bool, hidden: bool) -> None:
    c = ar.AlertChoices(general=ar.RuleSet(delivery=delivery))
    d = ar.decide(alert("Heat Advisory"), "p", c)
    assert (d.speaks, d.sounds, d.hidden) == (speaks, sounds, hidden)


# -- quiet hours --------------------------------------------------------------------


def test_quiet_hours_window_spans_midnight() -> None:
    q = ar.QuietHours(enabled=True, start="22:00", end="07:00")
    assert q.active_at(time(23, 0)) and q.active_at(time(3, 0)) and q.active_at(time(22, 0))
    assert not q.active_at(time(7, 0)) and not q.active_at(NOON)
    assert not ar.QuietHours(enabled=False).active_at(time(23, 0))
    assert not ar.QuietHours(enabled=True, start="08:00", end="08:00").active_at(NOON)


def test_quiet_hours_hold_back_everything_below_extreme() -> None:
    c = ar.AlertChoices(quiet=ar.QuietHours(enabled=True))
    held = ar.decide(alert("Tornado Warning", "Severe", "Immediate"), "p", c, NIGHT)
    assert held.hidden and held.reason == "quiet hours"
    assert not ar.decide(alert("Tornado Warning", "Severe"), "p", c, NOON).hidden


def test_extreme_breaks_through_quiet_hours_unless_turned_off() -> None:
    extreme = alert("Tornado Warning", "Extreme", "Immediate")
    c = ar.AlertChoices(quiet=ar.QuietHours(enabled=True))
    assert not ar.decide(extreme, "p", c, NIGHT).hidden
    c.quiet.extreme_breaks_through = False
    assert ar.decide(extreme, "p", c, NIGHT).hidden
    assert "Nothing breaks through" in text.describe_choices(c, 2)


# -- place overrides ----------------------------------------------------------------


def test_a_place_can_have_its_own_choices() -> None:
    c = ar.AlertChoices(places={"work": ar.RuleSet(ar.Selection("essentials"))})
    advisory = alert("Heat Advisory")
    assert not ar.decide(advisory, "home", c).hidden
    assert ar.decide(advisory, "work", c).hidden


def test_place_on_off_keeps_the_place_and_new_places_are_watched() -> None:
    config = monitor.MonitorConfig(muted_ids=["work"])
    assert config.places_to_watch(["home", "work", "cabin"]) == ["home", "cabin"]
    assert monitor.MonitorConfig().places_to_watch(["home", "work"]) == ["home", "work"]


def test_muted_ids_round_trip(tmp_path: Path) -> None:
    monitor.save_config(tmp_path, monitor.MonitorConfig(muted_ids=["work"]))
    assert monitor.load_config(tmp_path).muted_ids == ["work"]
    assert monitor.load_config(tmp_path / "missing").muted_ids == []


# -- nothing is lost: the plan reports what was held back ---------------------------


def test_plan_poll_reports_hidden_and_speaks_only_what_is_selected() -> None:
    c = ar.AlertChoices(general=ar.RuleSet(ar.Selection("essentials")))
    state = monitor.MonitorState()
    current = [alert("Tornado Warning", "Severe", "Immediate", "t"), alert("Heat Advisory", i="h")]
    plan_poll(monitor.apply_poll(state, []), [], state, "p", c, NOON)
    update = monitor.apply_poll(state, current)
    plan = plan_poll(update, current, state, "p", c, NOON)
    assert [d.alert.id for d in plan.speak] == ["t"]
    assert plan.interrupt
    assert [d.alert.id for d in plan.hidden] == ["h"]
    assert hidden_ids(current, "p", c, NOON) == {"h"}


def test_all_clear_only_for_alerts_the_user_was_told_about() -> None:
    c = ar.AlertChoices(general=ar.RuleSet(ar.Selection("essentials")))
    state = monitor.MonitorState()
    only_hidden = [alert("Heat Advisory", i="h")]
    plan_poll(monitor.apply_poll(state, only_hidden), only_hidden, state, "p", c, NOON)
    gone = monitor.apply_poll(state, [])
    assert plan_poll(gone, [], state, "p", c, NOON).cleared is False
    told = [alert("Tornado Warning", "Severe", "Immediate", "t")]
    plan_poll(monitor.apply_poll(state, told), told, state, "p", c, NOON)
    gone = monitor.apply_poll(state, [])
    assert plan_poll(gone, [], state, "p", c, NOON).cleared is True


def test_start_summary_mentions_hidden_alerts() -> None:
    line = monitor.start_summary_multi({"Home": 1}, monitor.MonitorConfig(), hidden=2)
    assert "2 alerts hidden by your settings" in line


# -- sentences ------------------------------------------------------------------------


def test_save_sentence_for_essentials() -> None:
    c = ar.AlertChoices(general=ar.RuleSet(ar.Selection("essentials")))
    assert text.describe_choices(c, 3) == (
        "Watching 3 places. Telling you about tornado, severe thunderstorm and flash flood "
        "warnings, and anything Extreme."
    )


def test_preview_sentence_for_hidden_and_told() -> None:
    c = ar.AlertChoices(general=ar.RuleSet(ar.Selection("essentials")))
    told = ar.decide(alert("Tornado Warning", "Extreme", "Immediate"), "p", c)
    assert "interrupting your screen reader" in text.describe_decision(told, "Home")
    hidden = ar.decide(alert("Heat Advisory"), "p", c)
    sentence = text.describe_decision(hidden, "Home")
    assert "would not be spoken" in sentence and "still appear in the alert list" in sentence


# -- persistence ------------------------------------------------------------------------


def test_round_trip(tmp_path: Path) -> None:
    clause = ar.Clause(categories=["Wind"], kinds=["Warning"])
    c = ar.AlertChoices(
        general=ar.RuleSet(ar.Selection("custom", clause), ar.Delivery.SOUND),
        places={"work": ar.RuleSet(ar.Selection("safety"))},
        quiet=ar.QuietHours(enabled=True, start="21:30", end="06:15", extreme_breaks_through=False),
        extreme_always=False,
        sounds={"Extreme": "C:/sounds/loud.wav"},
    )
    store.save_choices(tmp_path, c)
    assert store.load_choices(tmp_path) == c


def test_missing_file_is_the_default_and_damaged_file_is_kept_aside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert store.load_choices(tmp_path).is_default()
    kept: list[str] = []
    monkeypatch.setattr(
        "quill.core.migration_backup.backup_corrupt_file", lambda name, path: kept.append(name)
    )
    store.store_path(tmp_path).write_text("[1, 2", encoding="utf-8")
    assert store.load_choices(tmp_path).is_default()
    assert kept == ["weather_alert_choices"]


def test_bad_values_fall_back_to_the_safe_defaults() -> None:
    c = store.from_json({
        "general": {"preset": "nonsense", "delivery": "loud"},
        "quiet": {"enabled": True, "start": "99:99"},
        "extreme_always": "yes",
    })
    assert c.general.selection.preset == "everything"
    assert c.general.delivery is ar.Delivery.AUTO
    assert c.quiet.start == "22:00"
    assert c.extreme_always is True
