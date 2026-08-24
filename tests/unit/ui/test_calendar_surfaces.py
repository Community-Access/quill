"""The calendar's verbs and the reminder timer (6.4, 6.6, 6.7, 7.5).

The window itself is thin on purpose -- which verbs a row has, and how they
read, is pure and pinned in tests/unit/core/radio/test_calendar_actions.py.
What is here is the part that acts:

* **A verb that cannot finish says why and changes nothing.** Every one of them
  can meet a schedule that moved on -- a programme with no channel, an app with
  no player -- and the answer is always a sentence rather than an exception.
* **Play tunes in to the channel, and says which.** A live stream has one thing
  on it at a time; playing Thursday's programme on Tuesday is not something the
  medium can do, and pretending otherwise is how somebody records silence.
* **Quiet hours hold a reminder back without ending it.** A withheld reminder
  stays due, because marking it fired would be the app deciding the quiet
  window was the answer.
* **A reminder fires once.**
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio import calendar_actions
from quill.core.radio.ics import CalendarEvent

wx = pytest.importorskip("wx")

from quill.ui.radio import calendar_verbs  # noqa: E402
from quill.ui.radio.reminder_monitor import ReminderMonitor  # noqa: E402

NOW = datetime(2026, 8, 26, 18, 0, tzinfo=UTC)
SHOWTIME = datetime(2026, 8, 26, 19, 0, tzinfo=UTC)


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)


def _event(stream: str = "ACB Media 4", *, summary: str = "Main Menu") -> CalendarEvent:
    return CalendarEvent(
        uid="uid-1",
        summary=summary,
        start=SHOWTIME,
        end=SHOWTIME + timedelta(hours=1),
        categories=(stream,) if stream else (),
        description="Tech news.",
    )


class _Controller:
    def __init__(self) -> None:
        self.played: list[Any] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station)


class _Host:
    def __init__(self, *, controller: Any = None, queue: bool = False) -> None:
        self.said: list[str] = []
        self.copied: list[str] = []
        self.boxes: list[tuple[str, str]] = []
        self._radio_controller = controller
        if queue:
            self.queued: list[Any] = []
            self.radio_add_to_queue = self.queued.append

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _copy_text(self, text: str) -> None:
        self.copied.append(text)

    def _show_message_box(self, body: str, caption: str) -> None:
        self.boxes.append((caption, body))


class _Window:
    def __init__(self) -> None:
        self.dialog = None
        self.synced = 0

    def _sync(self) -> None:
        self.synced += 1


# -- play ------------------------------------------------------------------------


def test_play_tunes_in_to_the_channel() -> None:
    host, window = _Host(controller=_Controller()), _Window()

    calendar_verbs.run(host, window, calendar_actions.PLAY, _event())

    assert [s.name for s in host._radio_controller.played] == ["ACB Media 4"]


def test_play_says_the_programme_is_not_on_yet() -> None:
    """A live stream has one thing on it at a time. Saying which is the
    difference between tuning in and thinking you started a show."""
    host, window = _Host(controller=_Controller()), _Window()

    calendar_verbs.run(host, window, calendar_actions.PLAY, _event())

    assert "not on yet" in host.said[-1]
    assert "7:00 PM" in host.said[-1] or "PM" in host.said[-1]


def test_play_refuses_a_programme_with_no_channel() -> None:
    host, window = _Host(controller=_Controller()), _Window()

    calendar_verbs.run(host, window, calendar_actions.PLAY, _event(stream=""))

    assert host._radio_controller.played == []
    assert "does not say which channel" in host.said[-1]


def test_play_without_a_player_says_so_rather_than_crashing() -> None:
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.PLAY, _event())

    assert "Nothing here can play that" in host.said[-1]


# -- queue -----------------------------------------------------------------------


def test_queue_adds_the_channel_and_says_it_is_a_channel() -> None:
    """Somebody who thought they had queued Thursday's programme would find
    out at the worst possible moment."""
    host, window = _Host(queue=True), _Window()

    calendar_verbs.run(host, window, calendar_actions.QUEUE, _event())

    assert [s.name for s in host.queued] == ["ACB Media 4"]
    assert "whatever is on when the queue reaches it" in host.said[-1]


def test_queue_without_a_queue_says_so() -> None:
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.QUEUE, _event())

    assert "no play queue" in host.said[-1]


# -- copy and details ------------------------------------------------------------


def test_copy_details_carries_what_when_and_where() -> None:
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.COPY, _event())

    text = host.copied[0]
    assert "Main Menu" in text
    assert "ACB Media 4" in text
    assert "Tech news." in text


def test_show_notes_opens_a_read_only_box() -> None:
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.DETAILS, _event())

    assert host.boxes and host.boxes[0][0] == "Main Menu"


# -- reminders -------------------------------------------------------------------


def test_removing_a_reminder_that_is_not_there_says_so(tmp_path) -> None:
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.UNREMIND, _event())

    assert "no reminder on that" in host.said[-1]


def test_removing_a_reminder_removes_it(tmp_path) -> None:
    from quill.core.radio import reminders

    reminders.add_reminder(
        tmp_path, "Main Menu", SHOWTIME, kind=reminders.KIND_EVENT, target="uid-1"
    )
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.UNREMIND, _event())

    assert reminders.load_reminders(tmp_path) == []
    assert window.synced == 1


def test_a_verb_that_raises_is_reported_not_propagated(monkeypatch) -> None:
    """A menu that dies on a click is worse than one that says it could not."""

    def _boom(*_args, **_kwargs):
        raise RuntimeError("the schedule moved")

    monkeypatch.setattr(calendar_verbs, "_copy", _boom)
    host, window = _Host(), _Window()

    calendar_verbs.run(host, window, calendar_actions.COPY, _event())

    assert "could not be done" in host.said[-1]
    assert "the schedule moved" in host.said[-1]


# -- the reminder timer ----------------------------------------------------------


def _monitor(frame, said: list[str]) -> ReminderMonitor:
    return ReminderMonitor(frame, announce=said.append, wx=wx)


def test_a_due_reminder_is_announced_once(frame, tmp_path, monkeypatch) -> None:
    from quill.core.radio import reminders

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind, **_k: False)
    reminders.add_reminder(tmp_path, "Main Menu", SHOWTIME, target="uid-1")
    said: list[str] = []
    monitor = _monitor(frame, said)

    assert monitor.check_now(now=SHOWTIME) == 1
    assert "Main Menu" in said[0]

    assert monitor.check_now(now=SHOWTIME) == 0, "a reminder that repeats is an alarm"
    monitor.stop()


def test_nothing_due_is_silent(frame, tmp_path, monkeypatch) -> None:
    from quill.core.radio import reminders

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind, **_k: False)
    reminders.add_reminder(tmp_path, "Main Menu", SHOWTIME, target="uid-1")
    said: list[str] = []
    monitor = _monitor(frame, said)

    assert monitor.check_now(now=NOW) == 0
    assert said == []
    monitor.stop()


def test_quiet_hours_hold_a_reminder_without_ending_it(frame, tmp_path, monkeypatch) -> None:
    """Marking it fired would be the app deciding the quiet window was the
    answer. It stays due, and the Upcoming window still shows it."""
    from quill.core.quiet_hours import Kind
    from quill.core.radio import reminders

    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.quiet_hours_ui.held_back", lambda kind, **_k: asked.append(kind) or True
    )
    reminders.add_reminder(tmp_path, "Main Menu", SHOWTIME, target="uid-1")
    said: list[str] = []
    monitor = _monitor(frame, said)

    assert monitor.check_now(now=SHOWTIME) == 0
    assert said == []
    assert asked == [Kind.REMINDER], "as a reminder, not as generic background news"
    assert reminders.load_reminders(tmp_path)[0].is_done is False
    monitor.stop()


def test_a_reminder_held_back_speaks_when_the_quiet_window_ends(
    frame, tmp_path, monkeypatch
) -> None:
    from quill.core.radio import reminders

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind, **_k: True)
    reminders.add_reminder(tmp_path, "Main Menu", SHOWTIME, target="uid-1")
    said: list[str] = []
    monitor = _monitor(frame, said)
    monitor.check_now(now=SHOWTIME)

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind, **_k: False)
    assert monitor.check_now(now=SHOWTIME + timedelta(minutes=5)) == 1
    monitor.stop()


def test_an_unreadable_quiet_window_lets_the_reminder_through(frame, tmp_path, monkeypatch) -> None:
    """Silence is the wrong default for the one thing somebody asked to be
    interrupted by."""
    from quill.core.radio import reminders

    def _boom(_kind, **_k):
        raise RuntimeError("the quiet-hours file is unreadable")

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", _boom)
    reminders.add_reminder(tmp_path, "Main Menu", SHOWTIME, target="uid-1")
    said: list[str] = []
    monitor = _monitor(frame, said)

    assert monitor.check_now(now=SHOWTIME) == 1
    monitor.stop()


def test_a_broken_store_never_takes_the_app_down(frame, tmp_path, monkeypatch) -> None:
    from quill.core.radio import reminders

    monkeypatch.setattr(
        reminders, "load_reminders", lambda _dir: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monitor = _monitor(frame, [])

    assert monitor.check_now(now=SHOWTIME) == 0
    monitor.stop()


def test_the_timer_stops_cleanly(frame) -> None:
    monitor = _monitor(frame, [])
    monitor.start()
    monitor.stop()
    monitor.stop(), "stopping twice must not raise"


# -- what is on now --------------------------------------------------------------


def test_the_on_now_key_answers_without_opening_anything(monkeypatch) -> None:
    from quill.core.radio import acb_calendar
    from quill.ui.radio import calendar_wiring

    on_air = CalendarEvent(
        uid="x",
        summary="Main Menu",
        start=NOW - timedelta(minutes=10),
        end=NOW + timedelta(minutes=50),
        categories=("ACB Media 1",),
    )
    monkeypatch.setattr(acb_calendar, "fetch_schedule", lambda **_k: ([on_air], None))
    monkeypatch.setattr(
        "quill.ui.radio.calendar_wiring.datetime",
        SimpleNamespace(now=lambda _tz=None: NOW),
        raising=False,
    )
    host = _Host()

    calendar_wiring.announce_on_now(host)

    assert "Main Menu" in host.said[-1]
    assert "ACB Media 1" in host.said[-1]


def test_the_on_now_key_says_something_when_nothing_is_on(monkeypatch) -> None:
    """A key that answers with silence is a key somebody presses twice."""
    from quill.core.radio import acb_calendar
    from quill.ui.radio import calendar_wiring

    monkeypatch.setattr(acb_calendar, "fetch_schedule", lambda **_k: ([], None))
    host = _Host()

    calendar_wiring.announce_on_now(host)

    assert host.said[-1] == calendar_actions.nothing_on_now()


def test_a_high_priority_reminder_comes_through_quiet_hours(frame, tmp_path, monkeypatch) -> None:
    """7.3: the per-reminder choice has to work on its own, or it does nothing
    for the only person who would reach for it -- somebody who did *not* want
    every reminder through."""
    from quill.core.radio import reminders

    seen: list[bool] = []

    def _held(_kind, *, high_priority: bool = False, **_k):
        seen.append(high_priority)
        return not high_priority  # quiet hours are on; only the urgent escapes

    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", _held)
    reminders.add_reminder(
        tmp_path, "Board meeting", SHOWTIME, target="a", priority=reminders.PRIORITY_HIGH
    )
    reminders.add_reminder(tmp_path, "Main Menu", SHOWTIME, target="b")
    said: list[str] = []
    monitor = _monitor(frame, said)

    assert monitor.check_now(now=SHOWTIME) == 1
    assert said and "Board meeting" in said[0]
    assert seen == [True, False], "the priority reaches quiet hours per reminder"
    monitor.stop()
