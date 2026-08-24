"""The finished-download notification, wired (list.md 2.5).

The decision is pure and pinned in
tests/unit/core/podcasts/test_download_notice.py. What is here is the part that
could still be wrong with a correct decision behind it: that the completion
handler counts across the batch and resets, that quiet hours are consulted
**after** the batch check rather than instead of it, and that the notice is
shown through the one shared toast rather than a third hand-rolled copy of
``wx.adv.NotificationMessage``.

The quiet-hours leg is the one worth stating twice: this is the first thing in
the family that an overnight batch could use to wake somebody at three in the
morning, and it is the reason ``Kind.DOWNLOAD`` exists.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.podcasts import download_notice
from quill.core.podcasts.models_settings import PodcastSettings

REPO = Path(__file__).resolve().parents[3]


class _Show:
    def __init__(self) -> None:
        self.id = "show-1"
        self.title = "Main Menu"

    def find_episode(self, _guid: str) -> Any:
        return SimpleNamespace(title="Episode 412")


class _Library:
    def __init__(self, *, notify: bool) -> None:
        self.settings = PodcastSettings()
        self.settings.download_notify = notify

    def find_show(self, _show_id: str) -> Any:
        return _Show()


class _Queue:
    def __init__(self, active: int = 0) -> None:
        self.active = active

    def active_count(self) -> int:
        return self.active


class _Host:
    """The completion handler, off its frame."""

    def __init__(self, *, notify: bool = True, active: int = 0) -> None:
        from quill.ui.main_frame_podcast_transfers import PodcastTransfersMixin

        self._podcast_library = _Library(notify=notify)
        self._podcast_download_queue = _Queue(active)
        self.frame = None
        self._notify = PodcastTransfersMixin._maybe_notify_downloads_finished.__get__(self)


def _item() -> Any:
    return SimpleNamespace(show_id="show-1", episode_guid="ep1", destination="x.mp3")


@pytest.fixture
def toasts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.toast.show_toast",
        lambda title, body, **_kwargs: shown.append((title, body)) or True,
    )
    return shown


@pytest.fixture(autouse=True)
def _not_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind: False)


# -- the batch ------------------------------------------------------------------


def test_a_finished_queue_shows_one_notice(toasts) -> None:
    host = _Host()
    host._notify(_item())

    assert len(toasts) == 1
    assert toasts[0][0] == download_notice.TITLE
    assert "Episode 412" in toasts[0][1]


def test_a_batch_still_running_shows_nothing_yet(toasts) -> None:
    host = _Host(active=3)
    for _ in range(5):
        host._notify(_item())

    assert toasts == []


def test_the_count_is_the_whole_batch_and_then_resets(toasts) -> None:
    """Forty completions, one notice, counting all forty -- and the next batch
    starts from nothing rather than from forty."""
    host = _Host(active=1)
    for _ in range(39):
        host._notify(_item())
    host._podcast_download_queue.active = 0
    host._notify(_item())

    assert len(toasts) == 1
    assert toasts[0][1] == "40 episodes finished downloading."

    host._podcast_download_queue.active = 0
    host._notify(_item())
    assert len(toasts) == 2
    assert "Episode 412" in toasts[1][1], "one episode again, not forty-one"


def test_the_switch_being_off_shows_nothing(toasts) -> None:
    host = _Host(notify=False)
    host._notify(_item())

    assert toasts == []


# -- quiet hours ----------------------------------------------------------------


def test_quiet_hours_hold_the_notice_back(monkeypatch, toasts) -> None:
    """The download still happened. What is held back is the interruption."""
    from quill.core.quiet_hours import Kind

    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.quiet_hours_ui.held_back", lambda kind: asked.append(kind) or True
    )
    host = _Host()

    host._notify(_item())

    assert toasts == []
    assert asked == [Kind.DOWNLOAD], "as a download, not as generic background news"


def test_quiet_hours_are_asked_after_the_batch_check_not_instead_of_it(monkeypatch, toasts) -> None:
    """Asking first would consult quiet hours thirty-nine times a batch, and
    would make a held-back notice indistinguishable from a mid-batch one."""
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.quiet_hours_ui.held_back", lambda kind: asked.append(kind) or False
    )
    host = _Host(active=2)

    host._notify(_item())
    host._notify(_item())

    assert asked == [], "nothing to hold back while the batch is still running"
    assert toasts == []


def test_a_held_back_notice_does_not_re_announce_the_batch_later(monkeypatch, toasts) -> None:
    """The count is cleared when the batch ends, held back or not -- otherwise
    quiet hours would turn into a queue that empties in the morning."""
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind: True)
    host = _Host()
    host._notify(_item())

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind: False)
    host._notify(_item())

    assert len(toasts) == 1
    assert "Episode 412" in toasts[0][1], "the second batch, counted on its own"


# -- one toast implementation ---------------------------------------------------


def test_nothing_hand_rolls_a_notification_any_more() -> None:
    """Two copies is where the third one goes wrong; this was going to be it."""
    offenders = []
    for path in (REPO / "quill").rglob("*.py"):
        if path.name == "toast.py":
            continue
        if "NotificationMessage(" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []
