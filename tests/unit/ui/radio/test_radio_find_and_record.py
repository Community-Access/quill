"""Find and Record, Quill Radio's agent task (codex.md 6.5, Phase 4c).

Two halves. The command, called for real on a real Quill Radio window, with the
agent window patched where the shared opener imports it
(``quill.ui.agent_window``). Then every tool through a real
``FamilyToolRegistry``: reads answer without a question; playing, recording and
scheduling ask with one exact sentence, and do nothing when the answer is no.
The recorder, the scheduler and the player are stand-ins for Radio's own, so
nothing records, plays or leaves the machine.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.family_tools import FamilyToolRegistry
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity
from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.ui.radio.radio_ai_task import FIND_AND_RECORD, radio_task_tools

# --------------------------------------------------------------------------- #
# The command, on a real Quill Radio window
# --------------------------------------------------------------------------- #


class _Window:
    last: dict | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).last = {"args": args, "kwargs": kwargs}

    def Show(self):  # noqa: N802 - wx API shape
        pass

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        pass

    def Bind(self, *_args: Any, **_kwargs: Any):  # noqa: N802 - wx API shape
        pass


class _Service:
    signed_in = True
    direct = True

    def __init__(self, connection: str, *, tools: bool) -> None:
        self.connection_in_use = connection
        self.tools = tools
        self.harnesses: list[str] = []

    def can_do(self, capability: str) -> bool:
        return capability != "agent_tools" or self.tools

    def needs_label(self, capability: str) -> str:
        return "" if self.can_do(capability) else "(needs Copilot or Codex)"

    def agent_harness(self, connection: str) -> object:
        self.harnesses.append(connection)
        return object()

    def capability_offer(self, capability: str) -> Any:
        from quill.core.ai.connection_caps import SwitchOffer

        return SwitchOffer(
            "Agent tasks need a connection that runs tasks. My GitHub Copilot can. "
            "Switch to it and ask?",
            target="copilot",
        )


@pytest.fixture
def agent_window(monkeypatch):
    import quill.ui.agent_window as module

    cls = type("AgentWindow", (_Window,), {"last": None})
    monkeypatch.setattr(module, "AgentWindow", cls)
    return cls


@pytest.fixture
def radio(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    monkeypatch.setattr(type(frame), "_show_ai_window", lambda self, window: None)
    frame._radio_now_playing_text = lambda: "Blue in Green by Miles Davis"
    frame._radio_controller.state.station = SimpleNamespace(
        name="KJAZZ", station_uuid="k1", stream_url="http://k.invalid/live"
    )
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        frame._radio_shutdown()


#: Builds a real Quill Radio window, which registers system-wide hotkeys.
_REAL = pytest.mark.machine_global


@_REAL
def test_on_copilot_find_and_record_opens_on_radios_tools_and_facts(
    radio, agent_window, monkeypatch
) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(radio, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(radio)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.connection == "copilot"
    assert hooks.title == "Find and Record"
    assert hooks.starter == ""
    assert "record or schedule" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is FIND_AND_RECORD
    facts = runner.context()
    assert "Station: KJAZZ" in facts
    assert "Now playing: Blue in Green by Miles Davis" in facts
    names = [tool.name for tool in runner.tools()]
    assert names == [
        "radio.find_stations",
        "radio.list_favorites",
        "radio.recent_songs",
        "radio.list_scheduled",
        "radio.play_station",
        "radio.record_station",
        "radio.schedule_recording",
    ]
    assert radio.said == []  # the reader says the window; the app says nothing


@_REAL
def test_on_a_connection_without_agent_tools_it_sends_nothing(
    radio, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(radio, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(radio)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


@_REAL
def test_safe_mode_refuses_find_and_record(radio, agent_window) -> None:
    radio._safe_mode = True

    (lambda w: w.cmd_ai_task())(radio)

    assert agent_window.last is None
    assert radio.said == ["AI is off in Safe Mode."]


@_REAL
def test_the_row_is_registered_on_ctrl_f3(radio) -> None:
    command = radio.commands.get("tools.hosted_ai_task")
    assert command is not None
    assert radio._binding_for("tools.hosted_ai_task") == "Ctrl+F3"


# --------------------------------------------------------------------------- #
# The tools, through a real registry
# --------------------------------------------------------------------------- #


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


class _Ctx:
    def __init__(self) -> None:
        self.notes: list[str] = []

    def on_ui(self, fn, default=None):
        return fn()

    def preview(self, title: str, text: str) -> bool:
        raise AssertionError("Radio's tools change no data, so they preview nothing")

    def note(self, text: str) -> None:
        self.notes.append(text)


class _Recorder:
    def __init__(self) -> None:
        self.started: list[dict] = []

    def start(self, **kwargs: Any) -> None:
        self.started.append(kwargs)


class _Scheduler:
    def __init__(self) -> None:
        self.entries: list[RecordingScheduleEntry] = []

    def add(self, entry: RecordingScheduleEntry) -> None:
        self.entries.append(entry)


class _Controller:
    def __init__(self, station: Any = None) -> None:
        self.state = SimpleNamespace(station=station)
        self.played: list[Any] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station)


class _SongLog:
    def __init__(self, songs: dict[str, list[str]]) -> None:
        self._songs = songs

    def songs_for(self, key: str) -> list[Any]:
        return [SimpleNamespace(display=lambda s=s: s) for s in self._songs.get(key, [])]

    def known_stations(self) -> list[Any]:
        return []


_WBGO = RadioStation(name="WBGO", stream_url="http://wbgo.invalid/live", tags=("jazz",))
_KCSM = RadioStation(name="KCSM Jazz 91", stream_url="http://kcsm.invalid/live", tags=("jazz",))


def _host(**extra: Any) -> SimpleNamespace:
    host = SimpleNamespace(
        _safe_mode=False,
        _radio_favorites=RadioFavoritesStore(
            favorites=[FavoriteStation(station=_WBGO, folder="Jazz")]
        ),
        _radio_history=SimpleNamespace(catalog_enabled=False),
        _radio_controller=_Controller(),
        _radio_recorder=_Recorder(),
        _radio_scheduler=_Scheduler(),
        _radio_recording_settings=RecordingSettings(),
        _radio_recording_filter_graph=lambda: "",
        _radio_recording_exact=lambda: None,
        _radio_song_log=_SongLog({"http://wbgo.invalid/live": ["So What by Miles Davis"]}),
        refreshed=[],
    )
    host._refresh_statusbar = lambda: host.refreshed.append("status")
    host._refresh_radio_wake_task = lambda: host.refreshed.append("wake")
    host._update_sleep_inhibitor = lambda: host.refreshed.append("sleep")
    for key, value in extra.items():
        setattr(host, key, value)
    return host


def _registry(host: Any, approver: _Approver, live=None) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("radio-find-and-record", RiskLevel.LOW),
        app_scope="radio",
    )
    search = live or (lambda _query, _safe: [_KCSM])
    registry.register_app("radio", radio_task_tools(host, _Ctx(), search_live=search))
    registry.gate.begin_task(approver)
    return registry


@pytest.fixture(autouse=True)
def _ffmpeg(monkeypatch):
    import quill.core.speech.ffmpeg as ffmpeg

    monkeypatch.setattr(ffmpeg, "ffmpeg_available", lambda: True)


def test_find_stations_reads_favourites_then_the_directory_as_numbered_rows() -> None:
    approver = _Approver(ApprovalChoice.DENY)
    searched: list[tuple[str, bool]] = []
    registry = _registry(
        _host(), approver, live=lambda q, safe: searched.append((q, safe)) or [_KCSM, _WBGO]
    )

    result = registry.call("radio_find_stations", {"query": "jazz"})

    assert result.ok
    lines = result.text.splitlines()
    assert lines[0] == "2 stations for jazz:"
    assert lines[1] == "S1. WBGO. jazz. in your folder Jazz."
    assert lines[2].startswith("S2. KCSM Jazz 91. jazz")
    assert searched == [("jazz", False)]
    assert approver.asked == []  # a read: no question


def test_safe_mode_searches_only_this_computers_lists() -> None:
    searched: list[str] = []
    registry = _registry(
        _host(_safe_mode=True),
        _Approver(ApprovalChoice.DENY),
        live=lambda q, _s: searched.append(q),
    )

    result = registry.call("radio_find_stations", {"query": "polka"})

    assert searched == []
    assert result.text == (
        "No stations matched polka. Only this computer's lists were searched, because of Safe Mode."
    )


def test_favourites_and_recent_songs_are_reads() -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(_host(), approver)

    favourites = registry.call("radio_list_favorites", {})
    songs = registry.call("radio_recent_songs", {"station": "F1"})

    assert favourites.text.splitlines() == [
        "1 favourite station:",
        "F1. WBGO. jazz. in your folder Jazz.",
    ]
    assert songs.text.splitlines() == [
        "Songs heard on WBGO, newest first:",
        "- So What by Miles Davis",
    ]
    assert approver.asked == []


def test_play_asks_with_the_station_and_plays_on_yes() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(host, approver)
    registry.call("radio_find_stations", {"query": "jazz"})

    result = registry.call("radio_play_station", {"station": "S2"})

    assert approver.asked == ["Play KCSM Jazz 91."]
    assert result.ok and result.text == "Playing KCSM Jazz 91."
    assert host._radio_controller.played == [_KCSM]


def test_play_refused_plays_nothing() -> None:
    host = _host()
    registry = _registry(host, _Approver(ApprovalChoice.DENY))

    result = registry.call("radio_play_station", {"station": "F1"})

    assert not result.ok
    assert host._radio_controller.played == []
    assert not registry.mutated()


def test_record_asks_then_starts_radios_own_recorder_with_its_settings() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(host, approver)

    result = registry.call("radio_record_station", {"station": "F1", "minutes": 90})

    assert approver.asked == ["Record WBGO now, for 90 minutes."]
    assert result.ok
    assert result.text.startswith("Recording started: WBGO, for 90 minutes.")
    started = host._radio_recorder.started[0]
    assert started["stream_url"] == _WBGO.stream_url
    assert started["duration_minutes"] == 90
    assert started["settings"] is host._radio_recording_settings
    assert host.refreshed == ["status"]


def test_record_refused_records_nothing() -> None:
    host = _host()
    registry = _registry(host, _Approver(ApprovalChoice.DENY))

    result = registry.call("radio_record_station", {"station": "F1", "minutes": 30})

    assert not result.ok
    assert host._radio_recorder.started == []


def test_record_past_the_settings_cap_is_refused_before_it_starts() -> None:
    host = _host()
    host._radio_recording_settings = RecordingSettings(max_duration_minutes=60)
    registry = _registry(host, _Approver(ApprovalChoice.TASK))

    result = registry.call("radio_record_station", {"station": "F1", "minutes": 120})

    assert not result.ok
    assert "limited to 60 minutes" in result.text
    assert host._radio_recorder.started == []


def test_schedule_asks_with_the_exact_station_time_and_length() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(host, approver)
    day = date.today() + timedelta(days=3)
    months = (
        "January February March April May June July August September October November December"
    ).split()
    weekdays = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()

    result = registry.call(
        "radio_schedule_recording",
        {
            "station": "F1",
            "repeat": "once",
            "date": day.isoformat(),
            "time": "8:00 PM",
            "minutes": 60,
        },
    )

    words = f"{weekdays[day.weekday()]} {day.day} {months[day.month - 1]} {day.year}"
    assert approver.asked == [f"Schedule a recording of WBGO on {words} at 8:00 PM, for one hour."]
    assert result.ok, result.text
    entry = host._radio_scheduler.entries[0]
    assert (entry.station_name, entry.recurrence, entry.duration_minutes) == ("WBGO", "once", 60)
    assert entry.run_at == f"{day.isoformat()}T20:00:00"
    assert host.refreshed == ["wake", "sleep"]  # the same refresh the window does
    assert "nothing waits on the AI" in result.text


def test_a_weekly_schedule_says_the_day_and_a_duplicate_is_refused() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.TASK)
    registry = _registry(host, approver)
    args = {
        "station": "F1",
        "repeat": "weekly",
        "weekday": "Friday",
        "time": "19:30",
        "minutes": 30,
    }

    first = registry.call("radio_schedule_recording", args)
    again = registry.call("radio_schedule_recording", args)

    assert approver.asked == [
        "Schedule a recording of WBGO every Friday at 7:30 PM, for 30 minutes."
    ]  # "for this task": asked once
    assert first.ok
    assert not again.ok and again.text == "That recording is already scheduled."
    assert len(host._radio_scheduler.entries) == 1


def test_schedule_refused_adds_nothing_and_list_scheduled_says_so() -> None:
    host = _host()
    registry = _registry(host, _Approver(ApprovalChoice.DENY))

    result = registry.call(
        "radio_schedule_recording",
        {"station": "F1", "repeat": "daily", "time": "7:00 AM", "minutes": 60},
    )

    assert not result.ok
    assert host._radio_scheduler.entries == []
    assert registry.call("radio_list_scheduled", {}).text == "No recordings are scheduled."


def test_an_unknown_station_is_explained_not_guessed() -> None:
    registry = _registry(_host(), _Approver(ApprovalChoice.ONCE))

    result = registry.call("radio_play_station", {"station": "S9"})

    assert not result.ok
    assert "Use radio_find_stations or radio_list_favorites first" in result.text
