"""One run-end choice instead of two booleans (ear.md R7).

The pair could express four states, two of which meant the same thing, and could
not express the one thing people want to say -- *which* of the two should carry
on. The translation both ways is what lets the change ship without a migration.
"""

from __future__ import annotations

from quill.core.podcasts import run_end
from quill.core.podcasts.models import PodcastSettings


def test_a_fresh_record_means_carry_on_with_the_queue() -> None:
    """What auto-advance has always done, so it stays the default."""
    assert run_end.from_settings(PodcastSettings()) == "queue"
    assert run_end.default_choice() == "queue"


def test_the_old_booleans_are_still_read() -> None:
    """A settings file written before this change keeps its answer."""
    stop = PodcastSettings(continue_after_queue=False, continue_after_group=False)
    assert run_end.from_settings(stop) == "stop"

    folder = PodcastSettings(continue_after_queue=False, continue_after_group=True)
    assert run_end.from_settings(folder) == "folder"

    queue = PodcastSettings(continue_after_queue=True, continue_after_group=False)
    assert run_end.from_settings(queue) == "queue"


def test_both_old_booleans_on_reads_as_queue() -> None:
    """Which is what the old code did: the queue was tried first.

    Reading it any other way would change behaviour for somebody who never
    touched the setting.
    """
    both = PodcastSettings(continue_after_queue=True, continue_after_group=True)
    assert run_end.from_settings(both) == "queue"


def test_storing_a_choice_writes_both_shapes() -> None:
    """So an older build still reads the answer somebody gave a newer one."""
    settings = PodcastSettings()
    run_end.to_settings(settings, "folder")
    assert settings.run_end_action == "folder"
    assert settings.continue_after_queue is False
    assert settings.continue_after_group is True

    run_end.to_settings(settings, "stop")
    assert settings.continue_after_queue is False
    assert settings.continue_after_group is False


def test_the_new_field_wins_over_the_booleans_once_it_is_set() -> None:
    settings = PodcastSettings(continue_after_queue=True, continue_after_group=False)
    settings.run_end_action = "stop"
    assert run_end.from_settings(settings) == "stop"


def test_a_nonsense_choice_falls_back_to_the_default() -> None:
    settings = PodcastSettings()
    assert run_end.to_settings(settings, "explode") == "queue"
    assert run_end.from_settings(settings) == "queue"


def test_a_nonsense_stored_value_is_ignored_in_favour_of_the_booleans() -> None:
    """A settings file is somebody else's input."""
    settings = PodcastSettings(continue_after_queue=False, continue_after_group=True)
    settings.run_end_action = "sideways"
    assert run_end.from_settings(settings) == "folder"


def test_the_choice_survives_a_save_and_a_load() -> None:
    settings = PodcastSettings()
    run_end.to_settings(settings, "folder")
    restored = PodcastSettings.from_dict(settings.to_dict())
    assert run_end.from_settings(restored) == "folder"


def test_every_choice_has_a_sentence_that_says_what_it_carries_on_with() -> None:
    """ "Continue" on its own does not say *with what*."""
    for choice in run_end.CHOICES:
        sentence = run_end.describe(choice)
        assert sentence and sentence[0].isupper()
    assert "queue" in run_end.describe("queue")
    assert "folder" in run_end.describe("folder")


def test_the_default_is_offered_first() -> None:
    """A chooser whose default sits in the middle is a worse list."""
    assert run_end.CHOICES[0] == run_end.default_choice()
