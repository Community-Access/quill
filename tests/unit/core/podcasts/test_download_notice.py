"""Telling somebody a download finished, without waking them (list.md 2.5).

Three rules, and each one is a way the feature could have been worse than
nothing:

* **Off by default**, because a desktop notification is an interruption
  somebody else chose for you. The earcon that already existed is unchanged.
* **One notice per batch, not per episode.** Forty finished downloads are
  forty completions; forty toasts is a fault with a friendly icon.
* **Through quiet hours as the ``download`` kind**, or this becomes the first
  thing in the family that wakes somebody at three in the morning -- which is
  exactly what an overnight batch would have done.

The quiet-hours half is wiring and is pinned in
tests/unit/ui/test_podcast_download_notify.py; what is here is the decision.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.podcasts import download_notice
from quill.core.podcasts.models_settings import PodcastSettings


def _settings(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**{"download_notify": True, **kwargs})


# -- off until asked for --------------------------------------------------------


def test_the_shipped_answer_is_no() -> None:
    assert PodcastSettings().download_notify is False
    assert download_notice.wants_notice(PodcastSettings()) is False


def test_a_settings_object_that_never_heard_of_it_says_no() -> None:
    """An older library file, or any other duck. Silence is the safe default."""
    assert download_notice.wants_notice(SimpleNamespace()) is False
    assert download_notice.wants_notice(None) is False


def test_nothing_is_notified_while_the_switch_is_off() -> None:
    off = _settings(download_notify=False)
    assert download_notice.should_notify(off, still_downloading=0, finished=5) is False


# -- one notice per batch -------------------------------------------------------


def test_a_batch_still_running_says_nothing_yet() -> None:
    """Thirty-nine of forty landing is not news; the fortieth is."""
    assert download_notice.should_notify(_settings(), still_downloading=1, finished=39) is False


def test_the_queue_going_quiet_is_the_moment() -> None:
    assert download_notice.should_notify(_settings(), still_downloading=0, finished=40) is True


def test_a_quiet_queue_with_nothing_finished_says_nothing() -> None:
    assert download_notice.should_notify(_settings(), still_downloading=0, finished=0) is False


# -- what it says ---------------------------------------------------------------


def test_one_episode_is_named_because_the_name_is_the_news() -> None:
    said = download_notice.notice(1, "Episode 412", "Main Menu")
    assert "Episode 412" in said
    assert "Main Menu" in said


def test_one_episode_from_a_show_with_no_title_still_names_the_episode() -> None:
    assert download_notice.notice(1, "Episode 412", "") == "Downloaded Episode 412."


def test_an_episode_with_no_title_at_all_still_says_something_true() -> None:
    assert download_notice.notice(1) == "One episode finished downloading."


def test_several_are_counted_rather_than_listed() -> None:
    """A list of forty titles in a toast is a list nobody reads, and one a
    screen reader has to be interrupted to escape."""
    said = download_notice.notice(40, "Episode 412", "Main Menu")
    assert said == "40 episodes finished downloading."
    assert "Episode 412" not in said


def test_a_nonsense_count_never_produces_a_nonsense_sentence() -> None:
    assert download_notice.notice(-3) == "0 episodes finished downloading."


def test_the_notice_names_the_app_it_came_from() -> None:
    """A toast with no source is a toast somebody has to go and identify."""
    assert download_notice.TITLE == "QUILL Cast"


# -- it survives a save ---------------------------------------------------------


def test_the_setting_round_trips() -> None:
    settings = PodcastSettings()
    settings.download_notify = True
    assert PodcastSettings.from_dict(settings.to_dict()).download_notify is True


def test_an_older_library_file_reads_as_off() -> None:
    data = PodcastSettings().to_dict()
    data.pop("download_notify", None)
    assert PodcastSettings.from_dict(data).download_notify is False
