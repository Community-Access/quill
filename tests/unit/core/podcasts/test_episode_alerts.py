"""Whether to check a feed, how often, and what to say when something arrives.

The three questions 3.1.0 made answerable per podcast as well as globally. Two
of these tests exist because of bugs made building it, and both are the kind
that would have shipped silently:

* **A per-show interval of 0 is an opt-out, not a cadence.** The first version
  reused the same field for "is it time yet", so the shipped default (global 0)
  made the worker refuse *every* show -- an automatic check that never checked
  anything, with nothing to see in any log.
* **An opt-out is only read against a global yes.** Comparing a show's resolved
  interval to the *effective* cadence rather than the library's own global made
  every show look opted out the moment the legacy Radio setting supplied the
  cadence instead.

The alert defaults are asserted too: quiet, and a typo falling back to quiet
rather than to noise, because the safe direction for an alert is always the
quieter one.
"""

from __future__ import annotations

from quill.core.podcasts import episode_alerts as ea
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_settings import PodcastSettings


def _show(show_id: str, *, feed: str = "https://example.com/f.xml", paused: bool = False):
    return PodcastShow(id=show_id, title=show_id, feed_url=feed, paused=paused)


def _resolver(mapping: dict[str, PodcastSettings], default: PodcastSettings):
    return lambda show: mapping.get(show.id, default)


# -- the alert modes ---------------------------------------------------------


def test_quiet_is_the_shipped_answer() -> None:
    """An app that starts putting toasts over a document has decided for you."""
    assert ea.ALERT_DEFAULT == ea.ALERT_QUIET
    assert PodcastSettings().new_episode_alert == ea.ALERT_QUIET


def test_a_stored_typo_falls_back_to_quiet_not_to_noise() -> None:
    assert ea.normalize_alert("shout") == ea.ALERT_QUIET
    assert ea.normalize_alert(None) == ea.ALERT_QUIET
    assert ea.normalize_alert("") == ea.ALERT_QUIET


def test_quiet_records_but_never_interrupts() -> None:
    """The mode that makes a busy show bearable."""
    assert ea.wants_list_entry(ea.ALERT_QUIET) is True
    assert ea.wants_desktop_notice(ea.ALERT_QUIET) is False
    assert ea.plays_sound(ea.ALERT_QUIET) is False


def test_off_records_nothing_at_all() -> None:
    assert ea.wants_list_entry(ea.ALERT_OFF) is False
    assert ea.wants_desktop_notice(ea.ALERT_OFF) is False


def test_on_does_all_three() -> None:
    assert ea.wants_list_entry(ea.ALERT_ON) is True
    assert ea.wants_desktop_notice(ea.ALERT_ON) is True
    assert ea.plays_sound(ea.ALERT_ON) is True


def test_sound_and_notice_always_agree() -> None:
    """ "Quiet" that still made a noise would be a lie."""
    for mode in (ea.ALERT_ON, ea.ALERT_QUIET, ea.ALERT_OFF):
        assert ea.plays_sound(mode) == ea.wants_desktop_notice(mode)


def test_every_mode_reads_back_as_words() -> None:
    for value, _label in ea.ALERT_CHOICES:
        assert ea.describe_alert(value)


# -- which shows an automatic check asks about -------------------------------


def test_the_default_library_still_checks_its_shows() -> None:
    """The bug: a per-show 0 was read as a cadence, so the shipped default
    (global 0) refused every show and nothing was ever checked."""
    shows = [_show("a"), _show("b")]
    resolve = _resolver({}, PodcastSettings())  # every interval is the default 0
    assert len(ea.shows_worth_checking(shows, resolve, global_minutes=0)) == 2


def test_a_show_set_to_never_is_skipped_when_the_global_says_yes() -> None:
    """ "Hourly, except this one" -- the thing per-podcast intervals are for."""
    shows = [_show("a"), _show("never")]
    resolve = _resolver(
        {"never": PodcastSettings(check_interval_minutes=0)},
        PodcastSettings(check_interval_minutes=60),
    )
    kept = ea.shows_worth_checking(shows, resolve, global_minutes=60)
    assert [s.id for s in kept] == ["a"]


def test_a_show_with_its_own_longer_cadence_is_still_checked() -> None:
    shows = [_show("daily"), _show("weekly")]
    resolve = _resolver(
        {"weekly": PodcastSettings(check_interval_minutes=1440)},
        PodcastSettings(check_interval_minutes=60),
    )
    assert len(ea.shows_worth_checking(shows, resolve, global_minutes=60)) == 2


def test_a_paused_show_is_left_alone() -> None:
    shows = [_show("a"), _show("resting", paused=True)]
    resolve = _resolver({}, PodcastSettings(check_interval_minutes=60))
    kept = ea.shows_worth_checking(shows, resolve, global_minutes=60)
    assert [s.id for s in kept] == ["a"]


def test_a_forced_check_reaches_everything() -> None:
    """Refresh on a row ignores every switch: one that could strand a show
    would be a trap rather than a preference."""
    shows = [_show("a"), _show("resting", paused=True), _show("never")]
    resolve = _resolver(
        {"never": PodcastSettings(check_interval_minutes=0)},
        PodcastSettings(check_interval_minutes=60),
    )
    kept = ea.shows_worth_checking(shows, resolve, force=True, global_minutes=60)
    assert len(kept) == 3


def test_a_show_with_no_feed_is_never_asked() -> None:
    """A local or imported show has nothing to ask -- even forced."""
    shows = [_show("local", feed="")]
    resolve = _resolver({}, PodcastSettings(check_interval_minutes=60))
    assert ea.shows_worth_checking(shows, resolve, force=True, global_minutes=60) == []


def test_unresolvable_settings_leave_a_show_alone() -> None:
    def _boom(_show):
        raise RuntimeError("settings chain is broken")

    assert ea.shows_worth_checking([_show("a")], _boom, global_minutes=60) == []


# -- is there anything to do at all ------------------------------------------


def test_nothing_subscribed_means_nothing_to_check() -> None:
    """The timer asks before it reaches the network: an app that wakes up to do
    nothing is still an app that woke up."""
    assert ea.anything_to_check([], _resolver({}, PodcastSettings())) is False


def test_everything_set_to_never_means_nothing_to_check() -> None:
    shows = [_show("a"), _show("b")]
    resolve = _resolver(
        {
            "a": PodcastSettings(check_interval_minutes=0),
            "b": PodcastSettings(check_interval_minutes=0),
        },
        PodcastSettings(check_interval_minutes=60),
    )
    assert ea.anything_to_check(shows, resolve, global_minutes=60) is False


def test_one_live_subscription_is_enough() -> None:
    shows = [_show("a"), _show("b")]
    resolve = _resolver(
        {"b": PodcastSettings(check_interval_minutes=0)},
        PodcastSettings(check_interval_minutes=60),
    )
    assert ea.anything_to_check(shows, resolve, global_minutes=60) is True


# -- the interval ------------------------------------------------------------


def test_the_interval_is_clamped_not_trusted() -> None:
    """A stored value that survived a units change must not become a request
    every second."""
    from quill.core.podcasts import refresh_policy

    assert ea.interval_for_show(PodcastSettings(check_interval_minutes=1)) >= (
        refresh_policy.MIN_INTERVAL_MINUTES
    )
    assert ea.interval_for_show(PodcastSettings(check_interval_minutes=0)) == 0


def test_a_settings_record_without_the_field_reads_as_the_default() -> None:
    class Old:  # a record from before 3.1.0
        pass

    assert ea.interval_for_show(Old()) == 0
    assert ea.alert_for_show(Old()) == ea.ALERT_QUIET
