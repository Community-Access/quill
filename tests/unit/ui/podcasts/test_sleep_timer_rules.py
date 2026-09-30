"""Sleep timer: reset on use, cancel on switch (ear.md R22).

Both off by default, because each is a behaviour somebody either wants or finds
maddening. The asymmetry in what they *say* is the interesting part: resetting is
silent and cancelling speaks.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastSettings
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.queue_commands import sleep_timer_episode_changed, sleep_timer_keep_awake


class _Timer:
    def __init__(self, active: bool = True) -> None:
        self.is_active = active
        self.restarts = 0
        self.cancels = 0

    def restart(self) -> bool:
        self.restarts += 1
        return True

    def cancel(self) -> None:
        self.cancels += 1


class _Host:
    def __init__(self, *, active: bool = True, reset: bool = False, switch: bool = False) -> None:
        self._sleep_timer_controller = _Timer(active)
        self._podcast_library = PodcastLibrary()
        self._podcast_library.settings = PodcastSettings(
            sleep_timer_reset_on_use=reset, sleep_timer_cancel_on_switch=switch
        )
        self.said: list[str] = []

    def _announce(self, text: str, sound: object = None) -> None:
        self.said.append(text)


def test_reset_is_off_by_default() -> None:
    host = _Host()
    sleep_timer_keep_awake(host)
    assert host._sleep_timer_controller.restarts == 0


def test_reset_restarts_the_countdown_when_switched_on() -> None:
    host = _Host(reset=True)
    sleep_timer_keep_awake(host)
    assert host._sleep_timer_controller.restarts == 1


def test_reset_says_nothing() -> None:
    """Announcing it would be a sentence over the episode every fifteen seconds."""
    host = _Host(reset=True)
    sleep_timer_keep_awake(host)
    assert host.said == []


def test_nothing_happens_when_no_timer_is_running() -> None:
    host = _Host(active=False, reset=True)
    sleep_timer_keep_awake(host)
    assert host._sleep_timer_controller.restarts == 0


def test_cancel_on_switch_is_off_by_default() -> None:
    host = _Host()
    sleep_timer_episode_changed(host)
    assert host._sleep_timer_controller.cancels == 0


def test_cancel_on_switch_clears_the_timer_and_says_why() -> None:
    """Unlike the reset, this one speaks: a timer that vanished without a word is
    a timer the listener will assume is still running."""
    host = _Host(switch=True)
    sleep_timer_episode_changed(host)
    assert host._sleep_timer_controller.cancels == 1
    assert "Sleep timer cancelled" in host.said[0]


def test_neither_hook_needs_a_timer_to_exist() -> None:
    class _Bare:
        said: list[str] = []

        def _announce(self, text, sound=None):
            self.said.append(text)

    bare = _Bare()
    sleep_timer_keep_awake(bare)
    sleep_timer_episode_changed(bare)
    assert bare.said == []
