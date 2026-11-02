"""Find and Record: Quill Radio's agent task (codex.md 6.5, Phase 4c).

The person says what they want ("find a jazz station in New Orleans and record
it tonight from 8 for an hour"), and an agent engine -- My GitHub Copilot or
Codex -- works through it with Radio's own tools, in the shared agent window
(:mod:`quill.ui.agent_window`). Every tool here is a thin wrapper over what
Radio already does:

* ``radio.find_stations`` -- your favourites, the station catalogue on this
  computer and the Radio Browser directory, the same lanes Find Stations
  searches, as numbered text rows with an id (``S1``) the other tools take.
* ``radio.list_favorites``, ``radio.recent_songs``, ``radio.list_scheduled`` --
  reads, so they run without a question.
* ``radio.play_station`` -- what plays changes, so it asks.
* ``radio.record_station`` -- starts a recording now through Radio's own
  recorder, with your Recording Settings and Sound Enhancements, so it asks.
* ``radio.schedule_recording`` -- adds an entry to Radio's own schedule, so it
  asks with the exact station, time and length in the question. The recording
  is made by Radio's scheduler while Quill Radio is running; the agent never
  wakes up later, so nothing runs on your AI plan in the background.

Handlers run on a worker thread: every touch of Radio's state goes through
``ctx.on_ui``. Nothing here announces: the agent window reports each step and
the closing summary, once (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.ai.app_task import AppTaskHost
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError
from quill.ui.radio.radio_ai_task_words import (
    _FIND_LIMIT,
    _SONG_LIMIT,
    _WEEKDAYS,
    APP,
    FIND_AND_RECORD,
    INSTRUCTION_HELP,
    RadioTaskState,
    _entry_words,
    _favorite_stations,
    _minutes_words,
    _name,
    _playing,
    _when_words,
    radio_task_facts,
    station_row,
)

__all__ = [
    "FIND_AND_RECORD",
    "INSTRUCTION_HELP",
    "radio_task_facts",
    "radio_task_tools",
    "station_row",
]

# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def radio_task_tools(
    host: Any,
    ctx: AppTaskHost,
    *,
    search_live: Callable[[str, bool], list[Any]] | None = None,
) -> list[FamilyTool]:
    """Radio's tools for one task. *search_live* replaces the directory lane (tests)."""
    state = RadioTaskState()
    live = search_live or _radio_browser

    def favorites_now() -> list[tuple[Any, str]]:
        return list(ctx.on_ui(lambda: _favorite_stations(host), []) or [])

    def resolve(args: dict[str, Any]) -> Any:
        wanted = str(args.get("station", "") or "").strip()
        if not wanted:
            raise ToolError("Say which station, by its id from a list, such as S1 or F2.")
        key = wanted.upper()
        if key in ("PLAYING", "NOW", "NOW PLAYING"):
            station = ctx.on_ui(lambda: _playing(host), None)
            if station is None:
                raise ToolError("Nothing is playing.")
            return station
        if key in state.found:
            return state.found[key]
        if key.startswith("F") and key[1:].isdigit():
            favorites = favorites_now()
            index = int(key[1:]) - 1
            if 0 <= index < len(favorites):
                return favorites[index][0]
        folded = wanted.casefold()
        matches = [
            station
            for station in [s for s, _f in favorites_now()] + list(state.found.values())
            if _name(station).casefold() == folded or str(station.name).casefold() == folded
        ]
        if matches:
            return matches[0]
        raise ToolError(
            f"There is no station {wanted}. Use radio_find_stations or "
            "radio_list_favorites first, and pass the id it gives, such as S1 or F2."
        )

    def recordable(args: dict[str, Any]) -> Any:
        station = resolve(args)
        if bool(getattr(station, "is_recording", False)):
            raise ToolError(
                f"{_name(station)} is a finished recording, not a live stream, so there "
                "is nothing to record as it goes out."
            )
        if not str(getattr(station, "stream_url", "") or ""):
            raise ToolError(f"{_name(station)} has no stream address to record.")
        return station

    def safe_name(args: dict[str, Any]) -> str:
        try:
            return _name(resolve(args))
        except ToolError:
            return str(args.get("station", "") or "the station")

    # -- reads ---------------------------------------------------------------

    def find_stations(args: dict[str, Any]) -> str:
        query = " ".join(str(args.get("query", "") or "").split())
        if not query:
            raise ToolError("Say what to look for: a name, a city, a kind of music.")
        safe_mode = bool(getattr(host, "_safe_mode", False))
        rows: list[tuple[Any, str]] = []

        def mine() -> list[tuple[Any, str]]:
            store = getattr(host, "_radio_favorites", None)
            if store is None:
                return []
            from quill.core.radio.favorites import is_place

            return [
                (fav.station, str(fav.folder or "your favourites"))
                for fav in store.search(query)
                if not is_place(fav.station)
            ]

        rows.extend(ctx.on_ui(mine, []) or [])
        rows.extend((station, "") for station in _catalog(host, query))
        if len(rows) < _FIND_LIMIT and not safe_mode:
            try:
                rows.extend((station, "") for station in live(query, safe_mode))
            except Exception:  # noqa: BLE001 - one lane down is not the search down
                pass
        seen: set[str] = set()
        lines: list[str] = []
        for station, folder in rows:
            url = str(getattr(station, "stream_url", "") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            lines.append(station_row(state.remember(station), station, folder=folder))
            if len(lines) >= _FIND_LIMIT:
                break
        if not lines:
            said = f"No stations matched {query}."
            if safe_mode:
                said += " Only this computer's lists were searched, because of Safe Mode."
            return said
        head = f"{len(lines)} station{'s' if len(lines) != 1 else ''} for {query}:"
        return "\n".join([head, *lines])

    def list_favorites(args: dict[str, Any]) -> str:
        folder = str(args.get("folder", "") or "").strip().casefold()
        favorites = favorites_now()
        lines = [
            station_row(f"F{index}", station, folder=where or "the top level")
            for index, (station, where) in enumerate(favorites, start=1)
            if not folder or where.casefold() == folder
        ]
        if not lines:
            return "There are no favourite stations." if not folder else "No favourites there."
        return "\n".join([
            f"{len(lines)} favourite station{'s' if len(lines) != 1 else ''}:",
            *lines,
        ])

    def recent_songs(args: dict[str, Any]) -> str:
        from quill.ui.radio.song_history_commands import song_history

        chosen = resolve(args) if str(args.get("station", "") or "").strip() else None

        def read() -> list[tuple[str, list[str]]]:
            log = song_history(host)
            station = chosen if chosen is not None else _playing(host)
            if station is not None:
                key = str(station.station_uuid or station.stream_url)
                return [(_name(station), [s.display() for s in log.songs_for(key)])]
            return [
                (str(s.station_name or s.station_key), [song.display() for song in s.songs])
                for s in log.known_stations()[:5]
            ]

        found = ctx.on_ui(read, [])
        if not found or not any(songs for _n, songs in found):
            return "No songs have been heard and logged here yet."
        lines: list[str] = []
        for name, songs in found:
            if not songs:
                continue
            newest = songs[:_SONG_LIMIT]  # the log keeps the newest first
            lines.append(f"Songs heard on {name}, newest first:")
            lines.extend(f"- {song}" for song in newest)
        return "\n".join(lines)

    def list_scheduled(_args: dict[str, Any]) -> str:
        def read() -> list[Any]:
            scheduler = getattr(host, "_radio_scheduler", None)
            return list(getattr(scheduler, "entries", []) or [])

        entries = ctx.on_ui(read, []) or []
        if not entries:
            return "No recordings are scheduled."
        lines = [f"{len(entries)} scheduled recording{'s' if len(entries) != 1 else ''}:"]
        lines.extend(f"{i}. {_entry_words(e)}" for i, e in enumerate(entries, start=1))
        return "\n".join(lines)

    # -- what changes --------------------------------------------------------

    def play_station(args: dict[str, Any]) -> str:
        station = resolve(args)

        def play() -> bool:
            controller = getattr(host, "_radio_controller", None)
            if controller is None:
                return False
            controller.play_station(station)
            return True

        if not ctx.on_ui(play, False):
            raise ToolError("The player is not ready.")
        return f"Playing {_name(station)}."

    def _minutes(args: dict[str, Any]) -> int:
        try:
            minutes = int(args.get("minutes", 0) or 0)
        except (TypeError, ValueError):
            minutes = 0
        if minutes < 1:
            raise ToolError("Say how long to record, in minutes.")
        settings = getattr(host, "_radio_recording_settings", None)
        cap = int(getattr(settings, "max_duration_minutes", 0) or 0)
        if cap and minutes > cap:
            raise ToolError(
                f"Recordings are limited to {cap} minutes in Recording Settings; ask for "
                "that or less."
            )
        return minutes

    def record_station(args: dict[str, Any]) -> str:
        from quill.core.speech.ffmpeg import ffmpeg_available

        station = recordable(args)
        minutes = _minutes(args)
        if not ffmpeg_available():
            raise ToolError("Recording needs FFmpeg, and this copy of Quill Radio cannot find it.")

        def start() -> str:
            # Radio's own recorder, with the same settings and enhancements as
            # Record Station... (main_frame_radio.open_record_station_dialog).
            from quill.core.radio.recording import RecordingError

            try:
                host._radio_recorder.start(
                    station_name=station.name,
                    stream_url=station.stream_url,
                    settings=host._radio_recording_settings,
                    duration_minutes=minutes,
                    filter_graph=host._radio_recording_filter_graph(),
                    exact_optilab=host._radio_recording_exact(),
                )
            except RecordingError as error:
                return str(error) or "The recording could not start."
            refresh = getattr(host, "_refresh_statusbar", None)
            if callable(refresh):
                refresh()
            return ""

        problem = ctx.on_ui(start, "The task was stopped.")
        if problem:
            raise ToolError(problem)
        return (
            f"Recording started: {_name(station)}, for {_minutes_words(minutes)}. It goes "
            "where Radio keeps recordings; the Recordings list can stop it early."
        )

    def schedule_entry(args: dict[str, Any]) -> Any:
        from quill.core.radio.wake_timer import parse_time_of_day
        from quill.ui.radio.schedule_recording_dialog import build_schedule_entry

        station = recordable(args)
        minutes = _minutes(args)
        recurrence = str(args.get("repeat", "once") or "once").strip().lower()
        if recurrence not in ("once", "daily", "weekly"):
            raise ToolError("Repeat must be once, daily or weekly.")
        weekday_text = str(args.get("weekday", "") or "").strip().capitalize()
        weekday = _WEEKDAYS.index(weekday_text) if weekday_text in _WEEKDAYS else -1
        if recurrence == "weekly" and weekday < 0:
            raise ToolError("Say which day of the week, such as Monday.")
        time_text = str(args.get("time", "") or "")
        if not parse_time_of_day(time_text):
            raise ToolError("Give the time like 7:30 PM or 19:30.")
        entry, problem = build_schedule_entry(
            name=station.name,
            url=station.stream_url,
            recurrence_index=("once", "daily", "weekly").index(recurrence),
            time_text=time_text,
            date_text=str(args.get("date", "") or ""),
            weekday_index=weekday,
            timezone_name="",
            duration_minutes=minutes,
        )
        if entry is None:
            raise ToolError(problem or "That recording could not be scheduled.")
        return entry

    def schedule_recording(args: dict[str, Any]) -> str:
        entry = schedule_entry(args)

        def add() -> str:
            scheduler = getattr(host, "_radio_scheduler", None)
            if scheduler is None:
                return "Radio's schedule is not ready."
            for existing in list(scheduler.entries):
                if (
                    existing.stream_url == entry.stream_url
                    and existing.recurrence == entry.recurrence
                    and existing.run_at == entry.run_at
                    and existing.weekday == entry.weekday
                ):
                    return "That recording is already scheduled."
            # Radio's own scheduler, as the Schedule Recording window adds one,
            # then the same wake and keep-awake refresh that window does.
            scheduler.add(entry)
            for name in ("_refresh_radio_wake_task", "_update_sleep_inhibitor"):
                method = getattr(host, name, None)
                if callable(method):
                    try:
                        method()
                    except Exception:  # noqa: BLE001 - the entry is saved either way
                        pass
            return ""

        problem = ctx.on_ui(add, "The task was stopped.")
        if problem:
            raise ToolError(problem)
        return (
            f"Scheduled: {_entry_words(entry)} Quill Radio records it itself while it is "
            "running; nothing waits on the AI."
        )

    def schedule_summary(args: dict[str, Any]) -> str:
        from quill.core.radio.wake_timer import parse_time_of_day

        name = safe_name(args)
        recurrence = str(args.get("repeat", "once") or "once").strip().lower()
        hhmm = parse_time_of_day(str(args.get("time", "") or "")) or "00:00"
        weekday_text = str(args.get("weekday", "") or "").strip().capitalize()
        weekday = _WEEKDAYS.index(weekday_text) if weekday_text in _WEEKDAYS else 0
        when = _when_words(recurrence, hhmm, str(args.get("date", "") or ""), weekday)
        minutes = int(args.get("minutes", 0) or 0)
        return f"Schedule a recording of {name} {when}, for {_minutes_words(minutes)}."

    station_arg = {
        "type": "string",
        "description": "The station's id from a list (S1, F2), or 'playing'.",
    }
    minutes_arg = {"type": "integer", "description": "How long to record, in minutes."}
    return [
        FamilyTool(
            name=f"{APP}.find_stations",
            description=(
                "Find radio stations by name, place or kind of music. Searches your "
                "favourites, the station catalogue on this computer and the Radio "
                "Browser directory. Returns numbered rows with an id such as S1."
            ),
            handler=find_stations,
            parameters=_schema(
                {"query": {"type": "string", "description": "What to look for."}}, ("query",)
            ),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_favorites",
            description=(
                "List the person's favourite stations, with an id such as F1 and the "
                "folder each is in. Optionally only one folder."
            ),
            handler=list_favorites,
            parameters=_schema(
                {"folder": {"type": "string", "description": "Only this folder (optional)."}},
                (),
            ),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.recent_songs",
            description=(
                "List songs heard here, newest first: on one station, on the station "
                "playing, or across recent stations when nothing is playing."
            ),
            handler=recent_songs,
            parameters=_schema({"station": station_arg}, ()),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_scheduled",
            description="List the recordings already scheduled, with when each next runs.",
            handler=list_scheduled,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.play_station",
            description="Play one station now. Asks the person first.",
            handler=play_station,
            parameters=_schema({"station": station_arg}, ("station",)),
            category=PermissionCategory.MODIFY_SELECTION,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=lambda a: f"Play {safe_name(a)}.",
        ),
        FamilyTool(
            name=f"{APP}.record_station",
            description=(
                "Start recording one station now, for a number of minutes, with "
                "Radio's own recorder. Asks the person first."
            ),
            handler=record_station,
            parameters=_schema(
                {"station": station_arg, "minutes": minutes_arg}, ("station", "minutes")
            ),
            category=PermissionCategory.RECORD_AUDIO,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=lambda a: (
                f"Record {safe_name(a)} now, for {_minutes_words(int(a.get('minutes', 0) or 0))}."
            ),
        ),
        FamilyTool(
            name=f"{APP}.schedule_recording",
            description=(
                "Add a recording to Radio's schedule: once on a date, daily, or weekly "
                "on a day, at a local time, for a number of minutes. Radio records it "
                "itself while it is running. Asks the person first."
            ),
            handler=schedule_recording,
            parameters=_schema(
                {
                    "station": station_arg,
                    "repeat": {
                        "type": "string",
                        "enum": ["once", "daily", "weekly"],
                        "description": "once, daily or weekly.",
                    },
                    "date": {
                        "type": "string",
                        "description": "For once: the date, YYYY-MM-DD.",
                    },
                    "weekday": {
                        "type": "string",
                        "enum": list(_WEEKDAYS),
                        "description": "For weekly: the day.",
                    },
                    "time": {"type": "string", "description": "Local time, like 7:30 PM or 19:30."},
                    "minutes": minutes_arg,
                },
                ("station", "repeat", "time", "minutes"),
            ),
            category=PermissionCategory.SCHEDULE,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=schedule_summary,
        ),
    ]


def _catalog(host: Any, query: str) -> list[Any]:
    """The station catalogue on this computer (no network), as Find Stations reads it."""
    try:
        from quill.ui.radio.catalog_search import catalog_search_rows
        from quill.ui.radio.catalog_ui import catalog_for

        return catalog_search_rows(catalog_for(host), query, limit=_FIND_LIMIT)
    except Exception:  # noqa: BLE001 - the catalogue never breaks a search
        return []


def _radio_browser(query: str, safe_mode: bool) -> list[Any]:
    """The Radio Browser lane Find Stations searches (directory_search)."""
    from quill.core.radio.directory_search import radio_browser_variants

    return list(radio_browser_variants(query, limit=_FIND_LIMIT, safe_mode=safe_mode))
