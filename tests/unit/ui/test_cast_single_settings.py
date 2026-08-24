"""Quick Actions can reach a single control at last (list.md 5.7).

Cast's ``show_settings`` quick action opens the whole per-show dialog: two
dozen controls, of which somebody wanted one. Earshot's equivalents open the
download-count, queue-age and speed editors *directly*, with focus landing on
the adjustable control. For a setting somebody changes often, the difference is
a dialog and several Tab presses every single time -- which is the difference
between a feature being used and being known about.

Three things are pinned here, and they are the three that make it worth having:

* the editor opens on the value **actually in force**, inherited default and
  all -- an editor that opens on a blank misreports the setting it exists to
  change;
* writing one setting **cannot reset another**, which is what
  ``apply_show_override`` is for; and
* the confirmation is **words**, not the number that was just typed in.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.podcasts import single_settings as ss
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import single_setting_actions as actions


class _Host:
    """The manager's contract, as much of it as these actions touch."""

    def __init__(self, library: PodcastLibrary) -> None:
        self._library = library
        self.dialog = None
        self.said: list[str] = []
        self.changed = 0
        self.opened: list[tuple[ss.SingleSetting, dict[str, Any]]] = []
        self.answer: float | None = None

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _on_library_changed(self) -> None:
        self.changed += 1


@pytest.fixture
def show_and_host(monkeypatch: Any) -> tuple[PodcastShow, _Host]:
    show = PodcastShow(id="s", title="A Show", feed_url="https://e/f.xml", episodes=[])
    library = PodcastLibrary(shows=[show])
    host = _Host(library)

    def _fake_open(
        _host: Any, _show: Any, setting: ss.SingleSetting, **kwargs: Any
    ) -> float | None:
        host.opened.append((setting, kwargs))
        return host.answer

    monkeypatch.setattr(actions, "_open", _fake_open)
    return show, host


# -- what the editor opens on ---------------------------------------------------


def test_the_editor_opens_on_the_value_in_force_not_on_a_blank(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """A show with no override of its own inherits the library default."""
    show, host = show_and_host
    host._library.settings.queue_age_limit_days = 14

    actions.edit_queue_age(host, show)

    assert host.opened[0][1]["value"] == 14.0


def test_keep_all_opens_on_zero_rather_than_on_the_unused_count(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """``retention_count`` is 5 by default and means nothing while the rule
    says keep-all. Showing 5 would claim a limit that is not in force."""
    show, host = show_and_host

    actions.edit_keep_episodes(host, show)

    assert host.opened[0][1]["value"] == 0.0


def test_the_speed_editor_opens_on_the_shows_own_speed(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    show, host = show_and_host
    host._library.apply_show_override(show, speed=1.5)

    actions.edit_playback_speed(host, show)

    assert host.opened[0][1]["value"] == 1.5


# -- what it writes -------------------------------------------------------------


def test_a_count_sets_the_rule_as_well_as_the_number(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """A count on its own does nothing while the rule says keep-all, and a
    listener who set 5 and saw nothing deleted would reasonably conclude the
    setting is broken."""
    show, host = show_and_host
    host.answer = 5.0

    actions.edit_keep_episodes(host, show)

    settings = host._library.effective_settings(show)
    assert settings.retention == "keep_last_n"
    assert settings.retention_count == 5


def test_zero_means_keep_everything(show_and_host: tuple[PodcastShow, _Host]) -> None:
    """Zero reads as "none" to anybody who has met a limit field before, and
    means the opposite here -- which is why it is said back in words."""
    show, host = show_and_host
    host._library.apply_show_override(show, retention="keep_last_n", retention_count=3)
    host.answer = 0.0

    actions.edit_keep_episodes(host, show)

    assert host._library.effective_settings(show).retention == "keep_all"
    assert "every downloaded episode" in host.said[-1]


def test_setting_one_thing_does_not_reset_another(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """The reason every write goes through apply_show_override: it clones the
    show's effective settings and changes one field. A dataclass built fresh
    here would silently return every sibling override to its class default."""
    show, host = show_and_host
    host._library.apply_show_override(show, speed=1.75, queue_age_limit_days=9)
    host.answer = 4.0

    actions.edit_keep_episodes(host, show)

    settings = host._library.effective_settings(show)
    assert settings.speed == 1.75
    assert settings.queue_age_limit_days == 9
    assert settings.retention_count == 4


def test_a_speed_outside_the_range_is_clamped_rather_than_stored(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """Clamped in the action as well as bounded by the control, so a value
    that arrived some other way cannot write a speed nothing can play."""
    from quill.core.podcasts.models_settings import SPEED_MAX, SPEED_MIN

    show, host = show_and_host
    host.answer = 99.0

    actions.edit_playback_speed(host, show)

    assert host._library.effective_settings(show).speed == SPEED_MAX

    host.answer = 0.01
    actions.edit_playback_speed(host, show)

    assert host._library.effective_settings(show).speed == SPEED_MIN


def test_the_speed_editor_offers_the_range_the_rest_of_the_app_does(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """A dialog that stopped short would refuse a speed Cast accepts, and send
    somebody to the full settings window for it."""
    from quill.core.podcasts.models_settings import SPEED_MAX, SPEED_MIN

    show, host = show_and_host
    actions.edit_playback_speed(host, show)
    _setting, kwargs = host.opened[0]

    assert kwargs["minimum"] == SPEED_MIN
    assert kwargs["maximum"] == SPEED_MAX


def test_cancelling_changes_nothing(show_and_host: tuple[PodcastShow, _Host]) -> None:
    show, host = show_and_host
    host.answer = None

    actions.edit_queue_age(host, show)
    actions.edit_keep_episodes(host, show)
    actions.edit_playback_speed(host, show)

    assert show.settings is None
    assert host.changed == 0
    assert host.said == []


def test_a_saved_change_tells_the_library_to_write_itself(
    show_and_host: tuple[PodcastShow, _Host],
) -> None:
    """Otherwise the setting is right until the app closes."""
    show, host = show_and_host
    host.answer = 7.0

    actions.edit_queue_age(host, show)

    assert host.changed == 1


# -- what it says ---------------------------------------------------------------


def test_the_confirmation_is_a_sentence_not_the_number_typed_in() -> None:
    assert ss.describe_keep(5) == "Keeping the 5 newest downloaded episodes."
    assert ss.describe_keep(1) == "Keeping the 1 newest downloaded episode."
    assert "every downloaded episode" in ss.describe_keep(0)


def test_the_queue_expiry_sentence_names_what_it_does_not_do() -> None:
    """Dropping out of the queue is not deleting, and somebody who thinks it
    is will not use the setting at all."""
    setting = ss.setting(ss.QUEUE_AGE)
    assert setting is not None

    assert "does not delete" in setting.help
    assert ss.describe_queue_age(1).endswith("after 1 day.")
    assert "indefinitely" in ss.describe_queue_age(0)


def test_normal_speed_reads_as_normal_speed() -> None:
    """ "1.0 times speed" is a number read aloud; "normal speed" is an answer."""
    assert ss.describe_speed(1.0) == "This podcast plays at normal speed."
    assert ss.describe_speed(1.5) == "This podcast plays at 1.5 times speed."
    assert ss.describe_speed(1.25) == "This podcast plays at 1.25 times speed."


def test_every_setting_carries_help_in_the_house_form() -> None:
    """What it does, then the misreading it prevents. The second half is the
    one that earns the sentence: each of these has a plausible wrong reading
    (zero means none; expiry means deletion; speed is global)."""
    for setting in ss.SINGLE_SETTINGS:
        assert setting.help.endswith(".")
        assert len(setting.help.split()) > 20
        assert "&" in setting.field_label, "the control needs an access key"
        assert setting.label.endswith("...")


# -- the way in -----------------------------------------------------------------


def test_all_three_are_orderable_quick_actions() -> None:
    """So somebody who adjusts speed constantly can put it first and reach it
    with one key -- which is the whole point of Quick Actions."""
    from quill.core.podcasts.quick_actions import SHOW_ACTIONS

    ids = {action.id for action in SHOW_ACTIONS}

    assert {"keep_episodes", "queue_expiry", "playback_speed"} <= ids


def test_the_show_context_menu_opens_each_one_directly() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "podcasts" / "manager_menus.py"
    ).read_text(encoding="utf-8")

    for verb in ("edit_keep_episodes", "edit_queue_age", "edit_playback_speed"):
        assert f"single_setting_actions.{verb}(" in source


def test_the_dialog_puts_focus_on_the_control() -> None:
    """The one line the whole feature rests on. Not the Save button, not the
    label: the control somebody came here to change."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "quill"
        / "ui"
        / "podcasts"
        / "single_setting_dialog.py"
    ).read_text(encoding="utf-8")

    assert "wx.CallAfter(self._ctrl.SetFocus)" in source
