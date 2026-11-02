"""Find the Part Where: Quill Media Player's agent task (codex.md 6.11, Phase 4c).

The person says what they want ("take me to the chapter about the storm", "go
back to where I left the note about Ahab"), and an agent engine -- My GitHub
Copilot or Codex -- finds it with the player's own tools in the shared agent
window (:mod:`quill.ui.agent_window`):

* ``player.where_am_i`` -- the book's title, the place and the length.
* ``player.list_chapters`` and ``player.list_bookmarks`` -- the chapters (with
  their start times) and the bookmarks in this book (with times and notes), as
  numbered rows with ids (``C1``, ``B1``) ``go_to`` takes.
* ``player.go_to`` -- moves the place, the way Go to Position does (the same
  clamp to the length, the same seek), so it asks first: "Go to 1:02:30 in
  Moby Dick."

**Chapters and bookmarks only.** codex.md 6.11 imagines a transcript made by
Transcribe's local engine; none exists here and none is made, so the task finds
places by chapter titles, bookmark notes and times. The audio never leaves.
Handlers run on a worker thread; every touch of the player goes through
``ctx.on_ui``. Nothing here announces: the agent window says each step and the
closing summary, once (GATE-13).
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "APP",
    "FIND_THE_PART",
    "INSTRUCTION_HELP",
    "player_task_facts",
    "player_task_tools",
]

APP = "player"

_LIST_LIMIT = 300
_NOTHING_OPEN = "No book or file is open. The person opens one with Open (Ctrl+O)."

FIND_THE_PART = AppTaskSpec(
    app=APP,
    agent_id="player-find-the-part",
    title="Find the Part Where",
    instructions=(
        "You help someone who uses a screen reader find a place in what Quill "
        "Media Player has open: an audiobook, a DAISY book or a recording. "
        "player_where_am_i says the title, the place and the length; "
        "player_list_chapters and player_list_bookmarks give the chapters and "
        "the person's bookmarks with their times and notes. There is no "
        "transcript: find the place from chapter titles, bookmark notes, times "
        "and what you know about the book. Then move there with player_go_to, "
        "by a time like 1:02:30 or an id such as C3 or B2. Moving asks the "
        "person first, and they may say no."
    ),
    done_words={f"{APP}.go_to": "Moved the place"},
    noun="move",
)

INSTRUCTION_HELP = (
    "Type the part you want to find, then press Enter. For example: the chapter "
    "where the storm starts, or the bookmark I left about the map. It finds places "
    "by chapters, bookmarks and times, and asks before it moves. While a task "
    "runs, what you type here goes to it as a follow-up."
)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _clock(ms: int) -> str:
    from quill.core.media import format_timecode

    return str(format_timecode(max(0, int(ms)), always_hours=True))


def _title(host: Any) -> str:
    try:
        return str(host._now_playing.GetValue() or "").strip() or "the open file"
    except Exception:  # noqa: BLE001 - a half-built window has no title yet
        return "the open file"


def player_task_facts(host: Any) -> str:
    """What is open, as text, sent with the first instruction."""
    if getattr(host, "_book_path", None) is None and not getattr(host, "_book_key", ""):
        return "Nothing is open."
    lines = [f"Open: {_title(host)}"]
    try:
        lines.append(
            f"Place: {_clock(host._player.playhead_ms())} of {_clock(host._player.length_ms())}"
        )
    except Exception:  # noqa: BLE001 - no engine: the place is unknown
        pass
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def player_task_tools(host: Any, ctx: AppTaskHost) -> list[FamilyTool]:
    """Quill Media Player's tools for one task."""

    def is_open() -> bool:
        return bool(ctx.on_ui(lambda: host._book_path is not None or bool(host._book_key), False))

    def need_open() -> None:
        if not is_open():
            raise ToolError(_NOTHING_OPEN)

    def chapters() -> list[tuple[str, int | None, int]]:
        """(title, start in ms or None for a separate file, depth) for each chapter."""

        def read() -> list[tuple[str, int | None, int]]:
            rows = []
            for title, payload, depth in list(host._chapter_nodes):
                start = int(payload[1]) if payload and payload[0] == "seek" else None  # type: ignore[call-overload]
                rows.append((str(title), start, int(depth)))
            return rows

        return list(ctx.on_ui(read, []) or [])

    def bookmarks() -> list[Any]:
        return list(
            ctx.on_ui(lambda: host._bookmarks.list(host._book_key) if host._book_key else [], [])
            or []
        )

    def target_ms(args: dict[str, Any]) -> tuple[int, str]:
        """Where to go, in ms, and how to say it ("chapter 3, The Storm")."""
        from quill.core.media import InvalidTimecodeError, parse_timecode

        wanted = str(args.get("position", "") or "").strip()
        key = wanted.upper()
        if not wanted:
            raise ToolError("Say where to go: a time like 1:02:30, or an id such as C3 or B2.")
        if key[:1] == "C" and key[1:].isdigit():
            rows = chapters()
            index = int(key[1:]) - 1
            if not 0 <= index < len(rows):
                raise ToolError(f"There is no chapter {key}. Use player_list_chapters.")
            title, start, _depth = rows[index]
            if start is None:
                raise ToolError(
                    f"{title} is a separate file, not a place in this one. The person "
                    "opens it from the Chapters list."
                )
            return start, f"chapter {index + 1}, {title}"
        if key[:1] == "B" and key[1:].isdigit():
            marks = bookmarks()
            index = int(key[1:]) - 1
            if not 0 <= index < len(marks):
                raise ToolError(f"There is no bookmark {key}. Use player_list_bookmarks.")
            mark = marks[index]
            words = str(mark.note or mark.label or "").strip()
            return int(mark.position_ms), f"bookmark {index + 1}" + (f", {words}" if words else "")
        try:
            return parse_timecode(wanted), ""
        except InvalidTimecodeError as error:
            raise ToolError("Give the time like 1:02:30, or an id such as C3 or B2.") from error

    def clamped(ms: int) -> int:
        from quill.core.media import clamp_position

        length = int(ctx.on_ui(lambda: host._player.length_ms(), 0) or 0)
        return int(clamp_position(ms, length))

    # -- reads ---------------------------------------------------------------

    def where_am_i(_args: dict[str, Any]) -> str:
        need_open()

        def read() -> tuple[str, int, int, int, int]:
            return (
                _title(host),
                int(host._player.playhead_ms()),
                int(host._player.length_ms()),
                int(host._player.current_chapter_index()),
                len(host._chapters),
            )

        title, position, length, index, count = ctx.on_ui(read, ("", 0, 0, -1, 0))
        lines = [f"Open: {title}", f"Place: {_clock(position)}"]
        if length > 0:
            lines.append(f"Length: {_clock(length)}")
        rows = chapters()
        if count and 0 <= index < len(rows):
            lines.append(f"Chapter: {index + 1} of {count}, {rows[index][0]}")
        return "\n".join(lines)

    def list_chapters(_args: dict[str, Any]) -> str:
        need_open()
        rows = chapters()
        if not rows:
            return "This file has no chapters."
        lines = [f"{_plural(len(rows), 'chapter')}:"]
        for number, (title, start, depth) in enumerate(rows[:_LIST_LIMIT], start=1):
            where = f" at {_clock(start)}" if start is not None else " (a separate file)"
            lines.append(f"{'  ' * max(0, depth - 1)}C{number}. {title}{where}")
        if len(rows) > _LIST_LIMIT:
            lines.append(f"... and {len(rows) - _LIST_LIMIT} more.")
        return "\n".join(lines)

    def list_bookmarks(_args: dict[str, Any]) -> str:
        need_open()
        marks = bookmarks()
        if not marks:
            return "There are no bookmarks in this book."
        lines = [f"{_plural(len(marks), 'bookmark')}:"]
        for number, mark in enumerate(marks[:_LIST_LIMIT], start=1):
            words = " ".join(x for x in (str(mark.label or ""), str(mark.note or "")) if x)
            lines.append(f"B{number}. {_clock(mark.position_ms)}" + (f": {words}" if words else ""))
        return "\n".join(lines)

    # -- what changes --------------------------------------------------------

    def go_to(args: dict[str, Any]) -> str:
        from quill.core.media import format_spoken

        need_open()
        wanted, what = target_ms(args)
        target = clamped(wanted)

        def seek() -> bool:
            if host._book_path is None and not host._book_key:
                return False
            host._player.seek_to(target)  # Go to Position's own seek
            return True

        if not ctx.on_ui(seek, False):
            raise ToolError(_NOTHING_OPEN)
        said = f"Jumped to {format_spoken(target)}" + (f", {what}" if what else "") + "."
        if target != wanted:
            said += f" That was beyond the end, so it moved to {_clock(target)}."
        return said

    def go_to_summary(args: dict[str, Any]) -> str:
        try:
            wanted, what = target_ms(args)
            target = clamped(wanted)
        except ToolError:
            return f"Move the place in {ctx.on_ui(lambda: _title(host), 'the open file')}."
        where = _clock(target) + (f" ({what})" if what else "")
        return f"Go to {where} in {ctx.on_ui(lambda: _title(host), 'the open file')}."

    return [
        FamilyTool(
            name=f"{APP}.where_am_i",
            description="Say what is open, the place in it, its length and the chapter.",
            handler=where_am_i,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_chapters",
            description="List the chapters, each with an id such as C1 and its start time.",
            handler=list_chapters,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_bookmarks",
            description=(
                "List the person's bookmarks in this book, each with an id such as B1, "
                "its time and its note."
            ),
            handler=list_bookmarks,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.go_to",
            description=(
                "Move the place in the open file to a time (1:02:30), a chapter (C3) or "
                "a bookmark (B2), as Go to Position does. Asks the person first."
            ),
            handler=go_to,
            parameters=_schema(
                {
                    "position": {
                        "type": "string",
                        "description": "A time like 1:02:30, or an id such as C3 or B2.",
                    }
                },
                ("position",),
            ),
            category=PermissionCategory.MODIFY_SELECTION,
            risk=RiskLevel.LOW,
            app=APP,
            mutating=True,
            summarize=go_to_summary,
        ),
    ]
